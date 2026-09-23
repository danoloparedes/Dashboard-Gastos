import { readFileSync } from 'node:fs'

const reference = JSON.parse(readFileSync(new URL('../../shared/expense-reference.json', import.meta.url), 'utf8'))
const instructions = readFileSync(new URL('../../shared/expense-instructions.txt', import.meta.url), 'utf8')
export const transcriptionPrompt = reference.transcription_prompt
export function expenseInstructions(today) {
  return `${instructions}\nFecha actual en America/Santiago: ${today}.\nReferencia historica (descripcion, clasificacion, tipo, frecuencia; null indica dato ausente):\n${JSON.stringify(reference.patterns)}`
}
export function reviewResult(raw, draft) {
  const fields = Object.keys(draft)
  const inferred_fields = Array.isArray(raw.inferred_fields) ? [...new Set(raw.inferred_fields.filter(field => fields.includes(field)))] : []
  const notes = Array.isArray(raw.review_notes) ? raw.review_notes.filter(note => typeof note === 'string').slice(0, 8) : []
  if (!draft.descripcion) notes.push('Completa la descripcion del movimiento.')
  if (!draft.abono && !draft.gasto) notes.push('Indica el monto antes de guardar.')
  return { inferred_fields, review_notes: [...new Set(notes)] }
}
