import { syncGoogleSheet } from './_lib/sheets.js'

export default async function handler(request, response) {
  if (request.method !== 'POST') {
    response.setHeader('Allow', 'POST')
    return response.status(405).json({ error: 'method_not_allowed' })
  }

  try {
    return response.status(200).json({ ok: true, result: await syncGoogleSheet() })
  } catch (error) {
    console.error(error)
    return response.status(500).json({ ok: false, error: error.message || 'sync_error' })
  }
}