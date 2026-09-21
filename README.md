# Dashboard Gastos

Proyecto Vue para visualizar tus gastos personales, con tres vistas:

- Landing page
- Dashboard mensual (filtros por anio y mes)
- Registro de gastos por voz o texto con OpenAI

## Despliegue completo en Vercel + PostgreSQL

El dashboard, la API de datos y los endpoints de voz se despliegan juntos en
Vercel. Las funciones de `api/voice/` llaman a OpenAI desde el servidor y guardan
en PostgreSQL o Google Sheets. No necesitas publicar un servidor Python aparte.

1. Crea una base PostgreSQL desde una integracion del Marketplace de Vercel (por
	ejemplo, Neon) y conectala a este proyecto. Vercel debe exponer la cadena de
	conexion como `POSTGRES_URL`. Si tu proveedor usa otro nombre, copiala en una
	variable `POSTGRES_URL` en Vercel.
2. En Vercel importa este repositorio y usa estos valores:

- Framework preset: `Vite`
- Build command: `npm run build`
- Output directory: `dist`

3. Agrega estas variables de entorno de produccion en Vercel:

```text
POSTGRES_URL=postgresql://...
GOOGLE_SHEETS_SPREADSHEET_ID=...
GOOGLE_SHEETS_WORKSHEET=Gastos
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
OPENAI_API_KEY=tu_clave_de_openai
OPENAI_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe
OPENAI_EXPENSE_MODEL=gpt-4o-mini
```

`GOOGLE_SERVICE_ACCOUNT_JSON` debe contener el JSON completo de la cuenta de
servicio en una sola variable secreta. Comparte la hoja con el correo de esa
cuenta, con permiso de lectura para sincronizar o de editor para guardar por voz.
Nunca subas `backend/service-account.json` ni
`backend/.env` a Vercel.

4. Despliega. La funcion `GET /api/transactions` crea la tabla `transactions` e
	indices automaticamente. Luego abre el dashboard y pulsa **Actualizar datos**
	para ejecutar `POST /api/sync` e importar tu Google Sheet.

El frontend usa `/api` y `/api/voice` del mismo dominio de Vercel. No necesitas
`VITE_DATA_API_URL` ni `VITE_VOICE_API_URL`. Elimina `VITE_VOICE_API_URL` si la
agregaste anteriormente y vuelve a desplegar los cambios del repositorio.
Las claves de OpenAI son variables del servidor: nunca deben llevar prefijo `VITE_`.
En `/#/capture`, el destino predeterminado es Dashboard (PostgreSQL). Los gastos
guardados alli aparecen al abrir el dashboard sin sincronizar Google Sheets.
En desarrollo local, Vite conserva los proxies a `api_server.py` (puerto 8000) y
`voice_server.py` (puerto 8001).

Endpoints incluidos: `GET /api/voice/config`, `POST /api/voice/transcribe`,
`POST /api/voice/interpret`, `POST /api/voice/process`, `POST /api/voice/save`.
La configuracion publica de voz informa los destinos de guardado y el limite de audio,
sin exponer credenciales. El frontend adapta las opciones para Vercel o Python local.

En Vercel los audios admiten hasta 4 MB, dejando margen para multipart dentro del
[limite de carga de las funciones](https://vercel.com/docs/functions/limitations).
Las llamadas a OpenAI tienen timeout y las funciones de voz disponen de 60 segundos.
Pruebas de endpoints sin usar claves ni servicios reales: `npm test`.

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

### HTTPS local para microfono (notebook)

Si quieres abrir desde celular dentro de la misma red y usar microfono, necesitas HTTPS.

1. Instala `mkcert` en Windows (por ejemplo con Chocolatey):

```bash
choco install mkcert -y
```

2. Genera certificado local para Vite:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_local_https_windows.ps1
```

Opcional con IP manual:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_local_https_windows.ps1 -LocalIp "192.168.x.x"
```

3. Levanta `run_dashboard.bat` como siempre.

Si existen `certs/dev-local-cert.pem` y `certs/dev-local-key.pem`, Vite usara HTTPS automaticamente.

Notas:

- URL local: `https://localhost:5173`
- URL desde celular (misma WiFi): `https://IP_DE_TU_NOTEBOOK:5173`
- Para que el celular confie el certificado, debes instalar la CA de `mkcert` en ese dispositivo.

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

## Backend y despliegue en Raspberry Pi

En local y Raspberry se usan los servidores HTTP de Python de `backend/` y SQLite.
En Vercel, las funciones JavaScript de `api/` usan PostgreSQL.
Ambos entornos permiten sincronizar Google Sheets con su base de datos.

En Raspberry, los scripts y servicios de `deploy/` publican el frontend compilado
con Nginx y ejecutan las APIs Python en los puertos 8000 (datos) y 8001 (voz).
Nginx redirige `/api/voice` al servicio de voz y `/api` al servicio de datos.

## Flujo local completo (real)

Orden recomendado para probar con datos reales:

1. Sincronizar Google Sheets a SQLite:

```bash
cd backend
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
- El frontend consulta las transacciones mediante la API.

## Registro de gastos por voz (PWA)

La app ahora incluye una vista movil para capturar gastos por voz:

- Ruta: `/#/capture`
- En landing: boton **Registrar gasto por voz**
- Flujo: grabar audio -> transcribir -> interpretar a columnas -> editar -> guardar

### Backend de voz en desarrollo local y Raspberry

El servicio de voz corre en paralelo al dashboard:

- Dashboard API: `http://127.0.0.1:8000`
- Voice API: `http://127.0.0.1:8001`

En desarrollo, Vite hace proxy automatico de `/api/voice` al puerto 8001.

### Voz con OpenAI: configuracion local y produccion

El backend envia el audio a OpenAI para transcribirlo y usa Responses con
Structured Outputs para extraer `fecha`, `descripcion`, `clasificacion`, `tipo`,
`abono` y `gasto`. Conserva los pasos de transcribir, interpretar, editar y guardar,
asi como los endpoints `/api/voice/transcribe`, `/interpret`, `/process` y `/save`.
El procesamiento de audio y texto se realiza mediante la API de OpenAI.

1. Instala las dependencias desde la raiz del proyecto:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

2. Agrega a `backend/.env` (no al `.env` del frontend):

```dotenv
OPENAI_API_KEY=tu_clave_de_openai
OPENAI_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe
OPENAI_EXPENSE_MODEL=gpt-4o-mini
```

Los modelos son opcionales: esos son los valores predeterminados.
No subas `.env` al repositorio ni uses `VITE_OPENAI_API_KEY`: las variables `VITE_*`
se incorporan al frontend y son visibles desde el navegador.

3. Reinicia `backend/voice_server.py`, o inicia el entorno con `run_dashboard.bat`.

En Vercel, configura las mismas tres variables en Settings > Environment Variables
y despliega esta version del repositorio. Las funciones Node.js de voz las leen
directamente: no necesitas `VITE_VOICE_API_URL` ni un servidor Python externo.
Para Raspberry, el servicio systemd existente carga `backend/.env`.
Las variables de entorno tienen prioridad sobre el archivo `.env`.

El audio se transmite a OpenAI. Admite MP3, MP4, MPEG, MPGA, M4A, WAV y WebM
hasta 4 MB en Vercel y 24 MB en la interfaz local. Los errores de clave, cuota y conexion se muestran sin exponer
respuestas internas del proveedor. Un monto ausente queda en cero y debe
completarse antes de guardar; nunca se genera un gasto ficticio.

En Vercel el guardado usa PostgreSQL, Google Sheets o ambos; en local usa SQLite,
Google Sheets o ambos. Si solo guardas en Sheets, ejecuta **Actualizar datos**.
Al guardar en ambos desde Vercel, se reutiliza el identificador de fila de Sheets
para evitar duplicados durante la siguiente sincronizacion.

Referencias: [transcripcion](https://developers.openai.com/api/docs/guides/speech-to-text)
y [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

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

- `backend/sync_google_sheet.py`: descarga datos desde Google Sheets y hace upsert
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
cd backend
python sync_google_sheet.py
```

### 4) Programar 1 vez al dia (Raspberry)

Con `cron`:

```bash
0 3 * * * cd /ruta/proyecto/backend && /ruta/venv/bin/python sync_google_sheet.py >> /ruta/proyecto/backend/sync.log 2>&1
```

La API `backend/api_server.py` expone los datos de la base local sincronizada.

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
