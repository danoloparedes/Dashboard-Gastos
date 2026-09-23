<script setup>
import { onMounted, ref } from 'vue'
import { authenticated, authError, refreshSession, changeSession } from '../services/auth'
const password = ref('')
defineProps({ compact: Boolean })
const busy = ref(false)
const error = ref('')
onMounted(refreshSession)
async function submit(method) {
  busy.value = true
  error.value = ''
  try { await changeSession(method, method === 'POST' ? password.value : undefined) }
  catch (err) { error.value = err.message }
  finally { password.value = ''; busy.value = false }
}
</script>

<template>
  <section :class="compact && authenticated ? 'access-compact' : 'status-card'">
    <form v-if="!authenticated" @submit.prevent="submit('POST')">
      <p>Ingresa tu contraseña para registrar gastos o sincronizar datos.</p>
      <label class="capture-field">
        Contraseña
        <input v-model="password" type="password" autocomplete="current-password" required maxlength="1024" :disabled="busy" />
      </label>
      <button class="btn-primary" :disabled="busy">{{ busy ? 'Ingresando...' : 'Ingresar' }}</button>
      <p>Este dispositivo recordara tu sesion hasta que cierres sesion o borres los datos del sitio.</p>
    </form>
    <button v-else class="btn-secondary" :disabled="busy" @click="submit('DELETE')">Cerrar sesion</button>
    <p v-if="error || authError" role="alert" class="capture-error">{{ error || authError }}</p>
  </section>
</template>

<style scoped>
.access-compact { display:flex; flex-wrap:wrap; justify-content:flex-end; }
.access-compact button { border:0; background:transparent; padding:8px 0; font-size:12px; color:var(--muted); min-height:44px; box-shadow:none; }
</style>
