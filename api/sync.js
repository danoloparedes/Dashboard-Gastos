import { syncGoogleSheet } from './_lib/sheets.js'
import { requireSession, accessResponse } from './_lib/auth.js'

export default { async fetch(request) {
  if (request.method !== 'POST') {
    return Response.json({ error: 'method_not_allowed' }, { status: 405, headers: { Allow: 'POST' } })
  }

  try { await requireSession(request) } catch (error) { return accessResponse(error) }
  try {
    return Response.json({ ok: true, result: await syncGoogleSheet() }, { headers: { 'Cache-Control': 'no-store' } })
  } catch {
    return Response.json({ error: 'No se pudo sincronizar Google Sheets.' }, { status: 500, headers: { 'Cache-Control': 'no-store' } })
  }
} }
