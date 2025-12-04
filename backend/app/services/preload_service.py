import logging
import pandas as pd
from datetime import datetime
from typing import Optional, Dict
from app.services.bigquery_service import get_bigquery_service
from app.services.analytics_service import get_analytics_service
from app.services.ml_service import get_ml_service
from app.services.postgres_service import get_postgres_service
from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class DataPreloadService:
    """Servicio para pre-cargar y cachear datos cada hora"""
    
    def __init__(self):
        self.settings = get_settings()
        self._cached_data = {
            'df_raw': None,
            'df_processed': None,
            'intervals': None,
            'model': None,
            'features': None,
            'maintenance_dict': None,
            'brand_dict': None,
            'model_dict': None,
            'client_dict': None,
            'last_update': None
        }
        self._is_updating = False
    
    def refresh_all_data(self):
        """
        Refresca todos los datos: BigQuery, PostgreSQL (mantenimientos) y entrena modelo ML
        Esta función se ejecuta cada hora
        """
        if self._is_updating:
            logger.warning("⚠️ Actualización ya en progreso, saltando...")
            return
        
        try:
            self._is_updating = True
            start_time = datetime.now()
            logger.info("=" * 80)
            logger.info(f"🔄 INICIANDO ACTUALIZACIÓN PROGRAMADA - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 80)
            
            # 1. Obtener datos de BigQuery
            logger.info("📊 [1/5] Consultando BigQuery...")
            bigquery_service = get_bigquery_service()
            analytics_service = get_analytics_service()
            
            dispositivos_excluir = [
                '10.102.148.11', '10.102.148.13', '10.102.148.16', '10.102.148.10',
                '10.102.148.19', '10.102.148.12', '10.102.148.20', '10.102.148.15',
                '10.102.148.21', '10.102.148.17', '10.102.148.18', '10.102.148.14',
                '10.102.148.23', '10.102.148.22'
            ]
            
            df_raw = bigquery_service.get_all_alarms(dispositivos_excluir)
            logger.info(f"   ✅ BigQuery: {len(df_raw)} alarmas obtenidas")
            
            # 2. Completar seriales y procesar datos
            logger.info("🔧 [2/5] Procesando datos...")
            df_raw = analytics_service.completar_seriales(df_raw)
            df_processed = analytics_service.process_data(df_raw)
            logger.info(f"   ✅ Procesamiento: {len(df_processed)} registros válidos")
            
            # 3. Obtener datos de mantenimiento desde PostgreSQL (CAMBIO PRINCIPAL)
            logger.info("🗄️ [3/5] Consultando PostgreSQL (mantenimientos)...")
            postgres_service = get_postgres_service()
            seriales = df_raw['Serial_dispositivo'].dropna().unique()
            df_mttos = postgres_service.get_mantenimientos_dataframe(list(seriales))
            
            maintenance_dict = {}
            client_dict = {}
            brand_dict = {}
            model_dict = {}
            
            if df_mttos is not None and not df_mttos.empty:
                maintenance_dict, client_dict, brand_dict, model_dict = postgres_service.get_maintenance_metadata(df_mttos)
                logger.info(f"   ✅ PostgreSQL: {len(maintenance_dict)} registros de mantenimiento")
            else:
                logger.warning("   ⚠️ PostgreSQL: No se obtuvieron datos de mantenimiento")
            
            # 4. Detectar fallas y construir intervalos
            logger.info("🔍 [4/5] Detectando fallas y construyendo intervalos...")
            ml_service = get_ml_service()
            df_processed['is_failure_bool'] = ml_service.detect_failures(
                df_processed, 'Descripcion', 'Severidad', self.settings.SEVERITY_THRESHOLD
            )
            
            intervals = ml_service.build_intervals(
                df_processed, 'Dispositivo', 'Fecha_alarma', 'is_failure_bool',
                self.settings.SEVERITY_THRESHOLD, maintenance_dict
            )
            logger.info(f"   ✅ Intervalos: {len(intervals)} construidos")
            
            # 5. Entrenar modelo ML
            logger.info("🤖 [5/5] Entrenando modelo ML...")
            try:
                model, features = ml_service.train_model(intervals)
                logger.info(f"   ✅ Modelo entrenado con {len(features)} características")
            except ValueError as e:
                logger.error(f"   ❌ Error entrenando modelo: {str(e)}")
                model, features = None, None
            
            # Guardar en caché interno
            self._cached_data = {
                'df_raw': df_raw.copy(),
                'df_processed': df_processed.copy(),
                'intervals': intervals.copy(),
                'model': model,
                'features': features,
                'maintenance_dict': maintenance_dict,
                'brand_dict': brand_dict,
                'model_dict': model_dict,
                'client_dict': client_dict,
                'last_update': datetime.now()
            }
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info("=" * 80)
            logger.info(f"✅ ACTUALIZACIÓN COMPLETADA en {elapsed:.2f}s - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"❌ ERROR EN ACTUALIZACIÓN: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            self._is_updating = False
    
    def get_cached_data(self, cliente: Optional[str] = None) -> Dict:
        """
        Obtiene los datos pre-cargados (filtrados por cliente si aplica)
        
        Args:
            cliente: Nombre del cliente para filtrar (None = todos)
        
        Returns:
            Dict con todos los datos necesarios
        """
        if self._cached_data['last_update'] is None:
            logger.warning("⚠️ No hay datos pre-cargados, ejecutando actualización...")
            self.refresh_all_data()
        
        # Copiar datos base
        data = {
            'intervals': self._cached_data['intervals'].copy() if self._cached_data['intervals'] is not None else pd.DataFrame(),
            'model': self._cached_data['model'],
            'features': self._cached_data['features'],
            'maintenance_dict': self._cached_data['maintenance_dict'],
            'brand_dict': self._cached_data['brand_dict'],
            'model_dict': self._cached_data['model_dict'],
            'client_dict': self._cached_data['client_dict'],
            'last_update': self._cached_data['last_update']
        }
        
        # Filtrar por cliente si es necesario
        if cliente and cliente != "Todos los clientes":
            bigquery_service = get_bigquery_service()
            
            df_raw_filtered = bigquery_service.filter_by_cliente(
                self._cached_data['df_raw'].copy(), 
                cliente
            )
            df_processed_filtered = bigquery_service.filter_by_cliente(
                self._cached_data['df_processed'].copy(),
                cliente
            )
            
            # Filtrar intervalos por dispositivos del cliente
            if not df_processed_filtered.empty:
                dispositivos_cliente = df_processed_filtered['Dispositivo'].unique()
                intervals_filtered = self._cached_data['intervals'][
                    self._cached_data['intervals']['unit'].isin(dispositivos_cliente)
                ].copy()
                data['intervals'] = intervals_filtered
            else:
                data['intervals'] = pd.DataFrame()
            
            data['df_raw'] = df_raw_filtered
            data['df_processed'] = df_processed_filtered
        else:
            data['df_raw'] = self._cached_data['df_raw'].copy()
            data['df_processed'] = self._cached_data['df_processed'].copy()
        
        return data
    
    def get_status(self) -> Dict:
        """Obtiene el estado de la pre-carga"""
        if self._cached_data['last_update']:
            minutes_since_update = (datetime.now() - self._cached_data['last_update']).total_seconds() / 60
        else:
            minutes_since_update = None
        
        return {
            'has_data': self._cached_data['last_update'] is not None,
            'last_update': self._cached_data['last_update'].isoformat() if self._cached_data['last_update'] else None,
            'minutes_since_update': round(minutes_since_update, 1) if minutes_since_update else None,
            'is_updating': self._is_updating,
            'total_alarms': len(self._cached_data['df_raw']) if self._cached_data['df_raw'] is not None else 0,
            'total_intervals': len(self._cached_data['intervals']) if self._cached_data['intervals'] is not None else 0,
            'model_trained': self._cached_data['model'] is not None
        }
    
    def force_refresh(self):
        """Fuerza una actualización inmediata"""
        logger.info("🔄 Actualización forzada solicitada...")
        self.refresh_all_data()


# Singleton
_preload_service = None


def get_preload_service() -> DataPreloadService:
    """Obtiene instancia singleton del servicio de pre-carga"""
    global _preload_service
    if _preload_service is None:
        _preload_service = DataPreloadService()
    return _preload_service