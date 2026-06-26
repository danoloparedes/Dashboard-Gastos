#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/home/pi/dashboard-gastos"
PI_USER="pi"
LOG_PREFIX="[dashboard-startup]"

run_as_pi() {
  local cmd="$1"
  sudo -u "$PI_USER" -H bash -lc "$cmd"
}

echo "$LOG_PREFIX Iniciando proceso de actualizacion y arranque..."

if [ ! -d "$REPO_DIR" ]; then
  echo "$LOG_PREFIX ERROR: No existe repo en $REPO_DIR"
  exit 1
fi

echo "$LOG_PREFIX Git pull..."
run_as_pi "cd '$REPO_DIR' && git pull --ff-only"

echo "$LOG_PREFIX Verificando entorno virtual Python..."
run_as_pi "cd '$REPO_DIR' && [ -d .venv ] || python3 -m venv .venv"

echo "$LOG_PREFIX Instalando dependencias backend..."
run_as_pi "cd '$REPO_DIR' && . .venv/bin/activate && python -m pip install -r backend/requirements.txt"

echo "$LOG_PREFIX Instalando dependencias frontend y compilando..."
run_as_pi "cd '$REPO_DIR' && npm ci && npm run build"

echo "$LOG_PREFIX Ejecutando sync Google Sheets -> SQLite..."
run_as_pi "cd '$REPO_DIR/backend' && ../.venv/bin/python sync_google_sheet.py"

echo "$LOG_PREFIX Publicando frontend en Nginx root..."
mkdir -p /var/www/dashboard-gastos
rsync -a --delete "$REPO_DIR/dist/" /var/www/dashboard-gastos/
chown -R www-data:www-data /var/www/dashboard-gastos
find /var/www/dashboard-gastos -type d -exec chmod 755 {} \;
find /var/www/dashboard-gastos -type f -exec chmod 644 {} \;

echo "$LOG_PREFIX Reiniciando servicios..."
systemctl restart dashboard-api
systemctl reload nginx

echo "$LOG_PREFIX OK: dashboard actualizado y levantado."
