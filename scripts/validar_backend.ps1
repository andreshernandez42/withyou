# Ejecutar en PowerShell desde C:\dev\withyou tras aplicar el parche.
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
Write-Host '1. Configuración de Docker Compose'
docker compose config --quiet
if ($LASTEXITCODE -ne 0) { throw 'docker compose config falló' }
Write-Host '2. Estado de servicios'
docker compose ps
Write-Host '3. Health de API (si está levantada)'
Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/health/ready' -TimeoutSec 15 | ConvertTo-Json
Write-Host '4. Confirmación de versiones copiadas al contenedor'
docker compose exec api1 python -c 'from app.adapters.sgc import SgcEarthquakeAdapter; from app.core.config import settings; print("Capa:",settings.sgc_query_url); print("Sondeo habilitado:",settings.sgc_poll_enabled); print("Tiempo:",settings.sgc_time_field)'
Write-Host 'Si el sondeo está deshabilitado, primero validar la fuente SGC con inspect_sgc.py.'
