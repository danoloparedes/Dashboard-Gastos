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

const COMPACT_NUMBER_FORMATTER = new Intl.NumberFormat('es-CL', { maximumFractionDigits: 1 })

export function formatCompactMoney(value) {
  if (value < 1000) return CLP_FORMATTER.format(value)
  const divisor = value >= 1_000_000 ? 1_000_000 : 1000
  const suffix = divisor === 1_000_000 ? 'M' : 'mil'
  return `$${COMPACT_NUMBER_FORMATTER.format(value / divisor)} ${suffix}`
}

export function toAmount(transaction) {
  if (transaction.gasto > 0) {
    return transaction.gasto
  }
  if (transaction.abono > 0) {
    return transaction.abono
  }
  return 0
}
