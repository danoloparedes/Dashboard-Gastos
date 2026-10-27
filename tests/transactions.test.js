import test from 'node:test'
import assert from 'node:assert/strict'
import { validateTransaction } from '../api/_lib/transaction-input.js'
import transaction from '../api/transaction.js'
import { authFixture } from './auth-fixture.js'
import { parseDate } from '../api/_lib/sheets.js'
import { upsertTransactions, withTransaction } from '../api/_lib/database.js'
import pg from 'pg'
import { formatCompactMoney } from '../src/data/transactions.js'

const valid = { fecha: '2026-10-25', descripcion: ' Mercado ', clasificacion: 'Comida', tipo: 'Necesidad', abono: 0, gasto: 1200 }

test('compact chart labels stay in Spanish and preserve CLP amounts for detail views', () => {
  assert.equal(formatCompactMoney(0), '$0')
  assert.equal(formatCompactMoney(999), '$999')
  assert.equal(formatCompactMoney(1200), '$1,2 mil')
  assert.equal(formatCompactMoney(1_406_447), '$1,4 M')
})

test('transaction input rejects invalid dates, amounts, empty descriptions and unknown types', () => {
  assert.equal(validateTransaction(valid).descripcion, 'Mercado')
  for (const row of [
    { ...valid, fecha: '2026-02-30' }, { ...valid, gasto: -1 },
    { ...valid, gasto: 0 }, { ...valid, abono: 50 },
    { ...valid, descripcion: ' ' }, { ...valid, tipo: 'Otros' },
    { ...valid, gasto: '1200' }
  ]) assert.throws(() => validateTransaction(row))
})

test('sheet dates reject impossible calendar days instead of deleting or importing incorrect rows', () => {
  assert.equal(parseDate('25/10/2026'), '2026-10-25')
  assert.equal(parseDate('2024-02-29'), '2024-02-29')
  assert.equal(parseDate('31/02/2026'), null)
  assert.equal(parseDate('2026-13-01'), null)
})

test('PostgreSQL sync rolls back on failure and releases its connection', async t => {
  const commands = []
  let released = false
  t.mock.method(pg.Pool.prototype, 'query', async () => ({ rows: [] }))
  t.mock.method(pg.Pool.prototype, 'connect', async () => ({
    query: async sql => { commands.push(sql); return { rows: [] } },
    release: () => { released = true }
  }))
  const old = process.env.POSTGRES_URL
  process.env.POSTGRES_URL = 'postgresql://localhost/test'
  t.after(() => { if (old === undefined) delete process.env.POSTGRES_URL; else process.env.POSTGRES_URL = old })
  await assert.rejects(withTransaction(async run => {
    await run('INSERT INTO transactions ...')
    throw new Error('failed')
  }), /failed/)
  assert.deepEqual(commands, ['BEGIN', 'INSERT INTO transactions ...', 'ROLLBACK'])
  assert.equal(released, true)
})

test('PostgreSQL imports a batch in one query with its external IDs intact', async () => {
  const calls = []
  const run = async (sql, values) => { calls.push({ sql, values }) }
  const rows = [
    { ...valid, externalId: 'Gastos:2' },
    { ...valid, externalId: 'Gastos:3', gasto: 3500 }
  ]
  await upsertTransactions(rows, run)
  assert.equal(calls.length, 1)
  assert.match(calls[0].sql, /ON CONFLICT \(external_id\)/)
  assert.deepEqual(JSON.parse(calls[0].values[0]).map(row => row.external_id), ['Gastos:2', 'Gastos:3'])
  await upsertTransactions([], run)
  assert.equal(calls.length, 1)
})

test('mutations require session and validate payload before writing', async t => {
  const db = authFixture(t, false)
  const request = (method, body) => new Request('https://dashboard.example/api/transaction', {
    method, headers: { 'X-Gastos-Request': '1', 'Content-Type': 'application/json' }, body: JSON.stringify(body)
  })
  assert.equal((await transaction.fetch(request('POST', valid))).status, 401)
  assert.equal((await transaction.fetch(request('DELETE', { id: 1 }))).status, 401)
  assert.equal(db.calls.length, 0)
})
