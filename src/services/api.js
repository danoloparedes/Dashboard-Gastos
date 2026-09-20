const API_BASE = resolveApiBase(import.meta.env.VITE_DATA_API_URL, '/api')
const VOICE_API_BASE = resolveApiBase(import.meta.env.VITE_VOICE_API_URL, '/api/voice')
const REQUEST_TIMEOUT_MS = 8000
const SYNC_TIMEOUT_MS = 90000
const VOICE_TIMEOUT_MS = 120000

function resolveApiBase(configuredUrl, localPath) {
  const value = configuredUrl?.trim().replace(/\/$/, '')
  if (value) {
    return value
  }

  return localPath
}

function dataApiUrl(path) {
  return `${API_BASE}${path}`
}

function voiceApiUrl(path) {
  if (!VOICE_API_BASE) {
    throw new Error('El asistente de voz aun no esta configurado en este despliegue.')
  }

  return `${VOICE_API_BASE}${path}`
}

export async function fetchTransactions() {
  const response = await fetchWithTimeout(dataApiUrl('/transactions'))

  if (response.ok) {
    const payload = await response.json()
    return payload.transactions || []
  }

  throw new Error(`Error cargando transacciones (${response.status})`)
}

export async function triggerSync() {
  const response = await fetchWithTimeout(
    dataApiUrl('/sync'),
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    },
    SYNC_TIMEOUT_MS
  )

  if (response.ok) {
    const payload = await response.json()
    return payload.result || null
  }

  throw new Error(`Error ejecutando sync (${response.status})`)
}

export async function processVoiceAudio(audioBlob) {
  const form = new FormData()
  form.append('audio', audioBlob, 'voice.webm')

  const response = await fetchWithTimeout(
    voiceApiUrl('/process'),
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
    voiceApiUrl('/transcribe'),
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
    voiceApiUrl('/transcribe'),
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
    voiceApiUrl('/interpret'),
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
    voiceApiUrl('/process'),
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
    voiceApiUrl('/save'),
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
