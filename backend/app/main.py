from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config.settings import get_settings
from app.api import auth, devices, predictions, maintenance
from app.services.scheduler_service import get_scheduler_service
from app.services.preload_service import get_preload_service
import time
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuración
settings = get_settings()

# Crear aplicación FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    description="API para monitoreo predictivo de equipos CRAC",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware para logging de requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware para logging y timing de requests"""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log básico
    print(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
    
    return response


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handler global para excepciones no capturadas"""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Error interno del servidor",
            "detail": str(exc) if settings.DEBUG else "Contacte al administrador"
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Endpoint de health check"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "1.0.0"
    }


# Cache management endpoints
@app.get("/system/status")
async def system_status():
    """Obtiene estado del sistema y datos pre-cargados"""
    preload_service = get_preload_service()
    scheduler = get_scheduler_service()
    
    return {
        "system": "healthy",
        "data_preload": preload_service.get_status(),
        "scheduled_tasks": scheduler.get_all_tasks_status()
    }


@app.post("/system/refresh")
async def force_refresh():
    """Fuerza una actualización inmediata de los datos"""
    preload_service = get_preload_service()
    
    # Ejecutar en background para no bloquear
    import threading
    thread = threading.Thread(target=preload_service.force_refresh, daemon=True)
    thread.start()
    
    return {
        "success": True,
        "message": "Actualización iniciada en background"
    }


# Root endpoint
@app.get("/")
async def root():
    """Endpoint raíz con información de la API"""
    return {
        "message": "CRAC Monitoring API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/health"
    }


# Incluir routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(devices.router, prefix=settings.API_V1_PREFIX)
app.include_router(predictions.router, prefix=settings.API_V1_PREFIX)
app.include_router(maintenance.router, prefix=settings.API_V1_PREFIX)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Acciones al iniciar la aplicación"""
    logger.info("=" * 80)
    logger.info(f"🚀 {settings.APP_NAME} iniciado")
    logger.info(f"📚 Documentación disponible en: /api/docs")
    logger.info(f"🔒 CORS habilitado para: {settings.allowed_origins_list}")
    logger.info("=" * 80)
    
    # Iniciar servicio de pre-carga
    logger.info("🔄 Iniciando servicio de pre-carga de datos...")
    preload_service = get_preload_service()
    
    # Cargar datos iniciales
    logger.info("📊 Cargando datos iniciales (esto puede tomar 20-30 segundos)...")
    preload_service.refresh_all_data()
    
    # Programar actualización cada hora en punto
    logger.info("⏰ Programando actualización automática cada hora...")
    scheduler = get_scheduler_service()
    scheduler.schedule_task(
        task_name="refresh_data",
        func=preload_service.refresh_all_data,
        interval_minutes=60,  # Cada 60 minutos (1 hora)
        run_immediately=False  # Ya ejecutamos arriba
    )
    
    logger.info("=" * 80)
    logger.info("✅ Sistema listo - Próxima actualización a la siguiente hora en punto")
    logger.info("=" * 80)


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Acciones al cerrar la aplicación"""
    logger.info("🛑 Deteniendo tareas programadas...")
    scheduler = get_scheduler_service()
    scheduler.stop_all()
    logger.info(f"👋 {settings.APP_NAME} detenido")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )