export const MONTHS = [
  'Enero',
  'Febrero',
  'Marzo',
  'Abril',
  'Mayo',
  'Junio',
  'Julio',
  'Agosto',
  'Septiembre',
  'Octubre',
  'Noviembre',
  'Diciembre'
]

export const TYPES = ['Ahorro', 'Antojo', 'Necesidad']

export const CLP_FORMATTER = new Intl.NumberFormat('es-CL', {
  style: 'currency',
  currency: 'CLP',
  maximumFractionDigits: 0
})

export function toAmount(transaction) {
  if (transaction.gasto > 0) {
    return transaction.gasto
  }
  if (transaction.abono > 0) {
    return transaction.abono
  }
  return 0
}
