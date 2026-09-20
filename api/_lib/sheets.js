import { google } from 'googleapis'
import {
  countTransactions,
  deleteMissingSheetTransactions,
  upsertTransactions
} from './database.js'

const REQUIRED_HEADERS = ['fecha', 'descripcion', 'clasificacion', 'tipo', 'abono', 'gasto']

function normalizeText(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]/g, '')
}

function parseDate(value) {
  const text = String(value || '').trim()
  const match = text.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$/)
  if (match) return `${match[1]}-${match[2].padStart(2, '0')}-${match[3].padStart(2, '0')}`

  const reverseMatch = text.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$/)
  if (reverseMatch) {
    return `${reverseMatch[3]}-${reverseMatch[2].padStart(2, '0')}-${reverseMatch[1].padStart(2, '0')}`
  }

  return null
}

function parseMoney(value) {
  let cleaned = String(value || '').replace(/[$\s]/g, '')
  if (cleaned.includes(',') && cleaned.includes('.')) {
    cleaned =
      cleaned.lastIndexOf(',') > cleaned.lastIndexOf('.')
        ? cleaned.replaceAll('.', '').replace(',', '.')
        : cleaned.replaceAll(',', '')
  } else {
    cleaned = cleaned.replaceAll('.', '').replaceAll(',', '')
  }
  const amount = Number(cleaned)
  return Number.isFinite(amount) ? Math.round(amount) : 0
}

function getCredentials() {
  const raw = process.env.GOOGLE_SERVICE_ACCOUNT_JSON
  if (!raw) {
    throw new Error('Falta configurar GOOGLE_SERVICE_ACCOUNT_JSON en Vercel.')
  }

  try {
    return JSON.parse(raw)
  } catch {
    throw new Error('GOOGLE_SERVICE_ACCOUNT_JSON no contiene JSON valido.')
  }
}

export async function syncGoogleSheet() {
  const spreadsheetId = process.env.GOOGLE_SHEETS_SPREADSHEET_ID
  const worksheetName = process.env.GOOGLE_SHEETS_WORKSHEET || 'Gastos'
  if (!spreadsheetId) {
    throw new Error('Falta configurar GOOGLE_SHEETS_SPREADSHEET_ID en Vercel.')
  }

  const auth = new google.auth.GoogleAuth({
    credentials: getCredentials(),
    scopes: ['https://www.googleapis.com/auth/spreadsheets.readonly']
  })
  const sheets = google.sheets({ version: 'v4', auth })
  const response = await sheets.spreadsheets.values.get({
    spreadsheetId,
    range: `'${worksheetName.replace(/'/g, "''")}'!A:Z`
  })
  const [headers = [], ...records] = response.data.values || []
  const headerIndexes = Object.fromEntries(headers.map((header, index) => [normalizeText(header), index]))
  const rows = []
  let skipped = 0

  for (const [index, record] of records.entries()) {
    if (REQUIRED_HEADERS.some((header) => headerIndexes[header] === undefined)) {
      throw new Error('La hoja debe tener fecha, descripcion, clasificacion, tipo, abono y gasto.')
    }

    const fecha = parseDate(record[headerIndexes.fecha])
    if (!fecha) {
      skipped += 1
      continue
    }

    rows.push({
      externalId: `${worksheetName}:${index + 2}`,
      fecha,
      descripcion: String(record[headerIndexes.descripcion] || '').trim() || 'Sin descripcion',
      clasificacion: String(record[headerIndexes.clasificacion] || '').trim(),
      tipo: String(record[headerIndexes.tipo] || '').trim(),
      abono: parseMoney(record[headerIndexes.abono]),
      gasto: parseMoney(record[headerIndexes.gasto])
    })
  }

  await upsertTransactions(rows)
  const deleted = await deleteMissingSheetTransactions(
    worksheetName,
    rows.map((row) => row.externalId)
  )

  return {
    processed: records.length,
    imported: rows.length,
    skipped,
    deleted: deleted.rowCount || 0,
    total: await countTransactions()
  }
}