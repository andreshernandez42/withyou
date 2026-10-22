#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
PYTHONPATH=. python -m compileall -q app
PYTHONPATH=. pytest -q
