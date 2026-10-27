import { randomUUID } from 'node:crypto'
import { requireSession, accessResponse } from './_lib/auth.js'
import { createTransaction, deleteTransaction, updateTransaction } from './_lib/database.js'
import { validateTransaction } from './_lib/transaction-input.js'

export default { async fetch(request) {
  if (!['POST', 'PUT', 'DELETE'].includes(request.method)) {
    return Response.json({ error: 'method_not_allowed' }, { status: 405, headers: { Allow: 'POST, PUT, DELETE' } })
  }
  try { await requireSession(request) } catch (error) { return accessResponse(error) }
  let body
  try { body = await request.json() } catch { return Response.json({ error: 'JSON invalido.' }, { status: 400 }) }
  try {
    const id = body?.id
    if (request.method !== 'POST' && (!Number.isSafeInteger(id) || id < 1)) throw new Error('Identificador invalido.')
    const row = request.method === 'DELETE' ? null : validateTransaction(body)
    let result
    if (request.method === 'POST') result = await createTransaction({ ...row, externalId: `manual:${randomUUID()}` })
    else result = request.method === 'PUT' ? await updateTransaction(id, row) : await deleteTransaction(id)
    if (!result) return Response.json({ error: 'Movimiento no encontrado.' }, { status: 404 })
    return Response.json({ ok: true, id: request.method === 'POST' ? result : id }, { headers: { 'Cache-Control': 'no-store' } })
  } catch (error) {
    if (error.message?.includes('invalida') || error.message?.includes('invalido') || error.message?.includes('obligatoria') || error.message?.includes('Indica')) {
      return Response.json({ error: error.message }, { status: 400 })
    }
    console.error(error)
    return Response.json({ error: 'No se pudo guardar el movimiento.' }, { status: 500 })
  }
} }
