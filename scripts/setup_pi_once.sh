#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/home/pi/dashboard-gastos"
LOG_PREFIX="[dashboard-setup-once]"

echo "$LOG_PREFIX Iniciando setup unico de Raspberry..."

if [ ! -d "$REPO_DIR" ]; then
  echo "$LOG_PREFIX ERROR: No existe repo en $REPO_DIR"
  exit 1
fi

echo "$LOG_PREFIX Instalando/actualizando unidades systemd..."
sudo cp "$REPO_DIR/deploy/dashboard-startup.service" /etc/systemd/system/dashboard-startup.service
sudo cp "$REPO_DIR/deploy/dashboard-api.service" /etc/systemd/system/dashboard-api.service
sudo cp "$REPO_DIR/deploy/dashboard-voice-api.service" /etc/systemd/system/dashboard-voice-api.service

echo "$LOG_PREFIX Instalando configuracion de Nginx..."
sudo cp "$REPO_DIR/deploy/dashboard-gastos.nginx.conf" /etc/nginx/sites-available/dashboard-gastos
sudo ln -sf /etc/nginx/sites-available/dashboard-gastos /etc/nginx/sites-enabled/dashboard-gastos

if [ -f /etc/nginx/sites-enabled/default ]; then
  sudo rm -f /etc/nginx/sites-enabled/default
fi

echo "$LOG_PREFIX Validando Nginx..."
sudo nginx -t

echo "$LOG_PREFIX Recargando systemd y habilitando servicios..."
sudo systemctl daemon-reload
sudo systemctl enable dashboard-api
sudo systemctl enable dashboard-voice-api
sudo systemctl enable dashboard-startup
sudo systemctl enable nginx

echo "$LOG_PREFIX Ejecutando ciclo inicial de startup..."
sudo systemctl restart dashboard-startup
sudo systemctl restart dashboard-api
sudo systemctl restart dashboard-voice-api
sudo systemctl reload nginx

echo "$LOG_PREFIX OK. Setup unico completado."
echo "$LOG_PREFIX Estado rapido:"
sudo systemctl --no-pager --full status dashboard-startup | sed -n '1,8p'
sudo systemctl --no-pager --full status dashboard-api | sed -n '1,8p'
sudo systemctl --no-pager --full status dashboard-voice-api | sed -n '1,8p'
