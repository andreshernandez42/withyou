Set-Location (Join-Path $PSScriptRoot "..")
if (!(Test-Path ".env")) { Copy-Item ".env.demo" ".env" }
docker compose up -d --build
Start-Sleep -Seconds 8
docker compose exec api python -m app.seed
Write-Host "API: http://localhost:8000"
Write-Host "Swagger: http://localhost:8000/docs"
