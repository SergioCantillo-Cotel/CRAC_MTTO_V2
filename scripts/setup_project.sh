#!/bin/bash

# ===================================================================
# Script de Configuración Completa del Proyecto
# Autor: CRAC Monitoring Team
# ===================================================================

set -e  # Salir si hay algún error

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funciones de utilidad
print_header() {
    echo ""
    echo "=================================================================="
    echo -e "${BLUE}$1${NC}"
    echo "=================================================================="
    echo ""
}

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

# Banner
clear
cat << "EOF"
    ____  ____  ___   ______   __  ___            _ __            _            
   / __ \/ __ \/   | / ____/  /  |/  /___  ____  (_) /_____  ____(_)___  ____ _
  / / / / /_/ / /| |/ /      / /|_/ / __ \/ __ \/ / __/ __ \/ __/ / __ \/ __ `/
 / /_/ / _, _/ ___ / /___   / /  / / /_/ / / / / / /_/ /_/ / / / / / / / /_/ / 
 \____/_/ |_/_/  |_\____/  /_/  /_/\____/_/ /_/_/\__/\____/_/ /_/_/ /_/\__, /  
                                                                        /____/   
EOF
echo ""
echo "Configuración Completa del Proyecto - CRAC Monitoring"
echo ""

# Verificar que estamos en el directorio raíz del proyecto
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    print_error "Este script debe ejecutarse desde el directorio raíz del proyecto"
    exit 1
fi

print_header "1. Verificando requisitos del sistema"

# Verificar Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    print_success "Python instalado: $PYTHON_VERSION"
else
    print_error "Python 3 no está instalado"
    exit 1
fi

# Verificar PostgreSQL
if command -v psql &> /dev/null; then
    PSQL_VERSION=$(psql --version | awk '{print $3}')
    print_success "PostgreSQL instalado: $PSQL_VERSION"
else
    print_warning "psql no está en PATH (puede estar instalado pero no accesible)"
fi

# Verificar Docker (opcional)
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
    print_success "Docker instalado: $DOCKER_VERSION"
else
    print_warning "Docker no está instalado (opcional)"
fi

print_header "2. Configurando estructura de directorios"

# Crear directorios necesarios
mkdir -p database
mkdir -p scripts
mkdir -p logs
mkdir -p backups

print_success "Directorios creados"

print_header "3. Configurando archivos .env"

# CRM Sync API
if [ ! -f "crm-sync-api/.env" ]; then
    if [ -f "crm-sync-api/.env.example" ]; then
        cp crm-sync-api/.env.example crm-sync-api/.env
        print_success "Creado crm-sync-api/.env desde .env.example"
        print_warning "IMPORTANTE: Edita crm-sync-api/.env con tus credenciales reales"
    else
        print_warning "No existe crm-sync-api/.env.example"
    fi
else
    print_info "crm-sync-api/.env ya existe"
fi

# Backend
if [ ! -f "backend/.env" ]; then
    if [ -f "backend/.env.example" ]; then
        cp backend/.env.example backend/.env
        print_success "Creado backend/.env desde .env.example"
        print_warning "IMPORTANTE: Edita backend/.env con tus credenciales reales"
    else
        print_warning "No existe backend/.env.example"
    fi
else
    print_info "backend/.env ya existe"
fi

# Frontend
if [ ! -f "frontend/.env" ]; then
    echo "API_BASE_URL=http://localhost:8000" > frontend/.env
    print_success "Creado frontend/.env"
else
    print_info "frontend/.env ya existe"
fi

print_header "4. Configurando base de datos PostgreSQL"

print_info "Configuración de PostgreSQL:"
echo "  Host: 127.0.0.1"
echo "  Port: 5432"
echo "  Database: eficiencia_energetica"
echo "  User: api_crud_monitoreo_equipos"
echo ""

read -p "¿Deseas probar la conexión a PostgreSQL ahora? (s/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Ss]$ ]]; then
    print_info "Probando conexión a PostgreSQL..."
    
    # Solicitar password
    read -sp "Ingresa la contraseña de PostgreSQL: " PGPASSWORD
    export PGPASSWORD
    echo ""
    
    if psql -h 127.0.0.1 -p 5432 -U api_crud_monitoreo_equipos -d eficiencia_energetica -c "SELECT 1" &> /dev/null; then
        print_success "Conexión a PostgreSQL exitosa"
        
        # Verificar si la tabla existe
        TABLE_EXISTS=$(psql -h 127.0.0.1 -p 5432 -U api_crud_monitoreo_equipos -d eficiencia_energetica -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'mantenimientos');" | xargs)
        
        if [ "$TABLE_EXISTS" = "t" ]; then
            print_success "Tabla 'mantenimientos' ya existe"
        else
            print_warning "Tabla 'mantenimientos' NO existe"
            
            read -p "¿Deseas crear la tabla ahora? (s/n): " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Ss]$ ]]; then
                if [ -f "database/init_mantenimientos.sql" ]; then
                    psql -h 127.0.0.1 -p 5432 -U api_writter_monitoreo_sedes_telemetria -d eficiencia_energetica -f database/init_mantenimientos.sql
                    print_success "Tabla creada exitosamente"
                else
                    print_error "Archivo database/init_mantenimientos.sql no encontrado"
                fi
            fi
        fi
    else
        print_error "No se pudo conectar a PostgreSQL"
        print_info "Verifica que PostgreSQL esté corriendo y las credenciales sean correctas"
    fi
    
    unset PGPASSWORD
fi

print_header "5. Configurando entornos virtuales Python"

# CRM Sync API
print_info "Configurando CRM Sync API..."
cd crm-sync-api
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Entorno virtual creado en crm-sync-api/"
else
    print_info "Entorno virtual ya existe en crm-sync-api/"
fi

source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
print_success "Dependencias instaladas en crm-sync-api/"
deactivate
cd ..

# Backend
print_info "Configurando Backend..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Entorno virtual creado en backend/"
else
    print_info "Entorno virtual ya existe en backend/"
fi

source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
print_success "Dependencias instaladas en backend/"
deactivate
cd ..

# Frontend
print_info "Configurando Frontend..."
cd frontend
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Entorno virtual creado en frontend/"
else
    print_info "Entorno virtual ya existe en frontend/"
fi

source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
print_success "Dependencias instaladas en frontend/"
deactivate
cd ..

print_header "6. Creando scripts de utilidad"

# Script de inicio rápido
cat > start_services.sh << 'EOFSCRIPT'
#!/bin/bash

echo "Iniciando servicios CRAC Monitoring..."

# Iniciar CRM Sync API
echo "Iniciando CRM Sync API (puerto 8001)..."
cd crm-sync-api
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001 > ../logs/crm-sync-api.log 2>&1 &
CRM_PID=$!
echo $CRM_PID > ../logs/crm-sync-api.pid
deactivate
cd ..

sleep 2

# Iniciar Backend
echo "Iniciando Backend (puerto 8000)..."
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > ../logs/backend.pid
deactivate
cd ..

sleep 2

# Iniciar Frontend
echo "Iniciando Frontend (puerto 8501)..."
cd frontend
source venv/bin/activate
streamlit run app.py > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../logs/frontend.pid
deactivate
cd ..

echo ""
echo "✅ Todos los servicios iniciados"
echo ""
echo "URLs:"
echo "  - Frontend: http://localhost:8501"
echo "  - Backend: http://localhost:8000"
echo "  - CRM Sync API: http://localhost:8001"
echo ""
echo "PIDs guardados en logs/"
echo "Para detener: ./stop_services.sh"
EOFSCRIPT

chmod +x start_services.sh
print_success "Script start_services.sh creado"

# Script de detención
cat > stop_services.sh << 'EOFSCRIPT'
#!/bin/bash

echo "Deteniendo servicios CRAC Monitoring..."

# Detener servicios
for service in crm-sync-api backend frontend; do
    if [ -f "logs/${service}.pid" ]; then
        PID=$(cat logs/${service}.pid)
        if kill -0 $PID 2>/dev/null; then
            kill $PID
            echo "✅ ${service} detenido (PID: $PID)"
        else
            echo "⚠️  ${service} no estaba corriendo"
        fi
        rm logs/${service}.pid
    fi
done

echo ""
echo "✅ Todos los servicios detenidos"
EOFSCRIPT

chmod +x stop_services.sh
print_success "Script stop_services.sh creado"

print_header "7. Resumen de Configuración"

cat << EOF
✅ Configuración completada exitosamente

📁 Estructura del proyecto:
   - crm-sync-api/    (API de sincronización CRM → PostgreSQL)
   - backend/         (API principal FastAPI)
   - frontend/        (Interfaz Streamlit)
   - database/        (Scripts SQL)
   - logs/            (Logs de aplicaciones)
   - backups/         (Backups de base de datos)

🔧 Próximos pasos:

1. Editar archivos .env con credenciales reales:
   - crm-sync-api/.env (credenciales CRM y PostgreSQL)
   - backend/.env (credenciales BigQuery y PostgreSQL)

2. Verificar conexión a PostgreSQL:
   python3 scripts/test_postgres_connection.py

3. Iniciar servicios:
   ./start_services.sh

4. Acceder a la aplicación:
   http://localhost:8501

5. Detener servicios:
   ./stop_services.sh

📚 Documentación:
   - README.md
   - GUIA_MIGRACION.md
   - COMANDOS_UTILES.md

🔗 URLs de los servicios:
   - Frontend:     http://localhost:8501
   - Backend:      http://localhost:8000/api/docs
   - CRM Sync API: http://localhost:8001/health

EOF

print_success "¡Configuración completada! Lee los próximos pasos arriba."
echo ""