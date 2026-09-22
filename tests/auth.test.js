import test from 'node:test'
import assert from 'node:assert/strict'
import auth from '../api/auth/session.js'
import { consumeOpenAI } from '../api/_lib/auth.js'
import transcribe from '../api/voice/transcribe.js'
import interpret from '../api/voice/interpret.js'
import processVoice from '../api/voice/process.js'
import save from '../api/voice/save.js'
import sync from '../api/sync.js'
import transactions from '../api/transactions.js'
import pg from 'pg'
import { authFixture, PASSWORD, COOKIE } from './auth-fixture.js'
function request(method = 'POST', body = {}, headers = {}) {
  return new Request('https://dashboard.example/api/auth/session', {
    method, headers: { 'Content-Type': 'application/json', 'X-Gastos-Request': '1', ...headers },
    ...(method !== 'GET' ? { body: JSON.stringify(body) } : {})
  })
}

test('all private endpoints reject anonymous requests before database/OpenAI operations', async t => {
  const db = authFixture(t, false)
  t.mock.method(globalThis, 'fetch', () => { throw new Error('Must not call OpenAI') })
  for (const handler of [transcribe, interpret, processVoice, save, sync]) {
    assert.equal((await handler.fetch(request())).status, 401)
  }
  assert.equal(db.calls.length, 0)
})

test('persistent session survives years, renews cookie, supports logout and password revocation', async t => {
  const db = authFixture(t, false)
  assert.equal((await auth.fetch(request('GET'))).status, 200)
  const login = await auth.fetch(request('POST', { password: PASSWORD }))
  assert.equal(login.status, 200)
  const cookie = login.headers.get('set-cookie')
  assert.ok(cookie.includes('Max-Age=34560000'))
  for (const value of ['HttpOnly', 'Secure', 'SameSite=Strict', 'Path=/']) assert.ok(cookie.includes(value))
  const headers = { Cookie: cookie.split(';')[0] }
  assert.equal((await (await auth.fetch(request('GET', {}, headers))).json()).authenticated, true)
  process.env.ASSISTANT_PASSWORD = 'different-password-12345'
  assert.equal((await (await auth.fetch(request('GET', {}, headers))).json()).authenticated, false)
  process.env.ASSISTANT_PASSWORD = PASSWORD
  const future = Date.now() + 10 * 365 * 86400000
  t.mock.method(Date, 'now', () => future)
  const resumed = await auth.fetch(request('GET', {}, headers))
  assert.equal((await resumed.json()).authenticated, true)
  assert.equal(resumed.headers.get('set-cookie'), cookie)
  assert.equal((await auth.fetch(request('DELETE', {}, headers))).status, 200)
  assert.equal(db.sessions.size, 0)
})

test('bad passwords are rate limited across requests and cannot create sessions', async t => {
  const db = authFixture(t, false)
  for (let i = 0; i < 5; i++) assert.equal((await auth.fetch(request('POST', { password: 'wrong' }))).status, 401)
  assert.equal((await auth.fetch(request('POST', { password: PASSWORD }))).status, 429)
  assert.equal(db.sessions.size, 0)
})

test('cross-origin requests, missing custom header, forged cookie and missing configuration fail closed', async t => {
  authFixture(t)
  assert.equal((await interpret.fetch(request('POST', {}, { Cookie: COOKIE, Origin: 'https://evil.example' }))).status, 403)
  assert.equal((await interpret.fetch(request('POST', {}, { Cookie: COOKIE, 'X-Gastos-Request': '' }))).status, 403)
  assert.equal((await interpret.fetch(request('POST', {}, { Cookie: '__Host-gastos_session=' + 'b'.repeat(64) }))).status, 401)
  delete process.env.ASSISTANT_PASSWORD
  assert.equal((await interpret.fetch(request('POST', {}, { Cookie: COOKIE }))).status, 503)
})

test('OpenAI global quota blocks calls even with a valid session', async t => {
  authFixture(t)
  process.env.ASSISTANT_DAILY_OPENAI_LIMIT = '2'
  await consumeOpenAI()
  await consumeOpenAI()
  await assert.rejects(consumeOpenAI(), error => error.status === 429)
})

test('public transactions keep the same response shape without auth or new environment variables', async t => {
  t.mock.method(pg.Pool.prototype, 'query', async sql => ({ rows: sql.includes('SELECT fecha') ? [{ fecha: '2026-09-21', abono: '0', gasto: '2500' }] : [] }))
  const old = process.env.POSTGRES_URL
  process.env.POSTGRES_URL = 'postgresql://localhost/test'
  t.after(() => { if (old === undefined) delete process.env.POSTGRES_URL; else process.env.POSTGRES_URL = old })
  let payload
  const response = { setHeader() {}, status(code) { assert.equal(code, 200); return this }, json(body) { payload = body } }
  await transactions({ method: 'GET' }, response)
  assert.equal(payload.transactions[0].gasto, 2500)
})
