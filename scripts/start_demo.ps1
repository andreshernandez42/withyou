param([switch]$Seed)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
docker compose --env-file .env.demo config --quiet
if ($LASTEXITCODE -ne 0) { throw "Configuración de Compose inválida" }
docker compose --env-file .env.demo up -d --build --wait
if ($LASTEXITCODE -ne 0) { throw "No se pudo iniciar WithYou" }
Invoke-RestMethod "http://localhost:8000/api/v1/health/ready"
if ($Seed) {
    docker compose --env-file .env.demo exec -T api1 python -m app.seed
    if ($LASTEXITCODE -ne 0) { throw "No se pudieron crear los usuarios demo" }
}
