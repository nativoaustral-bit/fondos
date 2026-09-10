#!/bin/bash
set -e

echo "🚀 Iniciando despliegue de Humm Fondos a Servidor Producción (HostGator)..."

REMOTE_USER="paulocis"
REMOTE_HOST="humm.cl"
REMOTE_PORT="2222"
REMOTE_DIR="/home1/paulocis/public_html/FONDOS"
SUBDOMAIN_DIR="/home1/paulocis/fondos.humm.cl"

# 1. Enviar cambios locales a GitHub
echo "📦 Enviando cambios locales a GitHub (nativoaustral-bit/fondos)..."
git push origin main

# 2. Actualizar servidor de producción desde GitHub
echo "🌐 Actualizando servidor de producción desde GitHub..."
ssh -p ${REMOTE_PORT} ${REMOTE_USER}@${REMOTE_HOST} "cd ${REMOTE_DIR} && git fetch origin main && git reset --hard origin/main && source venv/bin/activate && python manage.py migrate && python manage.py collectstatic --noinput && cp passenger_wsgi.py ${SUBDOMAIN_DIR}/ && cp .htaccess ${SUBDOMAIN_DIR}/ && chmod 755 passenger_wsgi.py manage.py ${SUBDOMAIN_DIR}/passenger_wsgi.py && mkdir -p ${SUBDOMAIN_DIR}/tmp tmp && touch ${SUBDOMAIN_DIR}/tmp/restart.txt tmp/restart.txt"

echo "✅ ¡Despliegue completado con éxito! Humm Fondos activo y actualizado en https://fondos.humm.cl/"

