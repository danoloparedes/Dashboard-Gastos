const API_BASE = '/api'
const VOICE_API_BASE = '/api/voice'
const REQUEST_TIMEOUT_MS = 8000
const SYNC_TIMEOUT_MS = 90000
const VOICE_TIMEOUT_MS = 120000

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

export async function processVoiceAudio(audioBlob) {
  const form = new FormData()
  form.append('audio', audioBlob, 'voice.webm')

  const response = await fetchWithTimeout(
    `${VOICE_API_BASE}/process`,
    {
      method: 'POST',
      body: form
    },
    VOICE_TIMEOUT_MS
  )

  if (!response.ok) {
    const payload = await safeJson(response)
    throw new Error(payload?.error || `Error procesando audio (${response.status})`)
  }

  const payload = await response.json()
  return payload.result || {}
}

export async function transcribeVoiceAudio(audioBlob) {
  const form = new FormData()
  form.append('audio', audioBlob, 'voice.webm')

  const response = await fetchWithTimeout(
    `${VOICE_API_BASE}/transcribe`,
    {
      method: 'POST',
      body: form
    },
    VOICE_TIMEOUT_MS
  )

  if (!response.ok) {
    const payload = await safeJson(response)
    throw new Error(payload?.error || `Error transcribiendo audio (${response.status})`)
  }

  const payload = await response.json()
  return payload.result || {}
}

export async function transcribeVoiceText(text) {
  const response = await fetchWithTimeout(
    `${VOICE_API_BASE}/transcribe`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ text_override: text })
    },
    VOICE_TIMEOUT_MS
  )

  if (!response.ok) {
    const payload = await safeJson(response)
    throw new Error(payload?.error || `Error transcribiendo texto (${response.status})`)
  }

  const payload = await response.json()
  return payload.result || {}
}

export async function interpretVoiceTranscript(transcript) {
  const response = await fetchWithTimeout(
    `${VOICE_API_BASE}/interpret`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ transcript })
    },
    VOICE_TIMEOUT_MS
  )

  if (!response.ok) {
    const payload = await safeJson(response)
    throw new Error(payload?.error || `Error interpretando texto (${response.status})`)
  }

  const payload = await response.json()
  return payload.result || {}
}

export async function processVoiceText(text) {
  const response = await fetchWithTimeout(
    `${VOICE_API_BASE}/process`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ text_override: text })
    },
    VOICE_TIMEOUT_MS
  )

  if (!response.ok) {
    const payload = await safeJson(response)
    throw new Error(payload?.error || `Error procesando texto (${response.status})`)
  }

  const payload = await response.json()
  return payload.result || {}
}

export async function saveVoiceDraft(draft, persistTarget = 'sqlite') {
  const response = await fetchWithTimeout(
    `${VOICE_API_BASE}/save`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        draft,
        persist_target: persistTarget
      })
    },
    REQUEST_TIMEOUT_MS
  )

  if (!response.ok) {
    const payload = await safeJson(response)
    throw new Error(payload?.error || `Error guardando gasto (${response.status})`)
  }

  const payload = await response.json()
  return payload.result || {}
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

async function safeJson(response) {
  try {
    return await response.json()
  } catch {
    return null
  }
}
