from __future__ import annotations

import json
import os
import re
import sqlite3
import tempfile
import time
import unicodedata
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib import error, request

import gspread
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')


def _resolve_db_path() -> str:
  configured = os.getenv('SQLITE_DB_PATH', './data/gastos.db')
  db_path = Path(configured)
  if not db_path.is_absolute():
    db_path = (BASE_DIR / db_path).resolve()
  return str(db_path)


def _resolve_credentials_path() -> Path:
  configured = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', './service-account.json').strip()
  credentials_path = Path(configured)
  if not credentials_path.is_absolute():
    credentials_path = (BASE_DIR / credentials_path).resolve()

  if not credentials_path.exists():
    alt_path = (BASE_DIR / 'sync' / 'service-account.json').resolve()
    if alt_path.exists():
      credentials_path = alt_path

  return credentials_path


def _normalize_text(value: str) -> str:
  normalized = unicodedata.normalize('NFKD', value)
  normalized = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
  return normalized.lower().strip()


def _parse_iso_date(text: str) -> str:
  raw = (text or '').strip()
  if not raw:
    return date.today().isoformat()

  normalized = _normalize_text(raw)
  today = date.today()
  if normalized in {'hoy', 'ahora'}:
    return today.isoformat()
  if normalized == 'ayer':
    return (today - timedelta(days=1)).isoformat()

  for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d'):
    try:
      return datetime.strptime(raw, fmt).strftime('%Y-%m-%d')
    except ValueError:
      continue

  return today.isoformat()


def _parse_amount(value: str | int | float | None) -> int:
  if value is None:
    return 0

  if isinstance(value, (int, float)):
    return int(round(float(value)))

  text = str(value).strip()
  if not text:
    return 0

  cleaned = text.replace('$', '').replace(' ', '')
  if ',' in cleaned and '.' in cleaned:
    if cleaned.rfind(',') > cleaned.rfind('.'):
      cleaned = cleaned.replace('.', '').replace(',', '.')
    else:
      cleaned = cleaned.replace(',', '')
  else:
    cleaned = cleaned.replace('.', '').replace(',', '')

  try:
    return int(round(float(cleaned)))
  except ValueError:
    return 0


def _extract_first_json(text: str) -> dict | None:
  start = text.find('{')
  end = text.rfind('}')
  if start == -1 or end == -1 or end <= start:
    return None

  candidate = text[start:end + 1]
  try:
    parsed = json.loads(candidate)
    if isinstance(parsed, dict):
      return parsed
  except json.JSONDecodeError:
    return None

  return None


def _normalize_tipo(value: str) -> str:
  normalized = _normalize_text(value)
  if normalized in {'ahorro'}:
    return 'Ahorro'
  if normalized in {'antojo'}:
    return 'Antojo'
  return 'Necesidad'


def _clean_merchant_name(raw_value: str) -> str:
  cleaned = raw_value.strip(" .,:;!?'\"()[]{}")
  cleaned = re.sub(r'\s+', ' ', cleaned)
  if not cleaned:
    return ''

  words = [word.capitalize() for word in cleaned.split(' ') if word]
  return ' '.join(words)


def _extract_description(text: str) -> str:
  raw = (text or '').strip()
  if not raw:
    return 'Gasto por voz'

  patterns = [
    r'\ben\s+([\w\s\-]+?)(?:\s+tipo\b|\s+clasificacion\b|\s+categoria\b|\s+hoy\b|\s+ayer\b|\s+con\b|\s+por\b|[\.,;]|$)',
    r'\bde\s+([\w\s\-]+?)(?:\s+tipo\b|\s+clasificacion\b|\s+categoria\b|\s+hoy\b|\s+ayer\b|\s+con\b|\s+por\b|[\.,;]|$)',
  ]

  for pattern in patterns:
    match = re.search(pattern, raw, flags=re.IGNORECASE)
    if not match:
      continue
    merchant = _clean_merchant_name(match.group(1))
    if merchant:
      return merchant

  # Fallback: keep a short readable phrase instead of the full transcript.
  compact = re.sub(r'\s+', ' ', raw).strip()
  return compact[:80] if len(compact) > 80 else compact


def _infer_category(normalized_text: str) -> str:
  explicit_match = re.search(r'(?:clasificacion|categoria)\s+([a-zA-Z]+)', normalized_text)
  if explicit_match:
    return explicit_match.group(1).capitalize()

  if 'ocio' in normalized_text:
    return 'Ocio'

  if any(token in normalized_text for token in ['super', 'mercado', 'almacen']):
    return 'Supermercado'

  if any(token in normalized_text for token in ['clase', 'clases']):
    return 'Estudio'

  if any(token in normalized_text for token in ['almuerzo', 'spid', 'brutal', 'comida', 'cena', 'desayuno', 'cafeteria']):
    return 'Comida'

  if any(token in normalized_text for token in ['uber', 'taxi', 'metro', 'bus', 'bencina', 'estacionamiento']):
    return 'Transporte'

  if any(token in normalized_text for token in ['farmacia', 'medico', 'salud']):
    return 'Salud'

  if any(token in normalized_text for token in ['cine', 'netflix', 'spotify', 'bar', 'pub', 'restaurante', 'juego']):
    return 'Ocio'

  if any(token in normalized_text for token in ['homecenter', 'sodimac', 'ikea']):
    return 'Ocio'

  return 'General'


def _heuristic_parse_expense(text: str) -> dict:
  normalized = _normalize_text(text)
  amount_match = re.search(r'(\d{1,3}(?:[\.,]\d{3})+|\d+)', normalized)
  amount = _parse_amount(amount_match.group(1) if amount_match else '0')

  tipo = 'Necesidad'
  if 'ahorro' in normalized:
    tipo = 'Ahorro'
  elif 'antojo' in normalized:
    tipo = 'Antojo'

  clasificacion = _infer_category(normalized)
  descripcion = _extract_description(text)

  return {
    'fecha': date.today().isoformat(),
    'descripcion': descripcion,
    'clasificacion': clasificacion,
    'tipo': tipo,
    'abono': 0,
    'gasto': amount,
  }


def transcribe_audio(audio_bytes: bytes, filename: str, text_override: str = '') -> tuple[str, str]:
  override = (text_override or '').strip()
  if override:
    return override, 'text-override'

  whisper_mode = os.getenv('VOICE_WHISPER_MODE', 'mock').strip().lower()
  if whisper_mode == 'mock':
    return 'gaste 12000 en supermercado tipo necesidad hoy', 'mock'

  if not audio_bytes:
    raise RuntimeError('No se recibio audio para transcripcion.')

  with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix or '.webm') as temp_file:
    temp_file.write(audio_bytes)
    temp_path = Path(temp_file.name)

  try:
    if whisper_mode == 'faster-whisper':
      try:
        from faster_whisper import WhisperModel
      except Exception as exc:  # pragma: no cover
        raise RuntimeError('faster-whisper no esta instalado. Usa VOICE_WHISPER_MODE=mock o instala faster-whisper.') from exc

      model_size = os.getenv('VOICE_WHISPER_MODEL', 'base')
      compute_type = os.getenv('VOICE_WHISPER_COMPUTE_TYPE', 'int8')
      model = WhisperModel(model_size, device='cpu', compute_type=compute_type)
      segments, _ = model.transcribe(str(temp_path), language='es')
      transcript = ' '.join(segment.text.strip() for segment in segments).strip()
      if not transcript:
        raise RuntimeError('Whisper no retorno texto para el audio enviado.')
      return transcript, 'faster-whisper'

    raise RuntimeError(f'Modo de whisper no soportado: {whisper_mode}')
  finally:
    try:
      temp_path.unlink(missing_ok=True)
    except Exception:
      pass


def interpret_expense_text(transcript: str) -> dict:
  model_name = os.getenv('VOICE_OLLAMA_MODEL', "qwen2.5:7b").strip()
  use_ollama = bool(model_name)

  if not use_ollama:
    return _heuristic_parse_expense(transcript)

  prompt = (
    'Eres un extractor de transacciones personales en Chile. '
    'Debes responder SOLO un JSON valido, sin markdown ni texto extra, con estas llaves exactas: '
    'fecha, descripcion, clasificacion, tipo, abono, gasto. '
    'Formato de salida obligatorio: '
    'fecha en DD-MM-YYYY; descripcion corta (solo comercio o concepto principal, sin frases largas); '
    'clasificacion en una sola categoria; tipo solo Ahorro, Antojo o Necesidad; '
    'abono y gasto enteros >= 0 sin separadores ni simbolo $. '
    'Usa estas categorias preferidas segun historico real: '
    'Sueldo, Fit, Transporte, Comida, Dpto, Ocio, Higiene, Rosario, Estudio, Social, General. '
    'Mapeo sugerido de ejemplos reales: '
    'Homecenter/Sodimac/Ikea/Tornillos/Filamento/Laca/Papel lija/Encerado snow -> Ocio; '
    'Dmoov/Mut/Costanera/Estacionamiento/Bencina/Uber/Taxi/Metro/Bus/Unired -> Transporte; '
    'Spid/Almuerzo/Cafe/Brutal/Restaurante/Desayuno/Cena -> Comida; '
    'Clase Ingles/Clase Portugues -> Estudio; '
    'Barra proteina/Wellhub -> Fit; '
    'Rosario/Flores/Ferrero/Cumple mes -> Rosario; '
    'Junta/Salida con amigos -> Social; '
    'Pasta de dientes/Corte de pelo/Barba -> Higiene; '
    'Arriendo/Seguro dpto -> Dpto; '
    'Sueldo/Pago sueldo -> Sueldo. '
    'Reglas de consistencia: '
    'si es ingreso, usar abono > 0, gasto = 0 y clasificacion Sueldo o General; '
    'si es egreso, usar gasto > 0 y abono = 0; '
    'si no hay fecha explicita, usa hoy; '
    'si no hay certeza de categoria, usa General; '
    'si no hay certeza de tipo, usa Necesidad. '
    'No inventes montos no mencionados.\n\n'
    f'Texto a extraer: {transcript}'
  )

  payload = json.dumps({
    'model': model_name,
    'prompt': prompt,
    'stream': False,
    'format': 'json',
  }).encode('utf-8')

  ollama_url = os.getenv('VOICE_OLLAMA_URL', 'http://127.0.0.1:11434/api/generate')
  req = request.Request(
    ollama_url,
    data=payload,
    method='POST',
    headers={'Content-Type': 'application/json'},
  )

  try:
    with request.urlopen(req, timeout=90) as response:
      body = response.read().decode('utf-8')
  except error.URLError as exc:
    raise RuntimeError(f'No se pudo consultar Ollama: {exc}') from exc

  parsed_response = json.loads(body)
  raw = str(parsed_response.get('response', '')).strip()

  model_json = _extract_first_json(raw)
  if not model_json:
    return _heuristic_parse_expense(transcript)

  return model_json


def normalize_draft(draft: dict) -> dict:
  normalized = {
    'fecha': _parse_iso_date(str(draft.get('fecha', ''))),
    'descripcion': str(draft.get('descripcion', '')).strip() or 'Gasto por voz',
    'clasificacion': str(draft.get('clasificacion', '')).strip() or 'General',
    'tipo': _normalize_tipo(str(draft.get('tipo', 'Necesidad'))),
    'abono': max(0, _parse_amount(draft.get('abono', 0))),
    'gasto': max(0, _parse_amount(draft.get('gasto', 0))),
  }

  if normalized['abono'] == 0 and normalized['gasto'] == 0:
    normalized['gasto'] = 1

  return normalized


def save_to_sqlite(draft: dict) -> dict:
  db_path = _resolve_db_path()
  external_id = f"voice:{datetime.utcnow().strftime('%Y%m%d%H%M%S')}:{uuid.uuid4().hex[:8]}"
  conn = sqlite3.connect(db_path)
  try:
    schema_path = (BASE_DIR / 'sync' / 'schema.sql').resolve()
    if schema_path.exists():
      with open(schema_path, 'r', encoding='utf-8') as schema_file:
        conn.executescript(schema_file.read())

    conn.execute(
      """
      INSERT INTO transactions (
        external_id, fecha, descripcion, clasificacion, tipo, abono, gasto
      ) VALUES (?, ?, ?, ?, ?, ?, ?)
      """,
      (
        external_id,
        draft['fecha'],
        draft['descripcion'],
        draft['clasificacion'],
        draft['tipo'],
        int(draft['abono']),
        int(draft['gasto']),
      ),
    )
    conn.commit()
  finally:
    conn.close()

  return {'external_id': external_id, 'db_path': db_path}


def save_to_google_sheets(draft: dict) -> dict:
  spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', '').strip()
  worksheet_name = os.getenv('GOOGLE_SHEETS_WORKSHEET', 'Gastos').strip() or 'Gastos'
  credentials = _resolve_credentials_path()

  if not spreadsheet_id:
    raise RuntimeError('Falta GOOGLE_SHEETS_SPREADSHEET_ID en backend/.env')
  if not credentials.exists():
    raise RuntimeError(f'No existe archivo de credenciales: {credentials}')

  client = gspread.service_account(filename=str(credentials))
  worksheet = client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
  worksheet.append_row(
    [
      draft['fecha'],
      draft['descripcion'],
      draft['clasificacion'],
      draft['tipo'],
      int(draft['abono']),
      int(draft['gasto']),
    ],
    value_input_option='USER_ENTERED',
  )

  return {'worksheet': worksheet_name, 'spreadsheet_id': spreadsheet_id}


def process_audio_to_draft(audio_bytes: bytes, filename: str, text_override: str = '') -> dict:
  started = time.perf_counter()
  transcript, transcription_engine = transcribe_audio(audio_bytes, filename, text_override=text_override)
  raw_draft = interpret_expense_text(transcript)
  draft = normalize_draft(raw_draft)
  elapsed_ms = int((time.perf_counter() - started) * 1000)
  ollama_model = os.getenv('VOICE_OLLAMA_MODEL', '').strip()

  return {
    'transcript': transcript,
    'draft': draft,
    'meta': {
      'transcription_engine': transcription_engine,
      'interpretation_engine': ollama_model if ollama_model else 'heuristic-parser',
      'elapsed_ms': elapsed_ms,
    },
  }


def save_draft(draft: dict, persist_target: str) -> dict:
  target = (persist_target or 'sqlite').strip().lower()
  normalized = normalize_draft(draft)
  results: dict[str, dict] = {}

  if target in {'sqlite', 'both'}:
    results['sqlite'] = save_to_sqlite(normalized)

  if target in {'sheets', 'both'}:
    results['sheets'] = save_to_google_sheets(normalized)

  if not results:
    raise RuntimeError(f'persist_target no soportado: {persist_target}')

  return {'draft': normalized, 'saved': results}
