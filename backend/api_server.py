from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from assistant_auth import require_session, AccessError
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from sync_google_sheet import run_sync
from sync.db import get_connection, init_schema

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
    SELECT id, fecha, descripcion, clasificacion, tipo, abono, gasto
    FROM transactions
    ORDER BY fecha ASC, id ASC
    """
  ).fetchall()
  conn.close()

  return [
    {
      'id': row['id'],
      'fecha': row['fecha'],
      'descripcion': row['descripcion'] or '',
      'clasificacion': row['clasificacion'] or '',
      'tipo': row['tipo'] or '',
      'abono': int(row['abono'] or 0),
      'gasto': int(row['gasto'] or 0),
    }
    for row in rows
  ]


def validate_transaction(body):
  if not isinstance(body, dict):
    raise ValueError('Movimiento invalido.')
  fecha = body.get('fecha')
  try:
    if not isinstance(fecha, str) or date.fromisoformat(fecha).isoformat() != fecha:
      raise ValueError()
  except (ValueError, TypeError):
    raise ValueError('Fecha invalida.')
  descripcion = body.get('descripcion')
  clasificacion = body.get('clasificacion')
  if not isinstance(descripcion, str) or not descripcion.strip() or len(descripcion) > 500:
    raise ValueError('Descripcion obligatoria (maximo 500 caracteres).')
  if not isinstance(clasificacion, str) or len(clasificacion) > 100:
    raise ValueError('Clasificacion invalida.')
  tipo = body.get('tipo')
  if tipo not in ('Ahorro', 'Antojo', 'Necesidad'):
    raise ValueError('Tipo invalido.')
  abono, gasto = body.get('abono'), body.get('gasto')
  if any(type(value) is not int or not 0 <= value <= 1_000_000_000_000 for value in (abono, gasto)) or (abono > 0) == (gasto > 0):
    raise ValueError('Indica solo un abono o gasto positivo.')
  return (fecha, descripcion.strip(), clasificacion.strip(), tipo, abono, gasto)


def mutate_transaction(method, body):
  if not isinstance(body, dict):
    raise ValueError('Movimiento invalido.')
  row = validate_transaction(body) if method != 'DELETE' else None
  identifier = body.get('id')
  if method != 'POST' and (type(identifier) is not int or identifier < 1):
    raise ValueError('Identificador invalido.')
  conn = get_connection(DB_PATH)
  try:
    init_schema(conn, str(BASE_DIR / 'sync' / 'schema.sql'))
    with conn:
      if method == 'POST':
        cursor = conn.execute('INSERT INTO transactions (external_id, fecha, descripcion, clasificacion, tipo, abono, gasto) VALUES (?, ?, ?, ?, ?, ?, ?)', (f'manual:{uuid.uuid4()}', *row))
        return cursor.lastrowid
      old = conn.execute('SELECT external_id FROM transactions WHERE id=?', (identifier,)).fetchone()
      if not old:
        return None
      conn.execute('INSERT OR IGNORE INTO sheet_protections (external_id) VALUES (?)', (old['external_id'],))
      if method == 'PUT':
        conn.execute('UPDATE transactions SET fecha=?, descripcion=?, clasificacion=?, tipo=?, abono=?, gasto=?, updated_at=CURRENT_TIMESTAMP WHERE id=?', (*row, identifier))
      else:
        conn.execute('DELETE FROM transactions WHERE id=?', (identifier,))
      return identifier
  finally:
    conn.close()


class Handler(BaseHTTPRequestHandler):
  def _send_json(self, payload: dict, status: int = 200) -> None:
    body = json.dumps(payload).encode('utf-8')
    self.send_response(status)
    self.send_header('Content-Type', 'application/json; charset=utf-8')
    if self.command == 'GET':
      self.send_header('Access-Control-Allow-Origin', '*')
    self.send_header('Content-Length', str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def do_OPTIONS(self) -> None:
    self.send_response(204)
    self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    self.end_headers()

  def do_POST(self) -> None:
    parsed = urlparse(self.path)

    if parsed.path == '/api/transaction':
      self._mutate_transaction()
      return

    if parsed.path == '/api/sync':
      try:
        require_session(self)
        result = run_sync_now()
        self._send_json({'ok': True, 'result': result})
      except AccessError as exc:
        self._send_json({'error': str(exc)}, status=exc.status)
      except Exception as exc:  # pragma: no cover
        self._send_json({'ok': False, 'error': str(exc)}, status=500)
      return

    self._send_json({'error': 'not_found'}, status=404)

  def do_PUT(self) -> None:
    self._mutate_transaction()

  def do_DELETE(self) -> None:
    self._mutate_transaction()

  def _mutate_transaction(self) -> None:
    if urlparse(self.path).path != '/api/transaction':
      self._send_json({'error': 'not_found'}, status=404)
      return
    try:
      require_session(self)
      size = int(self.headers.get('Content-Length', '0'))
      if not 0 < size <= 4096:
        raise ValueError('Solicitud invalida.')
      body = json.loads(self.rfile.read(size))
      identifier = mutate_transaction(self.command, body)
      if identifier is None:
        self._send_json({'error': 'Movimiento no encontrado.'}, status=404)
      else:
        self._send_json({'ok': True, 'id': identifier})
    except AccessError as exc:
      self._send_json({'error': str(exc)}, status=exc.status)
    except (ValueError, TypeError) as exc:
      self._send_json({'error': str(exc) if isinstance(exc, ValueError) else 'Solicitud invalida.'}, status=400)
    except Exception:
      self._send_json({'error': 'No se pudo guardar el movimiento.'}, status=500)

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
