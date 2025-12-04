import threading
import time
import logging
from datetime import datetime, timedelta
from app.services.sync_service import get_sync_service
from app.config.settings import get_settings
from app.config.known_serials import KNOWN_SERIALS  # Importar desde configuración

logger = logging.getLogger(__name__)

_scheduler_thread = None
_stop_flag = threading.Event()


def sync_task():
    """Tarea de sincronización programada"""
    settings = get_settings()
    sync_service = get_sync_service()
    
    while not _stop_flag.is_set():
        try:
            # Calcular tiempo hasta la próxima hora en punto
            now = datetime.now()
            next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            wait_seconds = (next_hour - now).total_seconds()
            
            logger.info(f"⏰ Próxima sincronización en {wait_seconds/60:.1f} minutos (a las {next_hour.strftime('%H:%M')})")
            
            # Esperar hasta la próxima hora
            if _stop_flag.wait(timeout=wait_seconds):
                break  # Se canceló
            
            # Ejecutar sincronización
            logger.info("🔄 Iniciando sincronización programada...")
            sync_service.sync_mantenimientos(KNOWN_SERIALS)
            
        except Exception as e:
            logger.error(f"❌ Error en tarea de sincronización: {e}")
            # Esperar 5 minutos antes de reintentar en caso de error
            _stop_flag.wait(timeout=300)


def start_scheduler():
    """Inicia el scheduler de sincronización"""
    global _scheduler_thread
    
    if _scheduler_thread is not None and _scheduler_thread.is_alive():
        logger.warning("⚠️ Scheduler ya está en ejecución")
        return
    
    _stop_flag.clear()
    _scheduler_thread = threading.Thread(target=sync_task, daemon=True, name="SyncScheduler")
    _scheduler_thread.start()
    logger.info("✅ Scheduler de sincronización iniciado")


def stop_scheduler():
    """Detiene el scheduler"""
    global _scheduler_thread
    
    if _scheduler_thread is None or not _scheduler_thread.is_alive():
        logger.warning("⚠️ Scheduler no está en ejecución")
        return
    
    _stop_flag.set()
    _scheduler_thread.join(timeout=5)
    logger.info("✅ Scheduler detenido")