import { randomUUID } from 'node:crypto'
import { upsertTransactions } from '../_lib/database.js'
import { endpoint, readJson, validateDraft, VoiceError } from '../_lib/voice.js'

export async function saveDraft(body, dependencies = { upsertTransactions }) {
  if (body.persist_target != null && body.persist_target !== 'postgres') {
    throw new VoiceError('El registro ahora se guarda solo en el dashboard. Recarga la pagina e intenta de nuevo.')
  }
  const draft = validateDraft(body.draft, true)
  const externalId = `voice:${randomUUID()}`
  await dependencies.upsertTransactions([{ ...draft, externalId }])
  return { draft, saved: { postgres: { external_id: externalId } } }
}

export default endpoint(async request => saveDraft(await readJson(request)))
