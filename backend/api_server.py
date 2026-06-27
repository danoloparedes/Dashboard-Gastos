from __future__ import annotations

import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from sync_google_sheet import run_sync

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

DB_PATH = os.getenv('SQLITE_DB_PATH', './data/gastos.db')
if not Path(DB_PATH).is_absolute():
  DB_PATH = str((BASE_DIR / DB_PATH).resolve())

HOST = os.getenv('API_HOST', '0.0.0.0')
PORT = int(os.getenv('API_PORT', '8000'))


def run_sync_now() -> dict:
  spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', '').strip()
  worksheet_name = os.getenv('GOOGLE_SHEETS_WORKSHEET', 'Gastos').strip() or 'Gastos'
  credentials_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', './service-account.json').strip()

  if not spreadsheet_id:
    raise RuntimeError('Falta GOOGLE_SHEETS_SPREADSHEET_ID en backend/.env')

  credentials_path = Path(credentials_file)
  if not credentials_path.is_absolute():
    credentials_path = (BASE_DIR / credentials_path).resolve()
  if not credentials_path.exists():
    alt_path = (BASE_DIR / 'sync' / 'service-account.json').resolve()
    if alt_path.exists():
      credentials_path = alt_path
  if not credentials_path.exists():
    raise RuntimeError(f'No existe archivo de credenciales: {credentials_path}')

  schema_path = (BASE_DIR / 'sync' / 'schema.sql').resolve()

  return run_sync(
    db_path=DB_PATH,
    schema_path=str(schema_path),
    spreadsheet_id=spreadsheet_id,
    worksheet_name=worksheet_name,
    credentials_file=str(credentials_path),
  )


def query_transactions() -> list[dict]:
  db_file = Path(DB_PATH)
  if not db_file.exists():
    return []

  conn = sqlite3.connect(DB_PATH)
  conn.row_factory = sqlite3.Row

  rows = conn.execute(
    """
    SELECT fecha, descripcion, clasificacion, tipo, abono, gasto
    FROM transactions
    ORDER BY fecha ASC, id ASC
    """
  ).fetchall()
  conn.close()

  return [
    {
      'fecha': row['fecha'],
      'descripcion': row['descripcion'] or '',
      'clasificacion': row['clasificacion'] or '',
      'tipo': row['tipo'] or '',
      'abono': int(row['abono'] or 0),
      'gasto': int(row['gasto'] or 0),
    }
    for row in rows
  ]


class Handler(BaseHTTPRequestHandler):
  def _send_json(self, payload: dict, status: int = 200) -> None:
    body = json.dumps(payload).encode('utf-8')
    self.send_response(status)
    self.send_header('Content-Type', 'application/json; charset=utf-8')
    self.send_header('Access-Control-Allow-Origin', '*')
    self.send_header('Content-Length', str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def do_OPTIONS(self) -> None:
    self.send_response(204)
    self.send_header('Access-Control-Allow-Origin', '*')
    self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    self.end_headers()

  def do_POST(self) -> None:
    parsed = urlparse(self.path)

    if parsed.path == '/api/sync':
      try:
        result = run_sync_now()
        self._send_json({'ok': True, 'result': result})
      except Exception as exc:  # pragma: no cover
        self._send_json({'ok': False, 'error': str(exc)}, status=500)
      return

    self._send_json({'error': 'not_found'}, status=404)

  def do_GET(self) -> None:
    parsed = urlparse(self.path)

    if parsed.path == '/health':
      self._send_json({'ok': True, 'db_path': DB_PATH})
      return

    if parsed.path == '/api/transactions':
      try:
        transactions = query_transactions()
        self._send_json({'transactions': transactions})
      except Exception as exc:  # pragma: no cover
        self._send_json({'error': str(exc)}, status=500)
      return

    self._send_json({'error': 'not_found'}, status=404)


if __name__ == '__main__':
  server = HTTPServer((HOST, PORT), Handler)
  print(f'API running on http://{HOST}:{PORT}')
  print(f'Using DB: {DB_PATH}')
  server.serve_forever()
