#!/usr/bin/env bash
# Copia los archivos .py de Odoo 18 a .odoo_fuente/ para el autocompletado de VS Code.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf .odoo_fuente && mkdir -p .odoo_fuente
docker run --rm --entrypoint sh odoo:18.0 -c 'cd /usr/lib/python3/dist-packages && find odoo -name "*.py" -not -path "*/tests/*" -not -path "*/static/*" | tar cf - -T -' | tar xf - -C .odoo_fuente
echo ">> Fuente de Odoo copiada en .odoo_fuente/"
