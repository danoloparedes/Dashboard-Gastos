const API_BASE = '/api'
const REQUEST_TIMEOUT_MS = 8000

function buildFallbackBase() {
  const host = window.location.hostname || 'localhost'
  return `http://${host}:8000/api`
}

export async function fetchTransactions() {
  const primary = await fetchWithTimeout(`${API_BASE}/transactions`)

  if (primary.ok) {
    const payload = await primary.json()
    return payload.transactions || []
  }

  const fallbackUrl = `${buildFallbackBase()}/transactions`
  const fallback = await fetchWithTimeout(fallbackUrl)

  if (fallback.ok) {
    const payload = await fallback.json()
    return payload.transactions || []
  }

  throw new Error(`Error cargando transacciones (${primary.status})`)
}

async function fetchWithTimeout(url) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

  try {
    return await fetch(url, { signal: controller.signal })
  } catch (error) {
    if (error && error.name === 'AbortError') {
      throw new Error('Timeout al consultar API')
    }
    throw error
  } finally {
    clearTimeout(timer)
  }
}
