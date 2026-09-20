import { listTransactions } from './_lib/database.js'

export default async function handler(request, response) {
  if (request.method !== 'GET') {
    response.setHeader('Allow', 'GET')
    return response.status(405).json({ error: 'method_not_allowed' })
  }

  try {
    response.setHeader('Cache-Control', 'no-store, max-age=0')
    return response.status(200).json({ transactions: await listTransactions() })
  } catch (error) {
    console.error(error)
    return response.status(500).json({ error: error.message || 'database_error' })
  }
}