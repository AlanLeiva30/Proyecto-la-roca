#!/usr/bin/env bash
# Respaldo diario (lo ejecuta cron en el servidor): base de datos + archivos adjuntos/fotos.
# Guarda los últimos 7 días en /opt/laroca/backups.
set -euo pipefail
cd /opt/laroca
FECHA=$(date +%Y-%m-%d_%H%M)
docker compose exec -T db pg_dump -U odoo laroca | gzip > "backups/laroca_${FECHA}.sql.gz"
docker compose exec -T odoo tar -czf - -C /var/lib/odoo filestore > "backups/archivos_${FECHA}.tar.gz"
find backups -type f -mtime +7 -delete
echo "Respaldo listo: ${FECHA}"
