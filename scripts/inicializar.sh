#!/usr/bin/env bash
# Crea la base de datos "laroca", instala los módulos y carga datos de prueba.
# Uso: ./scripts/inicializar.sh            (con datos ficticios)
#      ./scripts/inicializar.sh --sin-datos (solo el módulo, sin datos de prueba)
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || { echo "Falta el archivo .env (copiá .env.example a .env)"; exit 1; }
source .env
MODULOS="laroca_inventario,laroca_datos_prueba"
[ "${1:-}" = "--sin-datos" ] && MODULOS="laroca_inventario"

docker compose up -d --wait db
docker compose stop odoo 2>/dev/null || true

echo ">> Instalando módulos: $MODULOS (tarda unos minutos la primera vez)"
docker compose run --rm odoo odoo -d "${ODOO_DB:-laroca}" -i "$MODULOS" \
    --load-language=es_419 --without-demo=all --stop-after-init

echo ">> Configurando clave del usuario técnico admin"
docker compose run --rm -T odoo sh -c 'odoo shell -d "$ODOO_DB" --no-http --db_host="$HOST" --db_user="$USER" --db_password="$PASSWORD" < /mnt/scripts/set_admin_password.py' 

docker compose up -d odoo
echo ">> Listo. Abrí http://localhost:${ODOO_PORT:-8069}"
