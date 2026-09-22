"""Local/Raspberry equivalent of the Vercel session and rate-limit endpoints."""
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from pathlib import Path
from http.cookies import SimpleCookie
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')
COOKIE = '__Host-gastos_session'
COOKIE_AGE = 34560000


def persistent_cookie(value):
  return f'{COOKIE}={value}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age={COOKIE_AGE if value else 0}'


class AccessError(Exception):
  def __init__(self, message, status=401):
    super().__init__(message)
    self.status = status


def digest(value):
  return hashlib.sha256(value.encode()).hexdigest()


def version():
  password = os.getenv('ASSISTANT_PASSWORD', '')
  if len(password) < 16:
    raise AccessError('Configura ASSISTANT_PASSWORD con al menos 16 caracteres en backend/.env.', 503)
  return digest(password)


def connection():
  path = BASE_DIR / 'data' / 'assistant-auth.db'
  path.parent.mkdir(parents=True, exist_ok=True)
  db = sqlite3.connect(path, timeout=10)
  db.executescript('''CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, version TEXT, expires REAL);
    CREATE TABLE IF NOT EXISTS limits (bucket TEXT PRIMARY KEY, hits INTEGER, expires REAL);''')
  return db


def limit(bucket, maximum, seconds):
  db = connection()
  try:
    with db:
      db.execute('BEGIN IMMEDIATE')
      row = db.execute('SELECT hits, expires FROM limits WHERE bucket=?', (bucket,)).fetchone()
      now = time.time()
      hits, expires = row if row and row[1] > now else (0, now + seconds)
      if hits >= maximum:
        raise AccessError('Limite de solicitudes alcanzado. Intenta mas tarde.', 429)
      db.execute('INSERT OR REPLACE INTO limits VALUES (?, ?, ?)', (bucket, hits + 1, expires))
  finally:
    db.close()


def token(handler):
  cookie = SimpleCookie()
  try:
    cookie.load(handler.headers.get('Cookie', ''))
    return cookie[COOKIE].value if COOKIE in cookie else ''
  except Exception:
    return ''


def same_origin(handler):
  # Neither Python server grants cross-origin requests; custom header forces preflight.
  if handler.headers.get('X-Gastos-Request') != '1' or handler.headers.get('Sec-Fetch-Site') == 'cross-site':
    raise AccessError('Solicitud no permitida.', 403)


def session(handler):
  current = version()
  value = token(handler)
  if not value:
    return False
  db = connection()
  try:
    return bool(db.execute('SELECT token FROM sessions WHERE token=? AND version=? AND expires>?', (digest(value), current, time.time())).fetchone())
  finally:
    db.close()


def require_session(handler):
  same_origin(handler)
  if not session(handler):
    raise AccessError('Ingresa la contraseña para continuar.')
  limit('private-actions', 30, 60)


def consume_openai():
  try:
    maximum = int(os.getenv('ASSISTANT_DAILY_OPENAI_LIMIT', '100'))
    if not 1 <= maximum <= 10000:
      raise ValueError()
  except ValueError:
    raise AccessError('ASSISTANT_DAILY_OPENAI_LIMIT debe estar entre 1 y 10000.', 503)
  limit('openai-daily', maximum, 86400)


def handle_session(handler):
  cookie = None
  try:
    if handler.command == 'GET':
      authenticated = session(handler)
      if authenticated:
        cookie = persistent_cookie(token(handler))
    else:
      same_origin(handler)
      current = version()
      if handler.command == 'POST':
        limit('login-global', 60, 900)
        limit('login:' + digest(handler.client_address[0]), 5, 900)
        size = int(handler.headers.get('Content-Length', '0'))
        if not 0 < size <= 4096:
          raise AccessError('Solicitud invalida.', 400)
        try:
          password = json.loads(handler.rfile.read(size)).get('password')
        except (ValueError, AttributeError):
          raise AccessError('JSON invalido.', 400)
        if not isinstance(password, str) or not hmac.compare_digest(digest(password), current):
          raise AccessError('Contraseña incorrecta.')
      value = secrets.token_hex(32) if handler.command == 'POST' else ''
      db = connection()
      try:
        with db:
          db.execute('DELETE FROM sessions WHERE expires<=? OR token=?', (time.time(), digest(token(handler))))
          db.execute('DELETE FROM limits WHERE expires<=?', (time.time(),))
          if value:
            db.execute('INSERT INTO sessions VALUES (?, ?, ?)', (digest(value), current, float('inf')))
      finally:
        db.close()
      authenticated = bool(value)
      cookie = persistent_cookie(value)
    body, status = {'authenticated': authenticated}, 200
  except AccessError as error:
    body, status = {'error': str(error)}, error.status
  except Exception:
    body, status = {'error': 'No se pudo verificar el acceso.'}, 503
  encoded = json.dumps(body).encode()
  handler.send_response(status)
  handler.send_header('Content-Type', 'application/json')
  handler.send_header('Cache-Control', 'no-store')
  handler.send_header('Content-Length', str(len(encoded)))
  if cookie:
    handler.send_header('Set-Cookie', cookie)
  handler.end_headers()
  handler.wfile.write(encoded)
