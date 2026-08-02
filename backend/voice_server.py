from __future__ import annotations

import cgi
import json
import os
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
    form = cgi.FieldStorage(
      fp=self.rfile,
      headers=self.headers,
      environ={
        'REQUEST_METHOD': 'POST',
        'CONTENT_TYPE': self.headers.get('Content-Type', ''),
      },
    )

    file_item = form['audio'] if 'audio' in form else None
    text_override = form.getfirst('text_override', '')

    if file_item is None or not getattr(file_item, 'file', None):
      return b'', 'audio.webm', text_override

    filename = getattr(file_item, 'filename', 'audio.webm') or 'audio.webm'
    audio_bytes = file_item.file.read()
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
