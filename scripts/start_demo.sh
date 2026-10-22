#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
[ -f .env ] || cp .env.demo .env
docker compose up -d --build
sleep 8
docker compose exec api python -m app.seed
printf '\nAPI: http://localhost:8000\nSwagger: http://localhost:8000/docs\n'
