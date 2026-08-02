<script setup>
import { computed, onUnmounted, ref } from 'vue'
import { processVoiceAudio, processVoiceText, saveVoiceDraft } from '../services/api'

defineEmits(['go-home'])

const status = ref('Listo para grabar')
const error = ref('')
const processing = ref(false)
const saving = ref(false)
const saveTarget = ref('sqlite')
const transcript = ref('')
const draft = ref({
  fecha: new Date().toISOString().slice(0, 10),
  descripcion: '',
  clasificacion: 'General',
  tipo: 'Necesidad',
  abono: 0,
  gasto: 0
})
const savedMessage = ref('')

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

const updateDraft = (nextDraft) => {
  draft.value = {
    fecha: nextDraft.fecha || new Date().toISOString().slice(0, 10),
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
  clearAudio()
  audioBlob.value = blob
  audioUrl.value = URL.createObjectURL(blob)
  status.value = 'Audio listo. Puedes procesarlo.'
}

const onAudioFileSelected = (event) => {
  const input = event?.target
  const file = input?.files?.[0]
  if (!file) {
    return
  }

  loadAudioBlob(file)
}

const startRecording = async () => {
  error.value = ''
  savedMessage.value = ''

  if (!isSecureContextOk.value) {
    error.value = 'Grabacion bloqueada: abre esta app en HTTPS o desde localhost.'
    return
  }

  if (!supportsGetUserMedia.value || !supportsMediaRecorder.value) {
    error.value = 'Este navegador no soporta grabacion directa. Usa la carga de audio.'
    return
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    chunks = []
    mediaRecorder = new MediaRecorder(stream)

    mediaRecorder.addEventListener('dataavailable', (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data)
      }
    })

    mediaRecorder.addEventListener('stop', () => {
      const blob = new Blob(chunks, { type: 'audio/webm' })
      clearAudio()
      audioBlob.value = blob
      audioUrl.value = URL.createObjectURL(blob)
      stream.getTracks().forEach((track) => track.stop())
      status.value = 'Audio grabado. Puedes procesarlo.'
    })

    mediaRecorder.start()
    isRecording.value = true
    status.value = 'Grabando audio...'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No se pudo iniciar la grabacion.'
  }
}

const stopRecording = () => {
  if (!mediaRecorder || mediaRecorder.state !== 'recording') {
    return
  }
  mediaRecorder.stop()
  isRecording.value = false
}

const processAudio = async () => {
  if (!audioBlob.value) {
    error.value = 'Primero graba un audio o usa texto manual.'
    return
  }

  processing.value = true
  error.value = ''
  savedMessage.value = ''
  status.value = 'Procesando audio con Whisper/Ollama...'

  try {
    const result = await processVoiceAudio(audioBlob.value)
    transcript.value = result.transcript || ''
    updateDraft(result.draft || {})
    const engine = result?.meta?.transcription_engine || 'desconocido'
    const elapsed = result?.meta?.elapsed_ms
    status.value =
      typeof elapsed === 'number'
        ? `Texto interpretado (${engine}, ${elapsed} ms). Revisa y confirma el gasto.`
        : `Texto interpretado (${engine}). Revisa y confirma el gasto.`
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No se pudo procesar el audio.'
  } finally {
    processing.value = false
  }
}

const processManualText = async () => {
  if (!transcript.value.trim()) {
    error.value = 'Escribe texto manual para procesar.'
    return
  }

  processing.value = true
  error.value = ''
  savedMessage.value = ''
  status.value = 'Interpretando texto manual...'

  try {
    const result = await processVoiceText(transcript.value.trim())
    transcript.value = result.transcript || transcript.value
    updateDraft(result.draft || {})
    status.value = 'Texto interpretado. Revisa y confirma el gasto.'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No se pudo procesar el texto.'
  } finally {
    processing.value = false
  }
}

const saveDraft = async () => {
  saving.value = true
  error.value = ''
  savedMessage.value = ''

  try {
    const result = await saveVoiceDraft(draft.value, saveTarget.value)
    const channels = Object.keys(result.saved || {})
    savedMessage.value = `Guardado correctamente en: ${channels.join(', ')}`
    status.value = 'Gasto guardado. Ya deberia aparecer en el dashboard.'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No se pudo guardar el gasto.'
  } finally {
    saving.value = false
  }
}

onUnmounted(() => {
  clearAudio()
})
</script>

<template>
  <main class="capture-wrap">
    <header class="capture-header">
      <button class="btn-secondary" @click="$emit('go-home')">Volver</button>
      <h1>Registro por voz</h1>
    </header>

    <section class="capture-card">
      <p class="capture-status">{{ status }}</p>

      <div class="capture-actions">
        <button class="btn-primary" :disabled="isRecording || processing" @click="startRecording">
          Iniciar grabacion
        </button>
        <button class="btn-secondary" :disabled="!isRecording" @click="stopRecording">
          Detener
        </button>
        <button class="btn-secondary" :disabled="!audioBlob || processing" @click="processAudio">
          Procesar audio
        </button>
      </div>

      <label class="capture-field">
        O subir audio (fallback celular)
        <input type="file" accept="audio/*" capture="user" @change="onAudioFileSelected" />
      </label>

      <p v-if="!isSecureContextOk" class="capture-note">
        La grabacion directa requiere HTTPS en celular. Si estas entrando por http://IP, usa HTTPS o sube audio.
      </p>

      <audio v-if="audioUrl" class="capture-player" :src="audioUrl" controls />

      <label class="capture-field">
        Texto (editable)
        <textarea
          v-model="transcript"
          rows="4"
          placeholder="Ej: gaste 12500 en supermercado tipo necesidad hoy"
        />
      </label>

      <button class="btn-secondary" :disabled="processing" @click="processManualText">
        Interpretar texto manual
      </button>

      <div class="capture-grid">
        <label>
          Fecha
          <input v-model="draft.fecha" type="date" />
        </label>
        <label>
          Tipo
          <select v-model="draft.tipo">
            <option>Ahorro</option>
            <option>Antojo</option>
            <option>Necesidad</option>
          </select>
        </label>
      </div>

      <label class="capture-field">
        Descripcion
        <input v-model="draft.descripcion" type="text" />
      </label>

      <label class="capture-field">
        Clasificacion
        <input v-model="draft.clasificacion" type="text" />
      </label>

      <div class="capture-grid">
        <label>
          Abono
          <input v-model.number="draft.abono" type="number" min="0" step="1" />
        </label>
        <label>
          Gasto
          <input v-model.number="draft.gasto" type="number" min="0" step="1" />
        </label>
      </div>

      <label class="capture-field">
        Destino de guardado
        <select v-model="saveTarget">
          <option value="sqlite">SQLite (inmediato dashboard)</option>
          <option value="sheets">Google Sheets</option>
          <option value="both">SQLite + Google Sheets</option>
        </select>
      </label>

      <button class="btn-primary" :disabled="saving" @click="saveDraft">
        {{ saving ? 'Guardando...' : 'Confirmar y guardar' }}
      </button>

      <p v-if="error" class="capture-error">{{ error }}</p>
      <p v-if="savedMessage" class="capture-ok">{{ savedMessage }}</p>
    </section>
  </main>
</template>
