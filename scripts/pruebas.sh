#!/usr/bin/env bash
# Ejecuta las pruebas automáticas en una base temporal (no toca la base "laroca").
set -euo pipefail
cd "$(dirname "$0")/.."
source .env
docker compose up -d --wait db
docker compose exec -T db dropdb -U odoo --if-exists laroca_pruebas
docker compose run --rm odoo odoo -d laroca_pruebas -i laroca_inventario \
    --without-demo=all --test-tags /laroca_inventario --stop-after-init --log-level=test 2>&1 \
    | tee /tmp/laroca_pruebas.log | grep -E "laroca|ERROR|FAIL|Ran |tests" || true
docker compose exec -T db dropdb -U odoo --if-exists laroca_pruebas
if grep -qE "(ERROR|FAIL):" /tmp/laroca_pruebas.log; then
    echo ">> HAY PRUEBAS FALLIDAS"; exit 1
fi
echo ">> Pruebas terminadas sin fallos"
