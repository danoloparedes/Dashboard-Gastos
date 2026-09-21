import { endpoint, transcribe, interpret } from '../_lib/voice.js'
export default endpoint(async request => {
  const started = Date.now()
  const transcription = await transcribe(request)
  const interpretation = await interpret(transcription.transcript)
  return {
    transcript: transcription.transcript, draft: interpretation.draft,
    meta: { elapsed_ms: Date.now() - started, transcription: transcription.meta, interpretation: interpretation.meta }
  }
})
