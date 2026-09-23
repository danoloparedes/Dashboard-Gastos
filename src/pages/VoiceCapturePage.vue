<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import AssistantAccess from '../components/AssistantAccess.vue'
import { authenticated } from '../services/auth'
import {
  interpretVoiceTranscript,
  fetchVoiceConfig,
  saveVoiceDraft,
  transcribeVoiceAudio
} from '../services/api'

defineEmits(['go-home'])

const status = ref('Cuéntame qué compraste y cuánto pagaste.')
const starting = ref(false)
const seconds = ref(0)
let timer = null
const hasDraft = ref(false)
const busy = computed(() => processing.value || saving.value || starting.value)
const money = n => new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format(n)
const direction = ref('gasto')
const amount = computed({ get: () => draft.value[direction.value], set: n => { draft.value[direction.value] = Number(n); draft.value[direction.value === 'gasto' ? 'abono' : 'gasto'] = 0 } })
const changeDirection = () => { const total = draft.value.gasto || draft.value.abono; draft.value.gasto = 0; draft.value.abono = 0; draft.value[direction.value] = total }
const today = () => new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Santiago' }).format(new Date())
const error = ref('')
const processing = ref(false)
const saving = ref(false)
const saveTarget = ref('')
const voiceConfig = ref(null)
onMounted(async () => {
  try {
    voiceConfig.value = await fetchVoiceConfig()
    saveTarget.value = voiceConfig.value.default_target
  } catch (err) { error.value = err.message }
})
const transcript = ref('')
const transcriptionMeta = ref(null)
const interpretationMeta = ref(null)
const draft = ref({
  fecha: today(),
  descripcion: '',
  clasificacion: 'General',
  tipo: 'Necesidad',
  abono: 0,
  gasto: 0
})
const savedMessage = ref('')
const labels = { fecha: 'Fecha', descripcion: 'Descripcion', clasificacion: 'Clasificacion', tipo: 'Tipo', abono: 'Abono', gasto: 'Gasto' }
const categories = ['Celular', 'Comida', 'Dap', 'Dpto', 'Estudio', 'Fit', 'Higiene', 'Nieve', 'Ocio', 'Otros', 'Rosario', 'Salud', 'Social', 'Souvenir', 'Sueldo', 'Transporte', 'General']
const reviewNotes = computed(() => interpretationMeta.value?.review_notes || [])
const inferred = computed(() => (interpretationMeta.value?.inferred_fields || []).map(field => labels[field]).filter(Boolean))
const interpretedText = ref('')
const stale = computed(() => !!interpretedText.value && transcript.value.trim() !== interpretedText.value)
const validDraft = computed(() => draft.value.descripcion.trim() && draft.value.clasificacion.trim() && draft.value.fecha &&
  [draft.value.abono, draft.value.gasto].every(n => Number.isSafeInteger(n) && n >= 0) &&
  ((draft.value.abono > 0) !== (draft.value.gasto > 0)))
watch(draft, () => { savedMessage.value = '' }, { deep: true })


const isRecording = ref(false)
const supportsGetUserMedia = computed(() => !!navigator.mediaDevices?.getUserMedia)
const supportsMediaRecorder = computed(() => typeof MediaRecorder !== 'undefined')
const isSecureContextOk = computed(() => window.isSecureContext)
const canRecord = computed(
  () => supportsGetUserMedia.value && supportsMediaRecorder.value && isSecureContextOk.value
)
const audioBlob = ref(null)
const audioUrl = ref('')

let mediaRecorder = null
let chunks = []
let disposed = false

const updateDraft = (nextDraft) => {
  direction.value = Number(nextDraft.abono || 0) > 0 ? 'abono' : 'gasto'
  draft.value = {
    fecha: nextDraft.fecha || today(),
    descripcion: nextDraft.descripcion || '',
    clasificacion: nextDraft.clasificacion || 'General',
    tipo: nextDraft.tipo || 'Necesidad',
    abono: Number(nextDraft.abono || 0),
    gasto: Number(nextDraft.gasto || 0)
  }
}

const clearAudio = () => {
  if (audioUrl.value) {
    URL.revokeObjectURL(audioUrl.value)
  }
  audioUrl.value = ''
  audioBlob.value = null
}

const loadAudioBlob = (blob) => {
  hasDraft.value = false
  savedMessage.value = ''
  transcript.value = ''
  interpretedText.value = ''
  interpretationMeta.value = null
  transcriptionMeta.value = null
  updateDraft({})
  clearAudio()
  audioBlob.value = blob
  audioUrl.value = URL.createObjectURL(blob)
  status.value = 'Audio listo. Puedes procesarlo.'
}

const onAudioFileSelected = async (event) => {
  const input = event?.target
  const file = input?.files?.[0]
  if (!file) {
    return
  }

  loadAudioBlob(file)
  event.target.value = ''
  await transcribeAudio()
}

const startRecording = async () => {
  if (busy.value || isRecording.value) return
  error.value = ''
  savedMessage.value = ''
  transcriptionMeta.value = null
  interpretationMeta.value = null

  if (!isSecureContextOk.value) {
    error.value = 'Grabacion bloqueada: abre esta app en HTTPS o desde localhost.'
    return
  }

  if (!supportsGetUserMedia.value || !supportsMediaRecorder.value) {
    error.value = 'Este navegador no soporta grabacion directa. Usa la carga de audio.'
    return
  }

  starting.value = true
  let stream
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    if (disposed) { stream.getTracks().forEach(track => track.stop()); return }
    chunks = []
    const mimeType = ['audio/webm', 'audio/mp4'].find((type) => MediaRecorder.isTypeSupported(type))
    mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)

    mediaRecorder.addEventListener('dataavailable', (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data)
      }
    })

    mediaRecorder.addEventListener('stop', async () => {
      clearInterval(timer)
      isRecording.value = false
      stream.getTracks().forEach((track) => track.stop())
      if (disposed) return
      const blob = new Blob(chunks, { type: mediaRecorder.mimeType || chunks[0]?.type || 'audio/webm' })
      loadAudioBlob(blob)
      await transcribeAudio()
    })

    seconds.value = 0
    mediaRecorder.start()
    timer = setInterval(() => { seconds.value++; if (seconds.value >= 120) stopRecording() }, 1000)
    isRecording.value = true
    status.value = 'Grabando audio...'
  } catch (err) {
    stream?.getTracks().forEach(track => track.stop())
    error.value = err instanceof Error ? err.message : 'No se pudo iniciar la grabacion.'
  } finally { starting.value = false }
}

const stopRecording = () => {
  if (!mediaRecorder || mediaRecorder.state !== 'recording') {
    return
  }
  mediaRecorder.stop()
  processing.value = true
}

const transcribeAudio = async () => {
  if (!audioBlob.value) {
    processing.value = false
    error.value = 'Primero graba un audio o usa texto manual.'
    return
  }
  if (voiceConfig.value && audioBlob.value.size > voiceConfig.value.max_audio_bytes) {
    processing.value = false
    error.value = `El audio supera el limite de ${voiceConfig.value.max_audio_bytes / 1000000} MB. Graba un mensaje mas corto.`
    return
  }

  processing.value = true
  error.value = ''
  savedMessage.value = ''
  status.value = 'Escuchando tu audio…'

  try {
    const result = await transcribeVoiceAudio(audioBlob.value)
    transcript.value = result.transcript || ''
    transcriptionMeta.value = result?.meta || null
    interpretationMeta.value = null
    status.value = 'Preparando tu gasto…'
    await fillFromText()

  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No se pudo transcribir el audio.'
  } finally {
    processing.value = false
  }
}

const interpretText = async () => {
  if (!transcript.value.trim()) {
    error.value = 'No hay texto para interpretar.'
    return
  }

  processing.value = true
  error.value = ''
  savedMessage.value = ''
  status.value = 'Preparando tu gasto…'

  try {
    await fillFromText()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No se pudo interpretar el texto.'
  } finally {
    processing.value = false
  }
}

const fillFromText = async () => {
  const text = transcript.value.trim()
  const result = await interpretVoiceTranscript(text)
  updateDraft(result.draft || {})
  hasDraft.value = true
  interpretedText.value = text
  interpretationMeta.value = result.meta || null
  status.value = '¿Está todo bien?'
}

const saveDraft = async () => {
  if (!validDraft.value || stale.value || processing.value || saving.value || isRecording.value || savedMessage.value) return
  saving.value = true
  error.value = ''
  savedMessage.value = ''

  try {
    const result = await saveVoiceDraft(draft.value, saveTarget.value)
    const channels = Object.keys(result.saved || {})
    savedMessage.value = `Guardado correctamente en: ${channels.join(', ')}`
    status.value = 'Gasto guardado en el destino seleccionado. Si usas Sheets, sincroniza el dashboard para verlo.'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No se pudo guardar el gasto.'
  } finally {
    saving.value = false
  }
}

onUnmounted(() => {
  disposed = true
  clearInterval(timer)
  if (mediaRecorder) {
    if (mediaRecorder.state === 'recording') mediaRecorder.stop()
    mediaRecorder.stream.getTracks().forEach(track => track.stop())
  }
  clearAudio()
})
</script>

<template>
  <main class="voice-mobile">
    <header class="voice-top">
      <button class="voice-back" aria-label="Volver al inicio" @click="$emit('go-home')">←</button>
      <div><span class="voice-eyebrow">TUS GASTOS, AL DÍA</span><h1>Registra y sigue</h1></div>
    </header>
    <AssistantAccess compact />
    <template v-if="authenticated">
      <section v-if="savedMessage" class="voice-success" role="status">
        <span class="voice-check">✓</span><h2>Listo, guardado</h2>
        <p>{{ draft.descripcion }}</p><strong>{{ money(draft.gasto || draft.abono) }}</strong>
        <p v-if="saveTarget === 'sheets'" class="voice-muted">Sincroniza el dashboard para verlo allí.</p>
        <button class="btn-primary" @click="savedMessage = ''; hasDraft = false; transcript = ''; interpretedText = ''; interpretationMeta = null; updateDraft({}); clearAudio()">Registrar otro</button>
      </section>
      <template v-else>
        <section class="voice-recorder" :class="{ recording: isRecording }" :aria-busy="busy">
          <button class="voice-mic" :disabled="busy || !voiceConfig || !canRecord" :aria-label="isRecording ? 'Terminar grabación y procesar' : 'Grabar gasto'" :aria-pressed="isRecording" @click="isRecording ? stopRecording() : startRecording()">
            <span v-if="processing || starting" class="voice-spinner" aria-hidden="true"></span>
            <span v-else-if="isRecording" class="voice-stop" aria-hidden="true"></span>
            <svg v-else width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8"/></svg>
          </button>
          <div aria-live="polite">
            <h2>{{ isRecording ? `Grabando · ${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}` : processing ? 'Un momento…' : starting ? 'Abriendo micrófono…' : hasDraft ? '¿Otro audio?' : 'Toca y cuéntame' }}</h2>
            <p>{{ isRecording ? 'Toca para terminar.' : processing ? status : hasDraft ? 'Puedes volver a grabar.' : 'Qué compraste, dónde y cuánto.' }}</p>
          </div>
        </section>
        <p v-if="!canRecord" class="voice-muted">Usa HTTPS para grabar, o adjunta un audio abajo.</p>
        <p v-if="error" class="capture-error" role="alert">{{ error }}</p>
        <button v-if="error && audioBlob && !hasDraft" class="voice-link" :disabled="busy || isRecording" @click="transcript ? interpretText() : transcribeAudio()">Reintentar</button>

        <form v-if="hasDraft" class="voice-summary" @submit.prevent="saveDraft">
          <div class="voice-section-title"><h2>Revisa tu movimiento</h2><span>Editable</span></div>
          <fieldset :disabled="busy || isRecording">
            <label class="voice-description">Descripción<textarea v-model="draft.descripcion" rows="2" maxlength="500" placeholder="¿En qué gastaste?" /></label>
            <div class="voice-amount-row">
              <select v-model="direction" aria-label="Gasto o ingreso" @change="changeDirection"><option value="gasto">Gasto</option><option value="abono">Ingreso</option></select>
              <label><span class="sr-only">Monto en pesos chilenos</span><span aria-hidden="true">$</span><input v-model.number="amount" type="number" inputmode="numeric" min="1" step="1" placeholder="0" /></label>
            </div>
            <div class="voice-small-fields">
              <label>Fecha<input v-model="draft.fecha" type="date" /></label>
              <label>Tipo<select v-model="draft.tipo"><option>Necesidad</option><option>Antojo</option><option>Ahorro</option></select></label>
              <label class="voice-category">Categoría<input v-model="draft.clasificacion" list="expense-categories" /><datalist id="expense-categories"><option v-for="category in categories" :key="category" :value="category" /></datalist></label>
            </div>
          </fieldset>
          <div v-if="reviewNotes.length" class="voice-warning" role="status"><p v-for="note in reviewNotes" :key="note">{{ note }}</p></div>
          <p v-if="stale" class="capture-error">Actualiza el formulario con el texto corregido antes de guardar.</p>
          <p v-if="!validDraft" class="voice-muted">Completa la descripción, categoría y monto.</p>
          <button class="btn-primary voice-save" :disabled="busy || isRecording || !saveTarget || !validDraft || stale">{{ saving ? 'Guardando…' : 'Guardar movimiento' }}</button>
        </form>

        <details class="voice-options">
          <summary>{{ hasDraft ? 'Audio, texto y opciones' : 'O escribe / adjunta un audio' }}</summary>
          <div class="voice-options-body">
            <label class="capture-field">Adjuntar audio<input type="file" :disabled="busy || isRecording || !voiceConfig" accept="audio/*" @change="onAudioFileSelected" /><small v-if="voiceConfig">Hasta {{ voiceConfig.max_audio_bytes / 1000000 }} MB</small></label>
            <audio v-if="audioUrl" :src="audioUrl" controls class="capture-player" />
            <label class="capture-field">Texto<textarea v-model="transcript" :disabled="busy || isRecording" rows="3" placeholder="Gasté tres lucas en un café" /></label>
            <button class="btn-secondary" :disabled="busy || isRecording || !transcript.trim()" @click="interpretText">{{ hasDraft ? 'Actualizar formulario' : 'Completar con texto' }}</button>
            <label class="capture-field">Guardar en<select v-model="saveTarget" :disabled="busy || isRecording"><option v-for="target in voiceConfig?.targets || []" :key="target.value" :value="target.value">{{ target.label }}</option></select></label>
            <p v-if="inferred.length" class="voice-muted">Sugeridos: {{ inferred.join(', ') }}.</p>
          </div>
        </details>
      </template>
    </template>
  </main>
</template>

<style scoped>
.voice-mobile { width: min(100% - 32px, 460px); margin: 0 auto; padding: 22px 0 max(28px, env(safe-area-inset-bottom)); }
.voice-top { display:flex; gap:14px; align-items:center; margin-bottom:12px; }
.voice-back { width:44px; height:44px; border:1px solid var(--border); border-radius:50%; background:var(--paper); font-size:22px; }
.voice-eyebrow { font-size:10px; letter-spacing:1.7px; color:var(--muted); }
.voice-top h1 { font-size:24px; margin:3px 0 0; }
.voice-recorder { display:flex; align-items:center; gap:18px; padding:24px 4px; }
.voice-recorder h2 { font-size:18px; margin:0 0 6px; }
.voice-recorder p,.voice-muted { font-size:13px; color:var(--muted); line-height:1.5; }
.voice-mic { flex-shrink:0; width:76px; height:76px; border:0; border-radius:50%; background:#174c46; color:white; display:grid; place-items:center; box-shadow:0 5px 20px #174c4625; }
.voice-mic:disabled { opacity:.6; }
.recording .voice-mic { background:#ac3e35; box-shadow:0 0 0 7px #ac3e3515; }
.voice-stop { width:23px; height:23px; border-radius:5px; background:white; }
.voice-spinner { width:25px; height:25px; border:3px solid #ffffff55; border-top-color:white; border-radius:50%; animation:spin 1s linear infinite; }
@keyframes spin { to { transform:rotate(360deg); } }
@media(prefers-reduced-motion:reduce) { .voice-spinner { animation:none; } }
.voice-summary { border:1px solid var(--border); background:var(--paper); border-radius:22px; padding:20px; box-shadow:0 8px 26px #1f2a3706; }
.voice-section-title { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.voice-section-title h2 { font-size:15px; }
.voice-section-title span { font-size:11px; color:var(--muted); }
fieldset { padding:0; border:0; margin:0; min-width:0; }
label { display:grid; gap:6px; font-size:12px; color:var(--muted); min-width:0; }
input,select,textarea { width:100%; min-width:0; box-sizing:border-box; font:inherit; font-size:16px; color:var(--ink); background:#f6f4ed; border:1px solid transparent; border-radius:10px; padding:11px; }
input:focus-visible,select:focus-visible,textarea:focus-visible,button:focus-visible,summary:focus-visible { outline:2px solid #287d70; outline-offset:3px; }
textarea { resize:vertical; line-height:1.4; }
.voice-description textarea { font-size:18px; background:transparent; padding:4px 0; border-radius:0; }
.voice-amount-row { display:flex; gap:12px; align-items:center; border-top:1px solid var(--border); border-bottom:1px solid var(--border); margin:12px 0 16px; padding:12px 0; }
.voice-amount-row select { width:106px; font-size:14px; }
.voice-amount-row label { display:flex; align-items:center; flex:1; font-size:24px; color:var(--ink); }
.voice-amount-row input { background:transparent; padding:5px; font-size:27px; font-weight:600; }
.voice-small-fields { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.voice-category { grid-column:1/-1; }
.voice-save { width:100%; min-height:50px; margin-top:18px; border-radius:12px; background:#174c46; color:white; }
.voice-warning { background:#fff0ce; border-radius:10px; padding:10px 12px; margin-top:12px; font-size:13px; line-height:1.5; }
.voice-warning p+p { margin-top:5px; }
.voice-options { margin-top:18px; font-size:13px; color:var(--muted); }
.voice-options summary { cursor:pointer; padding:12px 0; min-height:44px; }
.voice-options-body { display:grid; gap:14px; padding:12px 0; }
.voice-link { border:0; background:transparent; text-decoration:underline; min-height:44px; color:#174c46; }
.voice-success { display:grid; gap:14px; text-align:center; justify-items:center; padding:36px 20px; }
.voice-check { display:grid; place-items:center; width:64px; height:64px; border-radius:50%; background:#dcefe3; color:#174c46; font-size:30px; }
.voice-success h2 { font-size:23px; }.voice-success strong { font-size:30px; }
.sr-only { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0,0,0,0); }
button { cursor:pointer; }button:disabled { cursor:default; }
</style>
