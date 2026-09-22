import pg from 'pg'
import { createHash } from 'node:crypto'
export const PASSWORD = 'test-password-only-123456'
export const TOKEN = 'a'.repeat(64)
export const COOKIE = `__Host-gastos_session=${TOKEN}`
const digest = text => createHash('sha256').update(text).digest('hex')
export function authFixture(t, signedIn = true) {
  const old = { ...process.env }
  process.env.ASSISTANT_PASSWORD = PASSWORD
  process.env.POSTGRES_URL = 'postgresql://localhost/test'
  process.env.ASSISTANT_DAILY_OPENAI_LIMIT = '100'
  t.after(() => {
    for (const key of ['ASSISTANT_PASSWORD', 'POSTGRES_URL', 'ASSISTANT_DAILY_OPENAI_LIMIT']) {
      if (old[key] === undefined) delete process.env[key]; else process.env[key] = old[key]
    }
  })
  const sessions = new Map(signedIn ? [[digest(TOKEN), { version: digest(PASSWORD), expires: Date.now() + 43200000 }]] : [])
  const buckets = new Map()
  const calls = []
  t.mock.method(pg.Pool.prototype, 'query', async (sql, args = []) => {
    calls.push(sql)
    if (sql.startsWith('CREATE')) return { rows: [] }
    if (sql.startsWith('INSERT INTO assistant_limits')) {
      const [key, units, seconds, max] = args
      let current = buckets.get(key)
      if (!current || current.expires <= Date.now()) current = { hits: 0, expires: Date.now() + seconds * 1000 }
      if (current.hits + units > max) return { rows: [] }
      current.hits += units
      buckets.set(key, current)
      return { rows: [{ hits: current.hits }] }
    }
    if (sql.startsWith('SELECT token_hash')) {
      const value = sessions.get(args[0])
      return { rows: value && value.version === args[1] && value.expires > Date.now() ? [{}] : [] }
    }
    if (sql.startsWith('INSERT INTO assistant_sessions')) {
      sessions.set(args[0], { version: args[1], expires: sql.includes("'infinity'::timestamptz") ? Infinity : Date.now() + 43200000 })
      return { rows: [] }
    }
    if (sql.startsWith('DELETE FROM assistant_sessions WHERE token_hash')) sessions.delete(args[0])
    else if (sql.startsWith('DELETE')) return { rows: [] }
    else throw new Error('Unexpected database operation in auth test')
    return { rows: [] }
  })
  return { sessions, buckets, calls }
}
