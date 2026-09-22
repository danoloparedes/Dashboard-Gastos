import { ref } from 'vue'

export const authenticated = ref(false)
export const authError = ref('')
export async function refreshSession() {
  try {
    const response = await fetch('/api/auth/session', { cache: 'no-store' })
    const body = await response.json()
    if (!response.ok) throw new Error(body.error || 'No se pudo verificar la sesion.')
    authenticated.value = body.authenticated === true
    authError.value = ''
  } catch (error) { authenticated.value = false; authError.value = error.message }
}
export async function changeSession(method, password) {
  const response = await fetch('/api/auth/session', {
    method, headers: { 'Content-Type': 'application/json', 'X-Gastos-Request': '1' },
    ...(password !== undefined ? { body: JSON.stringify({ password }) } : {})
  })
  const body = await response.json()
  if (!response.ok) throw new Error(body.error || 'No se pudo cambiar la sesion.')
  authenticated.value = body.authenticated === true
  authError.value = ''
}
