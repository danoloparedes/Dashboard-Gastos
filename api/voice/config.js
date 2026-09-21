import { MAX_AUDIO_BYTES } from '../_lib/voice.js'
export default { fetch(request) {
  if (request.method !== 'GET') return Response.json({ error: 'method_not_allowed' }, { status: 405, headers: { Allow: 'GET' } })
  return Response.json({ result: {
    default_target: 'postgres',
    targets: [{ value: 'postgres', label: 'Dashboard' }, { value: 'sheets', label: 'Google Sheets' }, { value: 'both', label: 'Dashboard + Google Sheets' }],
    max_audio_bytes: MAX_AUDIO_BYTES
  } }, { headers: { 'Cache-Control': 'no-store' } })
} }
