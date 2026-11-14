$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location "$Root/backend"
$env:PYTHONPATH = "."
python -m compileall -q app alembic
pytest -q
Write-Host "Backend With You: compilación y Pytest OK"
Write-Host "Para la prueba Alembic/Docker completa use scripts/validate_backend.sh en WSL/Git Bash o Docker Desktop."
