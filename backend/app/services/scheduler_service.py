import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class SchedulerService:
    """Servicio para ejecutar tareas programadas periódicamente"""
    
    def __init__(self):
        self._tasks = {}
        self._threads = {}
        self._stop_flags = {}
        self._last_run = {}
        self._running = False
    
    def schedule_task(
        self, 
        task_name: str, 
        func: Callable, 
        interval_minutes: int,
        run_immediately: bool = False
    ):
        """
        Programa una tarea para ejecutarse periódicamente
        
        Args:
            task_name: Nombre único de la tarea
            func: Función a ejecutar
            interval_minutes: Intervalo en minutos
            run_immediately: Si ejecutar inmediatamente al programar
        """
        if task_name in self._tasks:
            logger.warning(f"Tarea '{task_name}' ya existe. Se reemplazará.")
            self.cancel_task(task_name)
        
        self._tasks[task_name] = {
            'func': func,
            'interval': interval_minutes,
            'run_immediately': run_immediately
        }
        
        self._stop_flags[task_name] = threading.Event()
        
        # Crear thread para la tarea
        thread = threading.Thread(
            target=self._run_task,
            args=(task_name,),
            daemon=True,
            name=f"Scheduler-{task_name}"
        )
        self._threads[task_name] = thread
        thread.start()
        
        logger.info(f"✅ Tarea '{task_name}' programada cada {interval_minutes} minutos")
    
    def _run_task(self, task_name: str):
        """Ejecuta una tarea en loop"""
        task_config = self._tasks[task_name]
        func = task_config['func']
        interval = task_config['interval']
        run_immediately = task_config['run_immediately']
        
        # Ejecutar inmediatamente si se requiere
        if run_immediately:
            logger.info(f"🚀 Ejecutando tarea '{task_name}' inmediatamente...")
            try:
                func()
                self._last_run[task_name] = datetime.now()
                logger.info(f"✅ Tarea '{task_name}' completada")
            except Exception as e:
                logger.error(f"❌ Error en tarea '{task_name}': {str(e)}")
        
        # Loop principal
        while not self._stop_flags[task_name].is_set():
            # Calcular tiempo hasta la próxima hora en punto
            now = datetime.now()
            next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            wait_seconds = (next_hour - now).total_seconds()
            
            logger.info(f"⏰ Tarea '{task_name}' se ejecutará en {wait_seconds/60:.1f} minutos (a las {next_hour.strftime('%H:%M')})")
            
            # Esperar hasta la próxima hora (o hasta que se cancele)
            if self._stop_flags[task_name].wait(timeout=wait_seconds):
                break  # Se canceló la tarea
            
            # Ejecutar tarea
            logger.info(f"🚀 Ejecutando tarea '{task_name}'...")
            try:
                start_time = time.time()
                func()
                elapsed = time.time() - start_time
                self._last_run[task_name] = datetime.now()
                logger.info(f"✅ Tarea '{task_name}' completada en {elapsed:.2f}s")
            except Exception as e:
                logger.error(f"❌ Error en tarea '{task_name}': {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
    
    def cancel_task(self, task_name: str):
        """Cancela una tarea programada"""
        if task_name in self._stop_flags:
            self._stop_flags[task_name].set()
            
            # Esperar a que el thread termine
            if task_name in self._threads:
                self._threads[task_name].join(timeout=5)
                del self._threads[task_name]
            
            del self._stop_flags[task_name]
            del self._tasks[task_name]
            self._last_run.pop(task_name, None)
            
            logger.info(f"🛑 Tarea '{task_name}' cancelada")
    
    def get_task_status(self, task_name: str) -> Optional[dict]:
        """Obtiene el estado de una tarea"""
        if task_name not in self._tasks:
            return None
        
        last_run = self._last_run.get(task_name)
        task_config = self._tasks[task_name]
        
        # Calcular próxima ejecución
        if last_run:
            next_run = last_run + timedelta(minutes=task_config['interval'])
        else:
            next_run = datetime.now()
        
        return {
            'task_name': task_name,
            'interval_minutes': task_config['interval'],
            'last_run': last_run.isoformat() if last_run else None,
            'next_run': next_run.isoformat(),
            'is_running': task_name in self._threads and self._threads[task_name].is_alive(),
            'minutes_until_next': (next_run - datetime.now()).total_seconds() / 60
        }
    
    def get_all_tasks_status(self) -> dict:
        """Obtiene el estado de todas las tareas"""
        return {
            task_name: self.get_task_status(task_name)
            for task_name in self._tasks.keys()
        }
    
    def stop_all(self):
        """Detiene todas las tareas"""
        logger.info("🛑 Deteniendo todas las tareas programadas...")
        for task_name in list(self._tasks.keys()):
            self.cancel_task(task_name)
        logger.info("✅ Todas las tareas detenidas")


# Singleton
_scheduler_service = None


def get_scheduler_service() -> SchedulerService:
    """Obtiene instancia singleton del servicio de scheduler"""
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    return _scheduler_service