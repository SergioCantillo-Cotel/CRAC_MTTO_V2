# 🏢 Command Center CRAC - Monitoreo Predictivo

Sistema de monitoreo predictivo para equipos CRAC con arquitectura Backend (FastAPI) + Frontend (Streamlit).

## 📋 Tabla de Contenidos

- [Características](#características)
- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Despliegue](#despliegue)
- [API Documentación](#api-documentación)
- [Desarrollo](#desarrollo)

## ✨ Características

- 🔐 **Autenticación JWT**: Sistema seguro de login con tokens
- 📊 **Monitoreo en Tiempo Real**: Visualización de estado de equipos CRAC
- 🤖 **Machine Learning**: Predicción de fallas con Random Survival Forest
- 📈 **Proyecciones de Riesgo**: Curvas de supervivencia y análisis predictivo
- 🎯 **Recomendaciones Inteligentes**: Priorización de mantenimiento preventivo
- 🔄 **Arquitectura Desacoplada**: Backend y Frontend completamente separados
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
│   Backend (8000)    │  FastAPI
│   - Autenticación   │
│   - Machine Learning│
│   - Integración DB  │
│   - Lógica de       │
│     Negocio         │
└─────────┬───────────┘
          │
    ┌─────┴──────┬──────────┐
    ▼            ▼          ▼
┌────────┐  ┌────────┐  ┌────────┐
│BigQuery│  │  CRM   │  │ Redis  │
│        │  │  API   │  │ (Cache)│
└────────┘  └────────┘  └────────┘
```

## 🔧 Requisitos

### Requisitos del Sistema
- Python 3.11+
- Docker & Docker Compose (opcional pero recomendado)
- 4GB RAM mínimo
- Acceso a BigQuery
- Acceso a CRM API

### Dependencias Principales
- **Backend**: FastAPI, scikit-survival, pandas, google-cloud-bigquery
- **Frontend**: Streamlit, plotly, requests

## 🚀 Instalación

### Opción 1: Docker (Recomendado)

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd crac-monitoring
```

2. **Configurar variables de entorno**
```bash
# Backend
cp backend/.env.example backend/.env
# Editar backend/.env con tus credenciales

# Frontend
cp frontend/.env.example frontend/.env
# Editar frontend/.env (por defecto: http://localhost:8000)
```

3. **Construir y ejecutar**
```bash
docker-compose up --build
```

4. **Acceder a la aplicación**
- Frontend: http://localhost:8501
- Backend API Docs: http://localhost:8000/api/docs

### Opción 2: Instalación Manual

#### Backend

```bash
cd backend

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# Ejecutar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variable de entorno
echo "API_BASE_URL=http://localhost:8000" > .env

# Ejecutar aplicación
streamlit run app.py
```

## ⚙️ Configuración

### Backend (.env)

```bash
# JWT Configuration
SECRET_KEY=your-super-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# BigQuery
GCP_PROJECT_ID=your-project-id
GCP_DATASET=your-dataset
GCP_SERVICE_ACCOUNT_TYPE=service_account
GCP_SERVICE_ACCOUNT_PROJECT_ID=...
GCP_SERVICE_ACCOUNT_PRIVATE_KEY_ID=...
GCP_SERVICE_ACCOUNT_PRIVATE_KEY=...
GCP_SERVICE_ACCOUNT_CLIENT_EMAIL=...
GCP_SERVICE_ACCOUNT_CLIENT_ID=...
GCP_SERVICE_ACCOUNT_AUTH_URI=...
GCP_SERVICE_ACCOUNT_TOKEN_URI=...
GCP_SERVICE_ACCOUNT_AUTH_PROVIDER_CERT_URL=...
GCP_SERVICE_ACCOUNT_CLIENT_CERT_URL=...

# CRM API
CRM_BASE_URL=https://crmcotel.com.co
CRM_CLIENT_ID=your-client-id
CRM_CLIENT_SECRET=your-client-secret

# CORS
ALLOWED_ORIGINS=http://localhost:8501,https://your-streamlit-app.com
```

### Frontend (.env)

```bash
API_BASE_URL=http://localhost:8000
# Para producción: API_BASE_URL=https://your-backend-api.com
```

### Usuarios por Defecto

```python
# Usuarios configurados en backend/app/auth/users.py
admin / admin123!         # Administrador (todos los clientes)
EAFIT / EAFIT1!          # Operador (Universidad EAFIT)
UNICAUCA / UCA1!         # Operador (Universidad del Cauca)
```

⚠️ **IMPORTANTE**: Cambiar estas contraseñas en producción

## 📚 API Documentación

### Documentación Interactiva

Una vez que el backend esté corriendo:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### Principales Endpoints

#### Autenticación
```
POST /api/v1/auth/login          # Login y obtención de token
GET  /api/v1/auth/me             # Info del usuario actual
POST /api/v1/auth/validate       # Validar token
```

#### Dispositivos
```
GET  /api/v1/devices/alarms      # Obtener alarmas
GET  /api/v1/devices/list        # Lista de dispositivos
GET  /api/v1/devices/top-priority # Top dispositivos prioritarios
```

#### Predicciones
```
GET  /api/v1/predictions/{dispositivo}  # Predicción individual
POST /api/v1/predictions/batch          # Predicciones múltiples
```

#### Mantenimiento
```
GET /api/v1/maintenance/recommendations  # Recomendaciones
GET /api/v1/maintenance/history/{serial} # Historial
```

### Ejemplo de Uso

```python
import requests

# Login
response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"username": "admin", "password": "admin123!"}
)
token = response.json()["access_token"]

# Obtener dispositivos
headers = {"Authorization": f"Bearer {token}"}
devices = requests.get(
    "http://localhost:8000/api/v1/devices/list",
    headers=headers
).json()
```

## 🐳 Despliegue

### Docker Compose (Producción)

1. **Preparar archivos de configuración**
```bash
# Asegurarse de tener .env configurado
ls -la backend/.env frontend/.env
```

2. **Construir imágenes**
```bash
docker-compose build
```

3. **Ejecutar en modo detached**
```bash
docker-compose up -d
```

4. **Ver logs**
```bash
docker-compose logs -f
```

5. **Detener servicios**
```bash
docker-compose down
```

### Despliegue en Cloud

#### Backend (FastAPI)

**Opciones:**
- **Railway**: `railway up` (requiere Railway CLI)
- **Heroku**: Procfile incluido
- **Google Cloud Run**:
  ```bash
  gcloud run deploy crac-backend \
    --source ./backend \
    --platform managed \
    --region us-central1
  ```

#### Frontend (Streamlit)

**Opciones:**
- **Streamlit Cloud**: Push a GitHub y conectar
- **Heroku**: Configurar con `Procfile`
- **Google Cloud Run**:
  ```bash
  gcloud run deploy crac-frontend \
    --source ./frontend \
    --platform managed \
    --region us-central1
  ```

⚠️ **Importante**: Al desplegar frontend, actualizar `API_BASE_URL` con la URL pública del backend

## 💻 Desarrollo

### Estructura del Proyecto

```
crac-monitoring/
├── backend/
│   ├── app/
│   │   ├── api/              # Endpoints REST
│   │   ├── auth/             # Autenticación JWT
│   │   ├── config/           # Configuración
│   │   ├── models/           # Modelos Pydantic
│   │   ├── services/         # Lógica de negocio
│   │   └── main.py           # App FastAPI
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── components/           # Componentes UI
│   ├── services/             # Cliente API
│   ├── utils/                # Utilidades
│   ├── styles/               # CSS
│   ├── app.py                # App Streamlit
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

### Agregar Nuevo Endpoint (Backend)

1. Crear endpoint en `backend/app/api/`
2. Agregar router en `backend/app/main.py`
3. Documentar con Pydantic schemas

### Agregar Nueva Vista (Frontend)

1. Crear componente en `frontend/components/`
2. Agregar método al API client en `frontend/services/api_client.py`
3. Integrar en tabs correspondiente

### Testing

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
streamlit run app.py
```

## 🔒 Seguridad

- ✅ Autenticación JWT
- ✅ CORS configurado
- ✅ Variables de entorno para secretos
- ✅ Validación de entrada con Pydantic
- ⚠️ Cambiar contraseñas por defecto
- ⚠️ Usar HTTPS en producción
- ⚠️ Rotar SECRET_KEY periódicamente

## 🐛 Troubleshooting

### Error de Conexión Backend

```bash
# Verificar que el backend esté corriendo
curl http://localhost:8000/health

# Ver logs
docker-compose logs backend
```

### Error de Autenticación

```bash
# Verificar SECRET_KEY en backend/.env
# Asegurarse de que los usuarios existan en backend/app/auth/users.py
```

### Error de BigQuery

```bash
# Verificar credenciales GCP en backend/.env
# Verificar permisos del service account
```

## 📞 Soporte

Para reportar problemas o solicitar características:
- Crear issue en GitHub
- Contactar al equipo de desarrollo

## 📝 Licencia

Propietario - Todos los derechos reservados

---

**Versión**: 1.0.0
**Última actualización**: 2025