#!/bin/bash
set -e

echo "🚀 Iniciando despliegue de Humm Fondos a Servidor Producción (HostGator)..."

REMOTE_USER="paulocis"
REMOTE_HOST="humm.cl"
REMOTE_PORT="2222"
REMOTE_DIR="/home1/paulocis/public_html/FONDOS"

# 1. Sincronizar archivos al servidor de producción HostGator
echo "🌐 Sincronizando archivos a ${REMOTE_HOST}:${REMOTE_DIR}..."
rsync -avz --exclude='.venv' --exclude='venv' --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store' --exclude='db.sqlite3' -e "ssh -p ${REMOTE_PORT}" ./ ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/

# 2. Ejecutar tareas de producción en el servidor
echo "⚡ Ejecutando migraciones, estáticos y reinicio en servidor..."
ssh -p ${REMOTE_PORT} ${REMOTE_USER}@${REMOTE_HOST} "cd ${REMOTE_DIR} && source venv/bin/activate && python manage.py migrate && python manage.py collectstatic --noinput && chmod 755 passenger_wsgi.py manage.py"

echo "✅ ¡Despliegue completado con éxito! Humm Fondos actualizado en producción."
