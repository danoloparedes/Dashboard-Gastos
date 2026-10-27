export function validateTransaction(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('Movimiento invalido.')
  const { fecha, descripcion, clasificacion, tipo, abono, gasto } = input
  if (typeof fecha !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(fecha) ||
      !Number.isFinite(Date.parse(`${fecha}T00:00:00Z`)) ||
      new Date(`${fecha}T00:00:00Z`).toISOString().slice(0, 10) !== fecha) throw new Error('Fecha invalida.')
  if (typeof descripcion !== 'string' || !descripcion.trim() || descripcion.length > 500) throw new Error('Descripcion obligatoria (maximo 500 caracteres).')
  if (typeof clasificacion !== 'string' || clasificacion.length > 100) throw new Error('Clasificacion invalida.')
  if (!['Ahorro', 'Antojo', 'Necesidad'].includes(tipo)) throw new Error('Tipo invalido.')
  if (![abono, gasto].every(value => Number.isSafeInteger(value) && value >= 0 && value <= 1_000_000_000_000) ||
      (abono > 0) === (gasto > 0)) throw new Error('Indica solo un abono o gasto positivo.')
  return { fecha, descripcion: descripcion.trim(), clasificacion: clasificacion.trim(), tipo, abono, gasto }
}
