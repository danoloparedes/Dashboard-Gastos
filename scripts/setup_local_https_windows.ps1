param(
  [string]$LocalIp
)

$ErrorActionPreference = 'Stop'

function Get-PrimaryIPv4 {
  $candidates = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
      $_.IPAddress -notlike '127.*' -and
      $_.IPAddress -notlike '169.254.*' -and
      $_.PrefixOrigin -ne 'WellKnown'
    }

  $picked = $candidates | Select-Object -First 1
  if (-not $picked) {
    throw 'No se pudo detectar una IPv4 local automaticamente. Usa -LocalIp "x.x.x.x".'
  }

  return $picked.IPAddress
}

if (-not $LocalIp) {
  $LocalIp = Get-PrimaryIPv4
}

$mkcert = Get-Command mkcert -ErrorAction SilentlyContinue
if (-not $mkcert) {
  Write-Host 'No se encontro mkcert en PATH.' -ForegroundColor Yellow
  Write-Host 'Instala mkcert y ejecuta este script de nuevo.' -ForegroundColor Yellow
  Write-Host 'Con Chocolatey: choco install mkcert -y' -ForegroundColor Yellow
  exit 1
}

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$certDir = Join-Path $projectRoot 'certs'
if (-not (Test-Path $certDir)) {
  New-Item -ItemType Directory -Path $certDir | Out-Null
}

$certFile = Join-Path $certDir 'dev-local-cert.pem'
$keyFile = Join-Path $certDir 'dev-local-key.pem'

Write-Host "Instalando CA local de mkcert (si falta)..." -ForegroundColor Cyan
mkcert -install

Write-Host "Generando certificado para localhost y $LocalIp ..." -ForegroundColor Cyan
mkcert -key-file $keyFile -cert-file $certFile localhost 127.0.0.1 ::1 $LocalIp

Write-Host 'Certificado generado:' -ForegroundColor Green
Write-Host "  $certFile"
Write-Host 'Llave generada:' -ForegroundColor Green
Write-Host "  $keyFile"
Write-Host ''
Write-Host 'Ahora puedes levantar run_dashboard.bat y Vite usara HTTPS automaticamente.' -ForegroundColor Green
Write-Host "Abre en el navegador: https://$LocalIp:5173" -ForegroundColor Green
