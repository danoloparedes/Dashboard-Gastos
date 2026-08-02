from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from voice_pipeline import process_audio_to_draft, save_draft

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

HOST = os.getenv('VOICE_API_HOST', '0.0.0.0')
PORT = int(os.getenv('VOICE_API_PORT', '8001'))


class Handler(BaseHTTPRequestHandler):
  def _send_json(self, payload: dict, status: int = 200) -> None:
    body = json.dumps(payload).encode('utf-8')
    self.send_response(status)
    self.send_header('Content-Type', 'application/json; charset=utf-8')
    self.send_header('Access-Control-Allow-Origin', '*')
    self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    self.send_header('Content-Length', str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def do_OPTIONS(self) -> None:
    self.send_response(204)
    self.send_header('Access-Control-Allow-Origin', '*')
    self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    self.end_headers()

  def do_GET(self) -> None:
    parsed = urlparse(self.path)

    if parsed.path == '/health':
      self._send_json({'ok': True, 'service': 'voice-api'})
      return

    self._send_json({'error': 'not_found'}, status=404)

  def _read_json(self) -> dict:
    length = int(self.headers.get('Content-Length', '0') or 0)
    if length <= 0:
      return {}

    raw = self.rfile.read(length)
    if not raw:
      return {}

    return json.loads(raw.decode('utf-8'))

  def _parse_multipart(self) -> tuple[bytes, str, str]:
    content_type = self.headers.get('Content-Type', '')
    length = int(self.headers.get('Content-Length', '0') or 0)
    body = self.rfile.read(length) if length > 0 else b''

    boundary_match = re.search(r'boundary=(?:"([^"]+)"|([^;]+))', content_type)
    if not boundary_match:
      raise RuntimeError('multipart/form-data invalido: boundary no encontrado.')

    boundary = (boundary_match.group(1) or boundary_match.group(2) or '').strip().encode('utf-8')
    if not boundary:
      raise RuntimeError('multipart/form-data invalido: boundary vacio.')

    delimiter = b'--' + boundary
    parts = body.split(delimiter)

    audio_bytes = b''
    filename = 'audio.webm'
    text_override = ''

    for raw_part in parts:
      part = raw_part.strip()
      if not part or part == b'--':
        continue

      if b'\r\n\r\n' not in part:
        continue

      header_bytes, payload = part.split(b'\r\n\r\n', 1)
      payload = payload.rstrip(b'\r\n')

      headers: dict[str, str] = {}
      for line in header_bytes.split(b'\r\n'):
        if b':' not in line:
          continue
        key, value = line.split(b':', 1)
        headers[key.decode('utf-8', errors='ignore').strip().lower()] = value.decode(
          'utf-8', errors='ignore'
        ).strip()

      disposition = headers.get('content-disposition', '')
      name_match = re.search(r'name="([^"]+)"', disposition)
      filename_match = re.search(r'filename="([^"]*)"', disposition)

      field_name = name_match.group(1) if name_match else ''

      if field_name == 'text_override':
        text_override = payload.decode('utf-8', errors='ignore').strip()
        continue

      if field_name == 'audio':
        audio_bytes = payload
        if filename_match and filename_match.group(1).strip():
          filename = filename_match.group(1).strip()

    return audio_bytes, filename, text_override

  def do_POST(self) -> None:
    parsed = urlparse(self.path)

    if parsed.path == '/api/voice/process':
      try:
        content_type = self.headers.get('Content-Type', '')

        if 'multipart/form-data' in content_type:
          audio_bytes, filename, text_override = self._parse_multipart()
          result = process_audio_to_draft(audio_bytes, filename, text_override=text_override)
        else:
          payload = self._read_json()
          text_override = str(payload.get('text_override', '')).strip()
          if not text_override:
            raise RuntimeError('Debes enviar multipart con audio o JSON con text_override.')
          result = process_audio_to_draft(b'', 'text.txt', text_override=text_override)

        self._send_json({'ok': True, 'result': result})
      except Exception as exc:  # pragma: no cover
        self._send_json({'ok': False, 'error': str(exc)}, status=500)
      return

    if parsed.path == '/api/voice/save':
      try:
        payload = self._read_json()
        draft = payload.get('draft') or {}
        persist_target = str(payload.get('persist_target', 'sqlite'))
        result = save_draft(draft, persist_target)
        self._send_json({'ok': True, 'result': result})
      except Exception as exc:  # pragma: no cover
        self._send_json({'ok': False, 'error': str(exc)}, status=500)
      return

    self._send_json({'error': 'not_found'}, status=404)


if __name__ == '__main__':
  server = HTTPServer((HOST, PORT), Handler)
  print(f'Voice API running on http://{HOST}:{PORT}')
  server.serve_forever()
