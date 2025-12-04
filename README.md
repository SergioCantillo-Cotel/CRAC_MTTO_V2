# 🏢 Command Center CRAC - Monitoreo Predictivo

Sistema de monitoreo predictivo para equipos CRAC con arquitectura Backend (FastAPI) + Frontend (Streamlit) + CRM Sync API.

## ✨ Características

- 🔐 **Autenticación JWT**: Sistema seguro de login con tokens
- 📊 **Monitoreo en Tiempo Real**: Visualización de estado de equipos CRAC
- 🤖 **Machine Learning**: Predicción de fallas con Random Survival Forest
- 📈 **Proyecciones de Riesgo**: Curvas de supervivencia y análisis predictivo
- 🎯 **Recomendaciones Inteligentes**: Priorización de mantenimiento preventivo
- 🔄 **Arquitectura Desacoplada**: Backend, Frontend y CRM Sync completamente separados
- 🗄️ **PostgreSQL**: Cache persistente de datos del CRM
- 🐳 **Docker Ready**: Despliegue fácil con Docker Compose

## 🏗️ Arquitectura

```
┌─────────────────────┐
│   Frontend (8501)   │  Streamlit UI
│   - Visualizaciones │
│   - Interacción     │
└──────────┬──────────┘
           │ HTTP/REST
           ▼
┌─────────────────────┐
│   Backend (8000)    │  FastAPI Principal
│   - Autenticación   │
│   - Machine Learning│
│   - Lógica de       │
│     Negocio         │
└─────────┬───────────┘
          │
    ┌─────┴────┬──────────┐
    ▼          ▼          ▼
┌────────┐ ┌──────────┐ ┌────────┐
│BigQuery│ │PostgreSQL│ │  ...   │
│        │ │          │ │        │
└────────┘ └────┬─────┘ └────────┘
                │
                ▼
        ┌───────────────┐
        │  CRM Sync API │  Puerto 8001
        │   (FastAPI)   │
        │ - Sincroniza  │
        │   CRM → PG    │
        └───────┬───────┘
                │
                ▼
           ┌────────┐
           │  CRM   │
           │  API   │
           └────────┘
```

## 🔧 Requisitos

### Requisitos del Sistema
- Python 3.11+
- PostgreSQL 12+ (con acceso vía ProxySQL en WSL)
- Docker & Docker Compose (opcional pero recomendado)
- 4GB RAM mínimo
- Acceso a BigQuery
- Acceso a CRM API

## 🚀 Instalación

### Paso 1: Configurar Base de Datos

```bash
# Conectar a PostgreSQL
psql -h localhost -p 5432 -U tu_usuario -d eficiencia_energetica

# Ejecutar script de inicialización
\i database/init_mantenimientos.sql
```

### Paso 2: Configurar Variables de Entorno

```bash
# CRM Sync API
cp crm-sync-api/.env.example crm-sync-api/.env
# Editar con credenciales reales

# Backend
cp backend/.env.example backend/.env
# Agregar configuración de PostgreSQL

# Frontend
cp frontend/.env.example frontend/.env
```

### Paso 3: Opción Docker (Recomendado)

```bash
docker-compose up --build
```

### Paso 3 Alternativa: Instalación Manual

#### CRM Sync API
```bash
cd crm-sync-api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Frontend
```bash
cd frontend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## ⚙️ Configuración

### Nuevas Variables de Entorno (Backend y CRM Sync API)

```bash
# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=eficiencia_energetica
POSTGRES_USER=tu_usuario
POSTGRES_PASSWORD=tu_password
```

## 🔄 Sincronización CRM

### Automática
- Se ejecuta cada hora en punto
- Sincroniza datos del CRM a PostgreSQL
- Logs detallados de cada sincronización

### Manual
```bash
curl -X POST http://localhost:8001/sync \
  -H "Content-Type: application/json" \
  -d '{"seriales": ["JK1142005099", "JK2117000712"]}'
```

## 📚 API Endpoints

### CRM Sync API (Puerto 8001)
```
GET  /health                    # Health check
POST /sync                      # Forzar sincronización
GET  /mantenimientos           # Obtener mantenimientos
GET  /mantenimientos/metadata  # Obtener metadatos
GET  /stats                    # Estadísticas de BD
```

### Backend Principal (Puerto 8000)
```
POST /api/v1/auth/login        # Login
GET  /api/v1/devices/list      # Lista de dispositivos
GET  /api/v1/devices/top-priority  # Top dispositivos críticos
GET  /api/v1/predictions/{dispositivo}  # Predicción individual
GET  /api/v1/maintenance/recommendations  # Recomendaciones
```

## 🧪 Verificación

```bash
# Verificar CRM Sync API
curl http://localhost:8001/health
curl http://localhost:8001/stats

# Verificar Backend
curl http://localhost:8000/health

# Verificar PostgreSQL
psql -h localhost -p 5432 -U tu_usuario -d eficiencia_energetica \
  -c "SELECT COUNT(*) FROM mantenimientos;"
```

## 📊 Monitoreo

### Ver logs en tiempo real
```bash
# Docker
docker-compose logs -f crm-sync-api
docker-compose logs -f backend

# Manual
tail -f crm-sync-api/logs/app.log
tail -f backend/logs/app.log
```

## 🔒 Seguridad

- ✅ JWT con tokens de 24 horas
- ✅ Credenciales del CRM aisladas en CRM Sync API
- ✅ Variables sensibles en archivos .env
- ✅ CORS configurado
- ✅ Validación de entrada con Pydantic
- ⚠️ Cambiar contraseñas por defecto en producción
- ⚠️ Usar HTTPS en producción

## 🐛 Troubleshooting

### PostgreSQL Connection Refused
```bash
# Verificar servicio
sudo systemctl status postgresql

# Verificar puerto
netstat -an | grep 5432
```

### CRM Token Failed
- Verificar credenciales en `.env`
- Ver logs de CRM Sync API
- Verificar conectividad al CRM

### Mantenimientos no aparecen
```bash
# Verificar datos en BD
psql -h localhost -p 5432 -U tu_usuario -d eficiencia_energetica \
  -c "SELECT COUNT(*) FROM mantenimientos;"

# Forzar sincronización
curl -X POST http://localhost:8001/sync \
  -H "Content-Type: application/json" \
  -d '{"seriales": ["JK1142005099"]}'
```

## 📦 Estructura del Proyecto

```
crac-monitoring-new/
├── backend/              # API principal FastAPI
├── crm-sync-api/        # API sincronización CRM (NUEVO)
├── frontend/            # Interfaz Streamlit
├── database/            # Scripts SQL (NUEVO)
├── docker-compose.yml   # Orquestación Docker
└── README.md           # Este archivo
```

## 📈 Ventajas de la Nueva Arquitectura

| Aspecto | Antes | Después |
|---------|-------|---------|
| **Performance** | 5-10s por consulta CRM | 0.1-0.3s desde PostgreSQL |
| **Disponibilidad** | Depende del CRM | Datos cacheados en BD |
| **Mantenibilidad** | Lógica mezclada | Servicios separados |
| **Escalabilidad** | Limitada por CRM | Múltiples servicios |

## 📝 Changelog

### v2.0.0 (2025-01-XX)
- ✨ Nuevo: CRM Sync API independiente
- ✨ Nuevo: Integración con PostgreSQL
- ✨ Nuevo: Sincronización automática cada hora
- 🔄 Cambio: Backend consulta PostgreSQL en vez de CRM
- ⚡ Mejora: Performance en consultas de mantenimiento (50x más rápido)
- 📚 Docs: Guía de migración completa

## 📞 Soporte

Para problemas o preguntas:
1. Revisar sección de Troubleshooting
2. Consultar GUIA_MIGRACION.md
3. Ver logs de los servicios
4. Crear issue en GitHub

## 📝 Licencia

Propietario - Todos los derechos reservados

---

**Versión**: 2.0.0  
**Última actualización**: 2025-01