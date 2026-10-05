#!/usr/bin/env bash
# Aplica cambios del código a la base existente (sin perder datos).
# Uso: ./scripts/actualizar.sh [modulos]   (por defecto: laroca_inventario)
set -euo pipefail
cd "$(dirname "$0")/.."
source .env
MODULOS="${1:-laroca_inventario}"
docker compose stop odoo
docker compose run --rm odoo odoo -d "${ODOO_DB:-laroca}" -u "$MODULOS" --stop-after-init
docker compose up -d odoo
echo ">> Módulos actualizados: $MODULOS"
