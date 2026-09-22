import { createHash, randomBytes, timingSafeEqual } from 'node:crypto'
import { query } from './database.js'

const COOKIE = '__Host-gastos_session'
const COOKIE_AGE = 34560000 // 400 days, refreshed when opening the assistant.
export function persistentCookie(request) {
  const value = token(request)
  return value ? cookieFor(value) : null
}
function cookieFor(value) {
  return `${COOKIE}=${value}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=${COOKIE_AGE}`
}
const digest = value => createHash('sha256').update(value).digest('hex')
export class AccessError extends Error {
  constructor(message, status = 401) { super(message); this.status = status }
}
function passwordVersion() {
  const password = process.env.ASSISTANT_PASSWORD
  if (!password || password.length < 16) throw new AccessError('Configura ASSISTANT_PASSWORD con al menos 16 caracteres en el servidor.', 503)
  return digest(password)
}
function token(request) {
  const value = request.headers.get('cookie')?.split(';').map(part => part.trim()).find(part => part.startsWith(`${COOKIE}=`))?.slice(COOKIE.length + 1)
  return /^[a-f0-9]{64}$/.test(value || '') ? value : null
}
export function sameOrigin(request) {
  if (request.headers.get('x-gastos-request') !== '1') throw new AccessError('Solicitud no permitida.', 403)
  const origin = request.headers.get('origin')
  if (origin && origin !== new URL(request.url).origin) throw new AccessError('Origen no permitido.', 403)
  if (request.headers.get('sec-fetch-site') === 'cross-site') throw new AccessError('Origen no permitido.', 403)
}
async function schema() {
  await query(`CREATE TABLE IF NOT EXISTS assistant_sessions (
    token_hash TEXT PRIMARY KEY, password_version TEXT NOT NULL, expires_at TIMESTAMPTZ NOT NULL
  ); CREATE TABLE IF NOT EXISTS assistant_limits (
    bucket TEXT PRIMARY KEY, hits INTEGER NOT NULL, expires_at TIMESTAMPTZ NOT NULL
  );`)
}
export async function limit(name, maximum, seconds, units = 1) {
  await schema()
  const result = await query(`INSERT INTO assistant_limits (bucket, hits, expires_at)
    VALUES ($1, $2, NOW() + $3 * INTERVAL '1 second')
    ON CONFLICT (bucket) DO UPDATE SET
      hits = CASE WHEN assistant_limits.expires_at <= NOW() THEN $2 ELSE assistant_limits.hits + $2 END,
      expires_at = CASE WHEN assistant_limits.expires_at <= NOW() THEN NOW() + $3 * INTERVAL '1 second' ELSE assistant_limits.expires_at END
    WHERE assistant_limits.expires_at <= NOW() OR assistant_limits.hits + $2 <= $4
    RETURNING hits`, [name, units, seconds, maximum])
  if (!result.rows.length) throw new AccessError('Limite de solicitudes alcanzado. Intenta mas tarde.', 429)
}
export async function session(request) {
  const version = passwordVersion()
  const value = token(request)
  if (!value) return false
  await schema()
  const result = await query('SELECT token_hash FROM assistant_sessions WHERE token_hash = $1 AND password_version = $2 AND expires_at > NOW()', [digest(value), version])
  return result.rows.length > 0
}
export async function requireSession(request) {
  sameOrigin(request)
  if (!await session(request)) throw new AccessError('Ingresa la contraseña para continuar.')
  await limit('private-actions', 30, 60)
}
export async function consumeOpenAI() {
  const maximum = Number(process.env.ASSISTANT_DAILY_OPENAI_LIMIT || 100)
  if (!Number.isInteger(maximum) || maximum < 1 || maximum > 10000) throw new AccessError('ASSISTANT_DAILY_OPENAI_LIMIT debe ser un entero entre 1 y 10000.', 503)
  await limit('openai-daily', maximum, 86400)
}
export async function login(request) {
  sameOrigin(request)
  const version = passwordVersion()
  await limit('login-global', 60, 900)
  const ip = request.headers.get('x-vercel-forwarded-for') || request.headers.get('x-forwarded-for') || 'unknown'
  await limit(`login:${digest(ip)}`, 5, 900)
  let body
  try { body = await request.json() } catch { throw new AccessError('JSON invalido.', 400) }
  if (typeof body?.password !== 'string' || body.password.length > 1024 || !timingSafeEqual(Buffer.from(digest(body.password)), Buffer.from(version))) throw new AccessError('Contraseña incorrecta.')
  const value = randomBytes(32).toString('hex')
  await query('DELETE FROM assistant_sessions WHERE expires_at <= NOW()')
  await query('DELETE FROM assistant_limits WHERE expires_at <= NOW()')
  const old = token(request)
  if (old) await query('DELETE FROM assistant_sessions WHERE token_hash = $1', [digest(old)])
  await query("INSERT INTO assistant_sessions (token_hash, password_version, expires_at) VALUES ($1, $2, 'infinity'::timestamptz)", [digest(value), version])
  return cookieFor(value)
}
export async function logout(request) {
  sameOrigin(request)
  const value = token(request)
  if (value) { await schema(); await query('DELETE FROM assistant_sessions WHERE token_hash = $1', [digest(value)]) }
  return `${COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0`
}
export function accessResponse(error) {
  return Response.json({ error: error instanceof AccessError ? error.message : 'No se pudo verificar el acceso. Revisa la conexion del servidor.' }, {
    status: error instanceof AccessError ? error.status : 503, headers: { 'Cache-Control': 'no-store' }
  })
}
