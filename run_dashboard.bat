@echo off
setlocal

set "ROOT=%~dp0"
set "PY=%ROOT%.venv\Scripts\python.exe"

if not exist "%PY%" (
  echo [ERROR] No se encontro Python del entorno virtual en:
  echo         %PY%
  echo Activa/crea el entorno .venv antes de usar este script.
  pause
  exit /b 1
)

where npm.cmd >nul 2>&1
if errorlevel 1 (
  echo [ERROR] No se encontro npm.cmd en PATH.
  echo Instala Node.js o abre una terminal donde npm.cmd este disponible.
  pause
  exit /b 1
)

set "API_PID="
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /R /C:":8000 .*LISTENING"') do (
  set "API_PID=%%p"
)
if defined API_PID (
  echo [WARN] Puerto 8000 en uso por PID %API_PID%.
  echo [WARN] Cerrando proceso previo para reiniciar API limpia...
  taskkill /PID %API_PID% /F >nul 2>&1
)

echo ================================================
echo 1^/3 Sincronizando Google Sheets ^> SQLite...
echo ================================================
pushd "%ROOT%backend"
"%PY%" sync_google_sheet.py
if errorlevel 1 (
  echo [WARN] La sincronizacion fallo. Revisar backend\.env y credenciales.
  echo [WARN] Continuando igualmente para levantar backend/frontend...
) else (
  echo [OK] Sincronizacion completada.
)
popd

echo.
echo ================================================
echo 2^/3 Levantando backend API en nueva ventana...
echo ================================================
start "Dashboard Backend API" /D "%ROOT%backend" cmd /k ""%PY%" api_server.py"

echo Esperando API en http://127.0.0.1:8000/health ...
powershell -NoProfile -Command "for($i=0; $i -lt 20; $i++){ try { Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 1 ^| Out-Null; exit 0 } catch { Start-Sleep -Milliseconds 500 } }; exit 1"
if errorlevel 1 (
  echo [WARN] La API no respondio a tiempo.
  echo [WARN] Revisa la ventana "Dashboard Backend API" para ver el error exacto.
) else (
  echo [OK] API levantada correctamente.
)

echo.
echo ================================================
echo 3^/3 Levantando frontend Vite en nueva ventana...
echo ================================================
start "Dashboard Frontend" /D "%ROOT%" cmd /k "npm.cmd run dev -- --host"

echo.
echo [OK] Todo lanzado.
echo Frontend: http://localhost:5173
echo API:      http://127.0.0.1:8000/health

echo Puedes cerrar esta ventana; backend y frontend quedan en sus ventanas.
endlocal
