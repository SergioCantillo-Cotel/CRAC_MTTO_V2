#!/bin/bash

# ===================================================================
# Script para configurar conexión automática a PostgreSQL
# Crea archivo .pgpass para evitar solicitar contraseña
# ===================================================================

set -e

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

echo ""
echo "=================================================================="
echo "Configuración de Conexión Automática a PostgreSQL"
echo "=================================================================="
echo ""

# Configuración de conexión
POSTGRES_HOST="127.0.0.1"
POSTGRES_PORT="5432"
POSTGRES_DB="eficiencia_energetica"
POSTGRES_USER="api_crud_api_crud_monitoreo_equipos"

print_info "Configuración de PostgreSQL:"
echo "  Host: $POSTGRES_HOST"
echo "  Port: $POSTGRES_PORT"
echo "  Database: $POSTGRES_DB"
echo "  User: $POSTGRES_USER"
echo ""

# Solicitar contraseña
read -sp "Ingresa la contraseña de PostgreSQL: " POSTGRES_PASSWORD
echo ""
echo ""

if [ -z "$POSTGRES_PASSWORD" ]; then
    print_error "La contraseña no puede estar vacía"
    exit 1
fi

# Probar conexión
print_info "Probando conexión a PostgreSQL..."
export PGPASSWORD="$POSTGRES_PASSWORD"

if psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1" &> /dev/null; then
    print_success "Conexión exitosa a PostgreSQL"
else
    print_error "No se pudo conectar a PostgreSQL con las credenciales proporcionadas"
    unset PGPASSWORD
    exit 1
fi

unset PGPASSWORD

# Crear o actualizar archivo .pgpass
PGPASS_FILE="$HOME/.pgpass"

print_info "Configurando archivo .pgpass..."

# Crear backup si existe
if [ -f "$PGPASS_FILE" ]; then
    cp "$PGPASS_FILE" "${PGPASS_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    print_success "Backup creado de .pgpass existente"
fi

# Formato: hostname:port:database:username:password
PGPASS_ENTRY="${POSTGRES_HOST}:${POSTGRES_PORT}:${POSTGRES_DB}:${POSTGRES_USER}:${POSTGRES_PASSWORD}"

# Crear o actualizar .pgpass
if [ -f "$PGPASS_FILE" ]; then
    # Eliminar entrada existente si hay
    sed -i "/${POSTGRES_HOST}:${POSTGRES_PORT}:${POSTGRES_DB}:${POSTGRES_USER}:/d" "$PGPASS_FILE"
fi

# Agregar nueva entrada
echo "$PGPASS_ENTRY" >> "$PGPASS_FILE"

# Establecer permisos correctos (requerido por PostgreSQL)
chmod 600 "$PGPASS_FILE"

print_success "Archivo .pgpass configurado en: $PGPASS_FILE"

# Crear alias para conexión rápida
BASHRC_FILE="$HOME/.bashrc"
ALIAS_NAME="pgconnect"
ALIAS_CMD="psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB"

if [ -f "$BASHRC_FILE" ]; then
    # Verificar si el alias ya existe
    if grep -q "alias $ALIAS_NAME=" "$BASHRC_FILE"; then
        print_info "Alias '$ALIAS_NAME' ya existe en .bashrc"
    else
        echo "" >> "$BASHRC_FILE"
        echo "# PostgreSQL - CRAC Monitoring" >> "$BASHRC_FILE"
        echo "alias $ALIAS_NAME='$ALIAS_CMD'" >> "$BASHRC_FILE"
        print_success "Alias '$ALIAS_NAME' agregado a .bashrc"
    fi
fi

# Actualizar archivos .env
print_info "Actualizando archivos .env..."

# Actualizar crm-sync-api/.env
if [ -f "crm-sync-api/.env" ]; then
    # Usar sed para actualizar o agregar POSTGRES_PASSWORD
    if grep -q "^POSTGRES_PASSWORD=" "crm-sync-api/.env"; then
        sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$POSTGRES_PASSWORD/" "crm-sync-api/.env"
    else
        echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD" >> "crm-sync-api/.env"
    fi
    print_success "crm-sync-api/.env actualizado"
fi

# Actualizar backend/.env
if [ -f "backend/.env" ]; then
    if grep -q "^POSTGRES_PASSWORD=" "backend/.env"; then
        sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$POSTGRES_PASSWORD/" "backend/.env"
    else
        echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD" >> "backend/.env"
    fi
    print_success "backend/.env actualizado"
fi

# Probar conexión sin contraseña
print_info "Probando conexión automática..."

if psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1" &> /dev/null; then
    print_success "Conexión automática configurada correctamente"
else
    print_error "La conexión automática falló"
    exit 1
fi

echo ""
echo "=================================================================="
echo "✅ Configuración completada exitosamente"
echo "=================================================================="
echo ""
echo "Ahora puedes conectarte a PostgreSQL sin contraseña usando:"
echo ""
echo "  psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB"
echo ""
echo "O simplemente usa el alias:"
echo ""
echo "  $ALIAS_NAME"
echo ""
print_warning "Nota: Ejecuta 'source ~/.bashrc' para activar el alias en esta sesión"
echo ""
print_info "Archivos actualizados:"
echo "  - $PGPASS_FILE (permisos: 600)"
echo "  - crm-sync-api/.env"
echo "  - backend/.env"
echo "  - $BASHRC_FILE (alias agregado)"
echo ""