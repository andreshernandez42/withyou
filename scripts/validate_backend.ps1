$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location (Join-Path $Root "backend")
$env:PYTHONPATH="."
python -m compileall -q app
pytest -q
