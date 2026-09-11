#!/usr/bin/env bash
# ==============================================================================
# Humm Fondos - Script de Restauración y Verificación de Base de Datos SQLite
# Ubicación de ejecución: Servidor HostGator o Local
# Permite restaurar a una ubicación aislada para verificación sin tocar la base viva.
# ==============================================================================
set -euo pipefail

BACKUP_ARCHIVE="${1:-}"
RESTORE_TARGET="${2:-}"

if [ -z "$BACKUP_ARCHIVE" ] || [ -z "$RESTORE_TARGET" ]; then
    echo "Uso: $0 <archivo_backup.sqlite3.gz> <destino_restauracion.sqlite3>"
    echo "Ejemplo para prueba aislada:"
    echo "  $0 /home1/paulocis/RESPALDOS/fondos_backups/fondos_backup_20260911_120000.sqlite3.gz /tmp/test_restore.sqlite3"
    exit 1
fi

if [ ! -f "$BACKUP_ARCHIVE" ]; then
    echo "❌ Error: Archivo de backup no encontrado: $BACKUP_ARCHIVE" >&2
    exit 1
fi

# 1. Comprobar checksum SHA-256 si existe archivo .sha256 correspondiente
SHA_FILE="${BACKUP_ARCHIVE%.gz}.sha256"
if [ ! -f "$SHA_FILE" ]; then
    # Probar quitando extensión .sqlite3.gz y buscando .sha256
    DIR_NAME=$(dirname "$BACKUP_ARCHIVE")
    BASE_NAME=$(basename "$BACKUP_ARCHIVE" .sqlite3.gz)
    SHA_FILE="${DIR_NAME}/${BASE_NAME}.sha256"
fi

if [ -f "$SHA_FILE" ]; then
    echo "🔍 Verificando integridad SHA-256 del backup..."
    EXPECTED_SHA=$(awk '{print $1}' "$SHA_FILE")
    ACTUAL_SHA=$(sha256sum "$BACKUP_ARCHIVE" | awk '{print $1}')
    if [ "$EXPECTED_SHA" != "$ACTUAL_SHA" ]; then
        echo "❌ Error de Checksum: El archivo no coincide con su firma." >&2
        echo "   Esperado: $EXPECTED_SHA" >&2
        echo "   Obtenido: $ACTUAL_SHA" >&2
        exit 1
    fi
    echo "✔ Checksum SHA-256 verificado: $ACTUAL_SHA"
else
    echo "⚠️ Advertencia: No se encontró archivo .sha256 acompañante. Procediendo con verificación gzip..."
fi

# 2. Descompresión hacia archivo destino temporal
TEMP_RESTORE="${RESTORE_TARGET}.tmp.$$"
echo "📂 Descomprimiendo backup hacia destino temporal: $TEMP_RESTORE..."
gunzip -c "$BACKUP_ARCHIVE" > "$TEMP_RESTORE"

# 3. Verificación de integridad SQLite sobre la base restaurada
echo "🔍 Ejecutando PRAGMA integrity_check..."
INTEGRITY=$(sqlite3 "$TEMP_RESTORE" "PRAGMA integrity_check;")
if [ "$INTEGRITY" != "ok" ]; then
    echo "❌ Error: La base de datos restaurada está corrupta: $INTEGRITY" >&2
    rm -f "$TEMP_RESTORE"
    exit 1
fi
echo "✔ PRAGMA integrity_check: ok"

# 4. Inspección y verificación de datos críticos
echo "📊 Verificando registros del catálogo y administración..."
TOTAL_INSTRUMENTOS=$(sqlite3 "$TEMP_RESTORE" "SELECT COUNT(*) FROM orientador_instrumento;" 2>/dev/null || echo "0")
TOTAL_CONVOCATORIAS=$(sqlite3 "$TEMP_RESTORE" "SELECT COUNT(*) FROM orientador_convocatoria;" 2>/dev/null || echo "0")
TOTAL_USUARIOS=$(sqlite3 "$TEMP_RESTORE" "SELECT COUNT(*) FROM auth_user;" 2>/dev/null || echo "0")
TOTAL_SOLICITUDES=$(sqlite3 "$TEMP_RESTORE" "SELECT COUNT(*) FROM orientador_solicitudapoyo;" 2>/dev/null || echo "0")

echo "   - Instrumentos en catálogo: $TOTAL_INSTRUMENTOS"
echo "   - Convocatorias: $TOTAL_CONVOCATORIAS"
echo "   - Usuarios administradores: $TOTAL_USUARIOS"
echo "   - Solicitudes de apoyo: $TOTAL_SOLICITUDES"

if [ "$TOTAL_INSTRUMENTOS" -lt 1 ]; then
    echo "❌ Error: El catálogo restaurado no contiene instrumentos." >&2
    rm -f "$TEMP_RESTORE"
    exit 1
fi

# 5. Mover a destino final atómicamente
mv -f "$TEMP_RESTORE" "$RESTORE_TARGET"
chmod 600 "$RESTORE_TARGET"

echo "🎉 Restauración y verificación completadas con éxito en: $RESTORE_TARGET"
