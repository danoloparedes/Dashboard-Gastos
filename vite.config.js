import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import basicSsl from '@vitejs/plugin-basic-ssl'
import fs from 'node:fs'
import path from 'node:path'

const DEV_CERT_PATH = path.resolve(__dirname, 'certs/dev-local-cert.pem')
const DEV_KEY_PATH = path.resolve(__dirname, 'certs/dev-local-key.pem')

const hasLocalHttpsCert = fs.existsSync(DEV_CERT_PATH) && fs.existsSync(DEV_KEY_PATH)

const httpsConfig = hasLocalHttpsCert
  ? {
      cert: fs.readFileSync(DEV_CERT_PATH),
      key: fs.readFileSync(DEV_KEY_PATH)
    }
  : false

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    basicSsl({
      name: 'dashboard-gastos-dev'
    })
  ],
  server: {
    host: true,
    https: hasLocalHttpsCert ? httpsConfig : true,
    proxy: {
      '/api/voice': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true
      },
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})
