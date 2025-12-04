from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import List
from pydantic import BaseModel
from app.config.settings import get_settings
from app.models.database import init_db
from app.services.sync_service import get_sync_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="API para sincronización de datos CRM a PostgreSQL",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SyncRequest(BaseModel):
    seriales: List[str]

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.APP_NAME}

@app.post("/sync")
async def trigger_sync(request: SyncRequest):
    try:
        sync_service = get_sync_service()
        stats = sync_service.sync_mantenimientos(request.seriales)
        return {
            "success": True,
            "message": "Sincronización completada",
            "statistics": stats
        }
    except Exception as e:
        logger.error(f"Error en sincronización: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    logger.info("=" * 80)
    logger.info(f"🚀 {settings.APP_NAME} iniciado")
    logger.info("=" * 80)
    logger.info("📊 Inicializando base de datos...")
    init_db()
    logger.info("✅ Base de datos lista")
    logger.info("=" * 80)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=settings.DEBUG)