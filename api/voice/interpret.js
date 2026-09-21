import { endpoint, interpret, readJson } from '../_lib/voice.js'
export default endpoint(async request => interpret((await readJson(request)).transcript))
