import test from 'node:test'
import assert from 'node:assert/strict'
import transcribe from '../api/voice/transcribe.js'
import interpret from '../api/voice/interpret.js'
import processVoice from '../api/voice/process.js'
import config from '../api/voice/config.js'
import save, { saveDraft } from '../api/voice/save.js'
import { validateDraft } from '../api/_lib/voice.js'

const draft = { fecha: '2026-09-21', descripcion: 'Cafe', clasificacion: 'Comida', tipo: 'Necesidad', abono: 0, gasto: 2500 }
function env(t, key, value) {
  const previous = process.env[key]
  process.env[key] = value
  t.after(() => { if (previous === undefined) delete process.env[key]; else process.env[key] = previous })
}
function json(body) {
  return new Request('http://localhost/api/voice', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
}
function audio(bytes = new Uint8Array([0, 32, 13, 10, 255])) {
  const form = new FormData()
  form.append('audio', new Blob([bytes], { type: 'audio/mp4' }), 'voice.mp4')
  return new Request('http://localhost/api/voice/transcribe', { method: 'POST', body: form })
}
function completed(value = draft) {
  return Response.json({ status: 'completed', output: [{ type: 'message', content: [{ type: 'output_text', text: JSON.stringify(value) }] }] })
}

test('voice endpoints work without an external voice URL', async t => {
  t.mock.method(globalThis, 'fetch', async () => { throw new Error('Unexpected network') })
  assert.equal((await config.fetch(new Request('http://localhost'))).status, 200)
  const settings = await (await config.fetch(new Request('http://localhost'))).json()
  assert.equal(settings.result.default_target, 'postgres')
  for (const handler of [transcribe, interpret, processVoice, save]) {
    const result = await handler.fetch(new Request('http://localhost'))
    assert.equal(result.status, 405)
    assert.equal(result.headers.get('Allow'), 'POST')
  }
  const result = await (await transcribe.fetch(json({ text_override: '  Cafe  ' }))).json()
  assert.equal(result.result.transcript, 'Cafe')
  assert.equal(result.result.meta.transcription_engine, 'text-override')
})

test('multipart audio bytes and filename reach OpenAI intact', async t => {
  env(t, 'OPENAI_API_KEY', 'test-key')
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, 'https://api.openai.com/v1/audio/transcriptions')
    assert.equal(options.headers.Authorization, 'Bearer test-key')
    assert.equal(options.body.get('file').name, 'voice.mp4')
    assert.deepEqual(new Uint8Array(await options.body.get('file').arrayBuffer()), new Uint8Array([0, 32, 13, 10, 255]))
    return Response.json({ text: 'Gaste 2500 en cafe' })
  })
  const result = await transcribe.fetch(audio())
  assert.equal(result.status, 200)
  assert.equal((await result.json()).result.transcript, 'Gaste 2500 en cafe')
})

test('combined endpoint transcribes and extracts a strict draft', async t => {
  env(t, 'OPENAI_API_KEY', 'test-key')
  const calls = []
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    calls.push(url)
    if (url.endsWith('transcriptions')) return Response.json({ text: 'Gaste 2500 en cafe' })
    const body = JSON.parse(options.body)
    assert.equal(body.input, 'Gaste 2500 en cafe')
    assert.equal(body.text.format.strict, true)
    assert.equal(body.store, false)
    return completed()
  })
  const response = await processVoice.fetch(audio())
  assert.equal(response.status, 200)
  const result = (await response.json()).result
  assert.deepEqual(result.draft, draft)
  assert.ok(result.meta.transcription)
  assert.ok(result.meta.interpretation)
  assert.equal(calls.length, 2)
})

test('invalid audio, text, JSON and missing key are rejected', async t => {
  env(t, 'OPENAI_API_KEY', '')
  t.mock.method(globalThis, 'fetch', async () => { throw new Error('Unexpected network') })
  assert.equal((await transcribe.fetch(audio())).status, 503)
  assert.equal((await transcribe.fetch(audio(new Uint8Array(4_000_001)))).status, 413)
  assert.equal((await transcribe.fetch(audio(new Uint8Array()))).status, 400)
  assert.equal((await interpret.fetch(json({ transcript: '' }))).status, 400)
  assert.equal((await interpret.fetch(new Request('http://localhost', { method: 'POST', body: '{' }))).status, 400)
})

test('provider errors and incomplete/refused/invalid outputs are safe', async t => {
  env(t, 'OPENAI_API_KEY', 'test-key')
  let providerResponse
  t.mock.method(globalThis, 'fetch', async () => providerResponse)
  for (const status of [401, 429, 500]) {
    providerResponse = Response.json({ error: 'secret-provider-detail' }, { status })
    const response = await interpret.fetch(json({ transcript: 'cafe' }))
    assert.equal(response.status, status === 429 ? 429 : 502)
    assert.ok(!(await response.text()).includes('secret-provider-detail'))
  }
  for (const value of [{ ...draft, fecha: '2026-02-30' }, { ...draft, gasto: -1 }, {}, []]) {
    providerResponse = completed(value)
    assert.equal((await interpret.fetch(json({ transcript: 'cafe' }))).status, 502)
  }
  providerResponse = Response.json({ status: 'incomplete', output: [] })
  assert.equal((await interpret.fetch(json({ transcript: 'cafe' }))).status, 502)
  providerResponse = Response.json({ status: 'completed', output: [{ content: [{ type: 'refusal' }] }] })
  assert.equal((await interpret.fetch(json({ transcript: 'cafe' }))).status, 422)
})

test('saving uses PostgreSQL by default and sheet row IDs avoid sync duplicates', async () => {
  const rows = []
  let sheetWrites = 0
  const dependencies = {
    upsertTransactions: async batch => rows.push(...batch),
    appendVoiceToSheet: async () => { sheetWrites++; return { external_id: 'Gastos:42' } }
  }
  const result = await saveDraft({ draft }, dependencies)
  assert.ok(result.saved.postgres.external_id.startsWith('voice:'))
  assert.equal(sheetWrites, 0)
  await saveDraft({ draft, persist_target: 'both' }, dependencies)
  assert.equal(rows[1].externalId, 'Gastos:42')
  assert.equal(sheetWrites, 1)
  await saveDraft({ draft, persist_target: 'sheets' }, dependencies)
  assert.equal(rows.length, 2)
  await assert.rejects(saveDraft({ draft, persist_target: 'sqlite' }, dependencies), /Destino/)
  await assert.rejects(saveDraft({ draft: { ...draft, gasto: 0 } }, dependencies), /monto/)
  assert.equal(validateDraft({ ...draft, gasto: 0 }).gasto, 0)
})

test('partial save explicitly reports that Sheets succeeded', async () => {
  await assert.rejects(saveDraft({ draft, persist_target: 'both' }, {
    appendVoiceToSheet: async () => ({ external_id: 'Gastos:42' }),
    upsertTransactions: async () => { throw new Error('db secret') }
  }), /No repitas el guardado/)
})
