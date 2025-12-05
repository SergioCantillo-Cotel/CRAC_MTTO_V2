# 🏢 Command Center CRAC - Monitoreo Predictivo

Sistema de monitoreo predictivo para equipos CRAC con arquitectura Backend (FastAPI) + Frontend (Streamlit) + API Externa de Mantenimientos.

## ✨ Características

- 🔐 **Autenticación JWT**: Sistema seguro de login con tokens
- 📊 **Monitoreo en Tiempo Real**: Visualización de estado de equipos CRAC
- 🤖 **Machine Learning**: Predicción de fallas con Random Survival Forest
- 📈 **Proyecciones de Riesgo**: Curvas de supervivencia y análisis predictivo
- 🎯 **Recomendaciones Inteligentes**: Priorización de mantenimiento preventivo
- 🔄 **Arquitectura Desacoplada**: Backend y Frontend completamente separados
- 🌐 **Integración API Externa**: Consume API REST para datos de mantenimiento
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
    ┌─────┴────┬──────────────────┐
    ▼          ▼                  ▼
┌────────┐ ┌──────────┐  ┌───────────────────┐
│BigQuery│ │  Otros   │  │ Mantenimientos API│
│        │ │Servicios │  │  (GCP - External) │
└────────┘ └──────────┘  └─────────┬─────────┘
                                    │
                                    ▼
                              ┌──────────┐
                              │PostgreSQL│
                              └──────────┘
```

## 🔧 Requisitos

### Requisitos del Sistema
- Python 3.11+
- Docker & Docker Compose (opcional pero recomendado)
- 4GB RAM mínimo
- Acceso a BigQuery
- Acceso a API de Mantenimientos (GCP)

## 🚀 Instalación

### Paso 1: Clonar Repositorio

```bash
git clone <repository-url>
cd crac-monitoring-new
```

### Paso 2: Configurar Variables de Entorno

#### Backend
```bash
cp backend/.env.example backend/.env
# Editar con credenciales reales
```

Variables requeridas en `backend/.env`:
```bash
# JWT Configuration
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# BigQuery Configuration
GCP_PROJECT_ID=your-project-id
GCP_DATASET=your-dataset
# ... (credenciales GCP)

# API Externa de Mantenimientos (NUEVO)
MANTENIMIENTOS_API_URL=https://api-bd-eficiencia-energetica-853514779938.us-central1.run.app
MANTENIMIENTOS_API_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Frontend
```bash
cp frontend/.env.example frontend/.env
```

Variables en `frontend/.env`:
```bash
API_BASE_URL=http://localhost:8000
```

### Paso 3: Opción Docker (Recomendado)

```bash
docker-compose up --build
```

### Paso 3 Alternativa: Instalación Manual

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Frontend
```bash
cd frontend
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## ⚙️ Configuración

### API Externa de Mantenimientos

El sistema consume un API REST externa alojada en Google Cloud Platform para obtener datos de mantenimiento:

- **URL Base**: `https://api-bd-eficiencia-energetica-853514779938.us-central1.run.app`
- **Autenticación**: Bearer Token
- **Endpoints**:
  - `GET /mantenimientos` - Consultar mantenimientos
  - `POST /mantenimientos` - Insertar nuevo mantenimiento

**Formato de consulta**:
```bash
curl -X GET "https://api-bd-eficiencia-energetica-853514779938.us-central1.run.app/mantenimientos?serial=in.(SERIAL1,SERIAL2)" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

**Formato de respuesta**:
```json
[
  {
    "serial": "JK1142005099",
    "datetime_maintenance_end": "2025-01-15T10:30:00",
    "customer_name": "CLIENTE SA",
    "device_brand": "APC",
    "device_model": "MODELO-123"
  }
]
```

## 📚 API Endpoints

### Backend Principal (Puerto 8000)
```
POST /api/v1/auth/login        # Login
GET  /api/v1/devices/list      # Lista de dispositivos
GET  /api/v1/devices/top-priority  # Top dispositivos críticos
GET  /api/v1/predictions/{dispositivo}  # Predicción individual
GET  /api/v1/maintenance/recommendations  # Recomendaciones
GET  /api/v1/maintenance/history/{serial}  # Historial de mantenimiento
```

## 🧪 Verificación

### Verificar Backend
```bash
# Health check
curl http://localhost:8000/health

# Estado del sistema
curl http://localhost:8000/system/status
```

### Verificar Frontend
```bash
# Acceder en navegador
http://localhost:8501
```

### Verificar API Externa
```bash
# Test de conexión
curl -X GET "https://api-bd-eficiencia-energetica-853514779938.us-central1.run.app/mantenimientos?limit=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 📊 Monitoreo

### Ver logs en tiempo real
```bash
# Docker
docker-compose logs -f backend
docker-compose logs -f frontend

# Manual
tail -f backend/logs/app.log
tail -f frontend/logs/app.log
```

## 🔒 Seguridad

- ✅ JWT con tokens de 24 horas
- ✅ Bearer Token para API externa
- ✅ Variables sensibles en archivos .env
- ✅ CORS configurado
- ✅ Validación de entrada con Pydantic
- ⚠️ Cambiar contraseñas por defecto en producción
- ⚠️ Usar HTTPS en producción
- ⚠️ Rotar tokens de API periódicamente

## 🐛 Troubleshooting

### Error de conexión con API externa
```bash
# Verificar token
curl -X GET "https://api-bd-eficiencia-energetica-853514779938.us-central1.run.app/mantenimientos?limit=1" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Verificar conectividad
ping api-bd-eficiencia-energetica-853514779938.us-central1.run.app
```

### Mantenimientos no aparecen
1. Verificar token en `.env` del backend
2. Ver logs del backend: `docker-compose logs backend`
3. Verificar conectividad a API externa
4. Verificar seriales en la consulta

### Token expirado
El Bearer Token tiene fecha de expiración (`exp: 1751334720`). Si el token expira:
1. Solicitar nuevo token al administrador del API
2. Actualizar `MANTENIMIENTOS_API_TOKEN` en `backend/.env`
3. Reiniciar el backend

## 📦 Estructura del Proyecto

```
crac-monitoring-new/
├── backend/              # API principal FastAPI
│   ├── app/
│   │   ├── api/         # Endpoints REST
│   │   ├── services/    # Lógica de negocio
│   │   │   ├── mantenimientos_api_client.py  # Cliente API Externa (NUEVO)
│   │   │   ├── bigquery_service.py
│   │   │   ├── ml_service.py
│   │   │   └── ...
│   │   └── ...
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/            # Interfaz Streamlit
│   ├── app.py
│   ├── components/
│   ├── services/
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml   # Orquestación Docker
└── README.md           # Este archivo
```

## 📈 Ventajas de la Nueva Arquitectura

| Aspecto | Antes | Después |
|---------|-------|---------|
| **Mantenibilidad** | Microservicio separado | Cliente integrado en backend |
| **Simplicidad** | 3 servicios independientes | 2 servicios principales |
| **Confiabilidad** | Depende de PostgreSQL local | API externa gestionada en GCP |
| **Escalabilidad** | Limitada por recursos locales | Aprovecha infraestructura cloud |
| **Seguridad** | Credenciales PostgreSQL locales | Bearer Token renovable |

## 📝 Changelog

### v3.0.0 (2025-01-XX)
- ♻️ Refactorización: Eliminado componente `crm-sync-api`
- ✨ Nuevo: Cliente para API REST de Mantenimientos (GCP)
- 🔄 Cambio: Backend consume API externa en vez de PostgreSQL directo
- ⚡ Mejora: Arquitectura más simple y mantenible
- 📚 Docs: Actualización completa de documentación

### v2.0.0 (2025-01-XX)
- ✨ Nuevo: CRM Sync API independiente
- ✨ Nuevo: Integración con PostgreSQL
- 🔄 Cambio: Backend consulta PostgreSQL en vez de CRM
- ⚡ Mejora: Performance en consultas de mantenimiento

## 📞 Soporte

Para problemas o preguntas:
1. Revisar sección de Troubleshooting
2. Ver logs de los servicios
3. Verificar conectividad con API externa
4. Crear issue en GitHub

## 📝 Licencia

Propietario - Todos los derechos reservados

---

**Versión**: 3.0.0  
**Última actualización**: 2025-01
**API Externa**: GCP Cloud Run