#!/usr/bin/env bash
# Se ejecuta EN EL SERVIDOR (Ubuntu 24.04), como root. Se puede repetir sin problema.
# Instala Docker, activa el firewall, agrega memoria de intercambio (swap) y actualizaciones automáticas.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

if ! command -v docker >/dev/null || ! docker compose version >/dev/null 2>&1; then
    echo ">> Instalando Docker (paquetes oficiales de Ubuntu)"
    apt-get update -q
    apt-get install -y -q docker.io docker-compose-v2 rsync ufw unattended-upgrades
    systemctl enable --now docker
fi

# 2 GB de swap: Odoo + PostgreSQL + generación de PDF en un servidor de 2 GB
if ! swapon --show | grep -q /swapfile; then
    echo ">> Creando swap de 2 GB"
    fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
    grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# Firewall: solo SSH (22) y la web (80 para el certificado, 443 HTTPS)
ufw allow 22/tcp >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null

# Actualizaciones de seguridad automáticas
dpkg-reconfigure -f noninteractive unattended-upgrades >/dev/null 2>&1 || true

mkdir -p /opt/laroca/backups
echo ">> Servidor preparado: $(docker --version)"
