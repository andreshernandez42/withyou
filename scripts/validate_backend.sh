#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"

echo '[1/4] Compilación Python'
PYTHONPATH=. python -m compileall -q app alembic

echo '[2/4] Pruebas automatizadas'
PYTHONPATH=. pytest -q

echo '[3/4] Migración Alembic de línea base sobre SQLite temporal'
TMP_DB="${TMPDIR:-/tmp}/withyou_alembic_validate.db"
rm -f "$TMP_DB"
DATABASE_URL="sqlite:///$TMP_DB" PYTHONPATH=. alembic upgrade head >/dev/null
rm -f "$TMP_DB"

echo '[4/4] Validación YAML de Docker Compose'
ROOT_DIR="$ROOT" python - <<'PY'
import os, pathlib, yaml
p=pathlib.Path(os.environ['ROOT_DIR'])/'docker-compose.yml'
d=yaml.safe_load(p.read_text())
assert {'db','redis','api1','api2','worker','beat','nginx'} <= set(d['services'])
print('docker-compose.yml OK')
PY

echo 'Backend With You: VALIDACIÓN OK'
