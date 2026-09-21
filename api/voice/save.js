import { randomUUID } from 'node:crypto'
import { upsertTransactions } from '../_lib/database.js'
import { appendVoiceToSheet } from '../_lib/sheets.js'
import { endpoint, readJson, validateDraft, VoiceError } from '../_lib/voice.js'

export async function saveDraft(body, dependencies = { upsertTransactions, appendVoiceToSheet }) {
  const draft = validateDraft(body.draft, true)
  const target = body.persist_target || 'postgres'
  if (!['postgres', 'sheets', 'both'].includes(target)) throw new VoiceError('Destino no soportado. Recarga la pagina y selecciona el destino nuevamente.')
  const saved = {}
  let externalId = `voice:${randomUUID()}`
  if (target === 'sheets' || target === 'both') {
    saved.sheets = await dependencies.appendVoiceToSheet(draft)
    // Use the same ID as sync so refreshing Sheets cannot duplicate this expense.
    externalId = saved.sheets.external_id
  }
  if (target === 'postgres' || target === 'both') {
    try { await dependencies.upsertTransactions([{ ...draft, externalId }]) }
    catch (error) {
      if (saved.sheets) throw new VoiceError('Se guardo en Google Sheets, pero fallo el dashboard. No repitas el guardado: usa Actualizar datos para sincronizar.', 502)
      throw error
    }
    saved.postgres = { external_id: externalId }
  }
  return { draft, saved }
}

export default endpoint(async request => saveDraft(await readJson(request)))
