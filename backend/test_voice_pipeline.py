import json
import os
import unittest
from unittest.mock import patch

import httpx
from openai import OpenAI

import voice_pipeline as voice


class VoicePipelineTests(unittest.TestCase):
  def setUp(self):
    self.env = patch.dict(os.environ, {
      'OPENAI_API_KEY': 'test-only',
      'OPENAI_TRANSCRIPTION_MODEL': 'gpt-4o-mini-transcribe',
      'OPENAI_EXPENSE_MODEL': 'gpt-4o-mini',
    })
    self.env.start()
    self.addCleanup(self.env.stop)
    self.draft = dict(fecha='2026-09-21', descripcion='Cafe', clasificacion='Comida',
                      tipo='Necesidad', abono=0, gasto=2500)

  def client(self, handler):
    return OpenAI(api_key='test-only', max_retries=0,
                  http_client=httpx.Client(transport=httpx.MockTransport(handler)))

  def response(self, draft):
    return httpx.Response(200, json={
      'id': 'resp_test', 'object': 'response', 'created_at': 0,
      'model': 'gpt-4o-mini', 'status': 'completed',
      'output': [{'type': 'message', 'id': 'msg_test', 'role': 'assistant',
                  'status': 'completed', 'content': [
                    {'type': 'output_text', 'text': json.dumps(draft), 'annotations': []}]}],
    })

  def test_audio_and_structured_expense_with_real_sdk(self):
    calls = []
    def handler(request):
      calls.append(request.url.path)
      if request.url.path.endswith('/audio/transcriptions'):
        self.assertIn(b'clip.m4a', request.content)
        self.assertIn(b'audio-bytes', request.content)
        return httpx.Response(200, json={'text': 'Gaste 2500 en cafe'})
      body = json.loads(request.content)
      self.assertEqual(body['input'], 'Gaste 2500 en cafe')
      self.assertTrue(body['text']['format']['strict'])
      self.assertFalse(body['store'])
      return self.response(self.draft)
    with patch.object(voice, '_openai_client', side_effect=lambda: self.client(handler)):
      result = voice.process_audio_to_draft(b'audio-bytes', 'clip.m4a')
    self.assertEqual(result['draft'], self.draft)
    self.assertEqual(len(calls), 2)

  def test_manual_text_needs_no_transcription_call(self):
    with patch.object(voice, '_openai_client') as client:
      self.assertEqual(voice.transcribe_audio(b'', '', ' hola '), ('hola', 'text-override'))
      client.assert_not_called()

  def test_missing_key(self):
    with patch.dict(os.environ, {'OPENAI_API_KEY': ''}):
      with self.assertRaisesRegex(RuntimeError, 'OPENAI_API_KEY'):
        voice.transcribe_audio(b'audio', 'voice.webm')

  def test_provider_errors_are_sanitized(self):
    for status, message in [(401, 'clave'), (429, 'cuota'), (500, 'procesar')]:
      with self.subTest(status=status):
        handler = lambda req: httpx.Response(status, json={'error': {'message': 'secret-provider-detail'}})
        with patch.object(voice, '_openai_client', side_effect=lambda: self.client(handler)):
          with self.assertRaisesRegex(RuntimeError, message) as error:
            voice.interpret_expense_text('cafe')
          self.assertNotIn('secret-provider-detail', str(error.exception))

  def test_incomplete_and_invalid_outputs_are_rejected(self):
    for payload in [dict(self.draft, fecha='bad'), dict(self.draft, gasto=-1), {}, []]:
      with patch.object(voice, '_openai_client', side_effect=lambda: self.client(lambda req: self.response(payload))):
        with self.assertRaisesRegex(RuntimeError, 'formato invalido'):
          voice.interpret_expense_text('cafe')
    with patch.object(voice, '_openai_client', side_effect=lambda: self.client(lambda req: httpx.Response(
        200, json={'id': 'resp_test', 'status': 'incomplete', 'output': []}))):
      with self.assertRaisesRegex(RuntimeError, 'completo'):
        voice.interpret_expense_text('cafe')

  def test_no_invented_amount_or_save(self):
    draft = voice.normalize_draft(dict(self.draft, gasto=0))
    self.assertEqual(draft['gasto'], 0)
    with patch.object(voice, 'save_to_sqlite') as save:
      with self.assertRaisesRegex(RuntimeError, 'monto'):
        voice.save_draft(draft, 'sqlite')
      save.assert_not_called()

  def test_audio_validation_before_api_call(self):
    with patch.object(voice, '_openai_client') as client:
      for audio, filename in [(b'', 'voice.webm'), (b'bytes', 'voice.exe'), (b'x' * 25_000_000, 'voice.wav')]:
        with self.assertRaises(RuntimeError):
          voice.transcribe_audio(audio, filename)
      client.assert_not_called()


if __name__ == '__main__':
  unittest.main()
