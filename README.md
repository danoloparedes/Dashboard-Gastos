# Dashboard Gastos

Proyecto Vue para visualizar tus gastos personales, con dos vistas:

- Landing page
- Dashboard mensual (filtros por anio y mes)

## Ejecutar en local

1. Instalar dependencias:

```bash
npm install
```

En PowerShell de Windows, si te bloquea `npm`, usa:

```bash
npm.cmd install
```

2. Levantar entorno de desarrollo:

```bash
npm run dev
```

En PowerShell de Windows:

```bash
npm.cmd run dev -- --host
```

Frontend local:

- http://localhost:5173

3. Compilar para produccion:

```bash
npm run build
```

## Estructura relevante

- `src/pages/LandingPage.vue`: portada del sitio
- `src/pages/DashboardPage.vue`: dashboard principal con filtros (consume API SQL)
- `src/components/charts/StackedMonthlyChart.vue`: barras apiladas por mes
- `src/components/charts/DailyTypeChart.vue`: barras diarias por tipo
- `src/data/transactions.js`: constantes y utilidades
- `src/services/api.js`: cliente frontend para la API
- `backend/api_server.py`: API local que lee SQLite
- `src/pages/VoiceCapturePage.vue`: captura y confirmacion de gastos por voz
- `backend/voice_server.py`: API de voz (proceso paralelo en puerto 8001)
- `backend/voice_pipeline.py`: transcripcion, interpretacion y guardado (SQLite/Sheets)

## Backend recomendado para tu caso

Como ya manejas Python y Django, la opcion mas simple y mantenible es:

- Django + Django REST Framework para exponer API
- PostgreSQL o SQLite (SQLite funciona bien para volumen personal)
- Un job diario para sincronizar desde Google Sheets a BD

### Flujo de datos sugerido

1. Script/management command de Django lee Google Sheets (1 vez al dia)
2. Hace upsert de movimientos en tabla `transactions`
3. Frontend consume API con datos ya normalizados

## Despliegue en Raspberry Pi

No abras el puerto directo del dev server de Vite. Mejor:

1. Compilas frontend (`npm run build`)
2. Sirves archivos estaticos con Nginx
3. Django corre con Gunicorn (localhost)
4. Nginx hace reverse proxy a Django

Si quieres exponerlo publico desde casa:

- Opcion A: Cloudflare Tunnel (recomendada)
- Opcion B: abrir puertos + DNS dinamico + HTTPS (mas mantenimiento)

## Flujo local completo (real)

Orden recomendado para probar con datos reales:

1. Sincronizar Google Sheets a SQLite:

```bash
cd backend/sync
python sync_google_sheet.py
```

2. Levantar API local (lee `backend/data/gastos.db`):

```bash
cd backend
python api_server.py
```

Si quieres acceso desde red local, usa:

```bash
API_HOST=0.0.0.0 python api_server.py
```

3. Levantar frontend (consume API por proxy Vite):

```bash
cd ..
npm run dev -- --host
```

Notas:

- Endpoint de datos: `GET /api/transactions`
- Endpoint voz: `POST /api/voice/process` y `POST /api/voice/save`
- El frontend ya no usa mock de transacciones.

## Registro de gastos por voz (PWA)

La app ahora incluye una vista movil para capturar gastos por voz:

- Ruta: `/#/capture`
- En landing: boton **Registrar gasto por voz**
- Flujo: grabar audio -> transcribir -> interpretar a columnas -> editar -> guardar

### Backend de voz separado (recomendado)

El servicio de voz corre en paralelo al dashboard:

- Dashboard API: `http://127.0.0.1:8000`
- Voice API: `http://127.0.0.1:8001`

En desarrollo, Vite hace proxy automatico de `/api/voice` al puerto 8001.

### Variables para voz (`backend/.env`)

Revisa `backend/.env.example` y define:

- `VOICE_API_HOST`, `VOICE_API_PORT`
- `VOICE_WHISPER_MODE`: `mock` o `faster-whisper`
- `VOICE_WHISPER_MODEL`, `VOICE_WHISPER_COMPUTE_TYPE`
- `VOICE_OLLAMA_MODEL` (opcional, si quieres parse con Ollama)
- `VOICE_OLLAMA_URL`

Si `VOICE_OLLAMA_MODEL` queda vacio, se usa parser heuristico local.

### Activar Whisper real para pruebas

1. Instala dependencias backend (incluye `faster-whisper`):

```bash
cd backend
pip install -r requirements.txt
```

2. En `backend/.env`, deja:

```env
VOICE_WHISPER_MODE=faster-whisper
VOICE_WHISPER_MODEL=small
VOICE_WHISPER_COMPUTE_TYPE=int8
```

3. Reinicia `voice_server.py`.

4. Al procesar audio, la respuesta devuelve `meta.transcription_engine` y `meta.elapsed_ms` para validar motor y tiempo.

### Instalable en celular (PWA)

Se agrego `public/manifest.webmanifest` y `public/sw.js`.
Desde el navegador del telefono puedes usar **Agregar a pantalla de inicio**.

Importante para grabacion en celular:

- `getUserMedia` requiere contexto seguro (HTTPS o localhost).
- Si abres por `http://IP:puerto`, muchos navegadores bloquean microfono.
- La vista de captura incluye fallback para subir audio (`input file`) cuando no hay soporte de grabacion directa.

### Habilitar HTTPS local en Raspberry (para microfono movil)

Se incluye un script para crear certificado local y activar TLS en Nginx:

```bash
cd /home/pi/dashboard-gastos
chmod +x scripts/setup_https_local_pi.sh
./scripts/setup_https_local_pi.sh
```

Luego abre en celular:

```text
https://IP_DE_TU_RASPBERRY
```

Como el certificado es local (self-signed), debes confiarlo en el celular para
evitar bloqueos de permisos de microfono:

1. Exporta/copia el certificado `dashboard-gastos.crt` al telefono.
2. Instala el certificado CA/usuario desde ajustes de seguridad del telefono.
3. Vuelve a abrir la URL HTTPS y acepta permisos de microfono.

### Si aparece error 502

Normalmente significa que Vite no pudo llegar a la API. Solucion rapida:

1. Reiniciar `backend/api_server.py`
2. Reiniciar `npm run dev`
3. Probar `http://localhost:8000/health`

## Sincronizacion Google Sheets a SQLite

Se agrego una base de sincronizacion en `backend/`:

- `backend/sync/sync_google_sheet.py`: descarga datos desde Google Sheets y hace upsert
- `backend/sync/schema.sql`: schema de tabla `transactions`
- `backend/.env.example`: variables de entorno

### 1) Instalar dependencias backend

```bash
cd backend
pip install -r requirements.txt
```

### 2) Configurar credenciales

1. Crea un Service Account en Google Cloud y descarga el JSON.
2. Comparte tu Google Sheet con el email del Service Account (permiso lector).
3. Copia `backend/.env.example` a `backend/.env` y completa:

```env
GOOGLE_SERVICE_ACCOUNT_FILE=./service-account.json
GOOGLE_SHEETS_SPREADSHEET_ID=tu_spreadsheet_id
GOOGLE_SHEETS_WORKSHEET=Movimientos
SQLITE_DB_PATH=./data/gastos.db
```

### 3) Ejecutar sincronizacion manual

```bash
cd backend/sync
python sync_google_sheet.py
```

### 4) Programar 1 vez al dia (Raspberry)

Con `cron`:

```bash
0 3 * * * cd /ruta/proyecto/backend/sync && /ruta/venv/bin/python sync_google_sheet.py >> /ruta/proyecto/backend/sync.log 2>&1
```

Con esto puedes mantener la BD local actualizada diariamente y luego exponerla via Django API.

## Raspberry auto-update + auto-start al reiniciar

Si subes este proyecto a GitHub y quieres que la Raspberry se actualice sola al boot, se incluye:

- `scripts/run_dashboard_pi.sh`: hace pull, instala deps, build, sync y reinicia servicios
- `deploy/dashboard-startup.service`: servicio systemd para ejecutar el script en cada reinicio
- `scripts/setup_pi_once.sh`: setup unico para Raspberry ya existente
- `deploy/dashboard-api.service`: servicio systemd para API principal (puerto 8000)
- `deploy/dashboard-voice-api.service`: servicio systemd para la API de voz
- `deploy/dashboard-gastos.nginx.conf`: sitio Nginx para frontend + proxy `/api` y `/api/voice`

### Si tu Raspberry ya estaba montada y hace pull automatico

Si ya tienes el repo en `/home/pi/dashboard-gastos` y solo quieres adaptar a esta version,
haces esto una sola vez:

```bash
cd /home/pi/dashboard-gastos
chmod +x scripts/setup_pi_once.sh scripts/run_dashboard_pi.sh
./scripts/setup_pi_once.sh
```

Desde ahi en adelante, el flujo normal queda igual: `dashboard-startup` ejecuta
`run_dashboard_pi.sh`, hace `git pull`, build, sync y reinicia servicios.

### Setup en Raspberry (una sola vez)

1. Dar permisos de ejecucion al script:

```bash
chmod +x /home/pi/dashboard-gastos/scripts/run_dashboard_pi.sh
```

2. Instalar el servicio systemd:

```bash
sudo cp /home/pi/dashboard-gastos/deploy/dashboard-startup.service /etc/systemd/system/dashboard-startup.service
sudo systemctl daemon-reload
sudo systemctl enable dashboard-startup.service
```

3. Asegurar servicios base habilitados:

```bash
sudo systemctl enable nginx
sudo cp /home/pi/dashboard-gastos/deploy/dashboard-api.service /etc/systemd/system/dashboard-api.service
sudo systemctl enable dashboard-api
sudo cp /home/pi/dashboard-gastos/deploy/dashboard-voice-api.service /etc/systemd/system/dashboard-voice-api.service
sudo systemctl daemon-reload
sudo systemctl enable dashboard-voice-api
```

4. Probar ejecucion manual:

```bash
sudo systemctl start dashboard-startup.service
sudo systemctl status dashboard-startup.service
```

5. Ver logs:

```bash
journalctl -u dashboard-startup.service -n 200 --no-pager
```

Con esto, en cada encendido/reinicio:

1. Hace `git pull`
2. Actualiza backend y frontend
3. Ejecuta sync Google Sheets -> SQLite
4. Publica `dist/` en `/var/www/dashboard-gastos`
5. Reinicia API dashboard + API voz y recarga Nginx
