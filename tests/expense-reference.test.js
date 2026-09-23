import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { expenseInstructions, transcriptionPrompt, reviewResult } from '../api/_lib/expense-reference.js'
import { validateDraft } from '../api/_lib/voice.js'

const profile = JSON.parse(readFileSync(new URL('../shared/expense-reference.json', import.meta.url), 'utf8'))
test('reference retains real preferences and conflicting examples without financial history', () => {
  assert.equal(profile.movements, 155)
  assert.ok(profile.patterns.some(row => row.descripcion === 'Clase Ingles Olga' && row.tipo === 'Antojo'))
  assert.ok(profile.patterns.some(row => row.descripcion === 'Sueldo Ausenco' && row.tipo === null))
  assert.equal(profile.patterns.filter(row => row.descripcion === 'Barra Proteina').length, 2)
  for (const row of profile.patterns) assert.deepEqual(Object.keys(row).sort(), ['clasificacion', 'count', 'descripcion', 'tipo'])
  for (const category of ['Dap', 'Celular', 'Salud', 'Souvenir', 'Nieve']) assert.ok(profile.categories.includes(category))
})
test('prompt carries Santiago date, naming guidance, uncertainty and historical examples', () => {
  const prompt = expenseInstructions('2026-09-22')
  assert.ok(prompt.includes('2026-09-22'))
  assert.ok(prompt.includes('Tornillos M3 25 mm Allen'))
  assert.ok(prompt.includes('NO inventes "Olga"'))
  assert.ok(prompt.includes('varios movimientos independientes'))
  assert.ok(prompt.includes('No inventes') || prompt.includes('Nunca copies precios'))
  assert.ok(transcriptionPrompt.includes('Dmoov'))
})
test('incomplete interpretation remains editable but cannot be saved', () => {
  const draft = validateDraft({ fecha: '2026-09-22', descripcion: '', clasificacion: 'Otros', tipo: 'Necesidad', abono: 0, gasto: 0 })
  const review = reviewResult({ inferred_fields: ['tipo', 'tipo', 'unknown'], review_notes: ['Revisa el concepto.'] }, draft)
  assert.deepEqual(review.inferred_fields, ['tipo'])
  assert.ok(review.review_notes.some(note => note.includes('monto')))
  assert.ok(review.review_notes.some(note => note.includes('descripcion')))
  assert.throws(() => validateDraft(draft, true), /descripcion/)
  assert.throws(() => validateDraft({ ...draft, descripcion: 'Cafe' }, true), /monto/)
})
