const API_BASE = '/api'
const REQUEST_TIMEOUT_MS = 8000
const SYNC_TIMEOUT_MS = 90000

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

export async function triggerSync() {
  const primary = await fetchWithTimeout(
    `${API_BASE}/sync`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    },
    SYNC_TIMEOUT_MS
  )

  if (primary.ok) {
    const payload = await primary.json()
    return payload.result || null
  }

  const fallbackUrl = `${buildFallbackBase()}/sync`
  const fallback = await fetchWithTimeout(
    fallbackUrl,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    },
    SYNC_TIMEOUT_MS
  )

  if (fallback.ok) {
    const payload = await fallback.json()
    return payload.result || null
  }

  throw new Error(`Error ejecutando sync (${primary.status})`)
}

async function fetchWithTimeout(url, options = {}, timeoutMs = REQUEST_TIMEOUT_MS) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  try {
    return await fetch(url, {
      ...options,
      signal: controller.signal
    })
  } catch (error) {
    if (error && error.name === 'AbortError') {
      throw new Error('Timeout al consultar API')
    }
    throw error
  } finally {
    clearTimeout(timer)
  }
}
