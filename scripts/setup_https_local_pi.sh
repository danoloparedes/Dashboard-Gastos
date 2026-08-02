#!/usr/bin/env bash
set -euo pipefail

CERT_DIR="/etc/ssl/localcerts"
CERT_FILE="$CERT_DIR/dashboard-gastos.crt"
KEY_FILE="$CERT_DIR/dashboard-gastos.key"

HOSTNAME_VALUE="$(hostname -s)"
IP_VALUE="$(hostname -I | awk '{print $1}')"

if [ -z "$IP_VALUE" ]; then
  echo "[https-setup] ERROR: No se pudo detectar IP local de la Raspberry."
  exit 1
fi

echo "[https-setup] Instalando openssl si falta..."
sudo apt-get update
sudo apt-get install -y openssl

echo "[https-setup] Creando carpeta de certificados..."
sudo mkdir -p "$CERT_DIR"

TMP_OPENSSL_CNF="$(mktemp)"
cat > "$TMP_OPENSSL_CNF" <<EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
x509_extensions = v3_req
distinguished_name = dn

[dn]
C = CL
ST = RM
L = Santiago
O = DashboardGastos
OU = HomeLab
CN = $IP_VALUE

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
IP.1 = $IP_VALUE
DNS.1 = $HOSTNAME_VALUE
DNS.2 = $HOSTNAME_VALUE.local
EOF

echo "[https-setup] Generando certificado local (365 dias)..."
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "$KEY_FILE" \
  -out "$CERT_FILE" \
  -config "$TMP_OPENSSL_CNF"

rm -f "$TMP_OPENSSL_CNF"

echo "[https-setup] Ajustando permisos..."
sudo chmod 600 "$KEY_FILE"
sudo chmod 644 "$CERT_FILE"

echo "[https-setup] Validando Nginx y recargando..."
sudo nginx -t
sudo systemctl reload nginx

echo "[https-setup] OK HTTPS local habilitado."
echo "[https-setup] URL sugerida: https://$IP_VALUE"
echo "[https-setup] Certificado publico para importar en celular: $CERT_FILE"
