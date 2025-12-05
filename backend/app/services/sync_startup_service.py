import logging
from datetime import datetime
from typing import List, Dict
import pandas as pd
from app.services.crm_service import get_crm_service
from app.services.mantenimientos_api_client import get_mantenimientos_api_client
from app.services.analytics_service import EQUIPO_SERIAL_MAPPING

logger = logging.getLogger(__name__)


class SyncStartupService:
    """Servicio para sincronizar datos del CRM al API de Mantenimientos al inicio"""
    
    def __init__(self):
        self.crm_service = get_crm_service()
        self.api_client = get_mantenimientos_api_client()
    
    def sync_on_startup(self) -> Dict:
        """
        Sincroniza datos del CRM al API de Mantenimientos al iniciar el backend
        
        Returns:
            Dict con estadísticas de sincronización
        """
        logger.info("=" * 80)
        logger.info(f"🔄 SINCRONIZACIÓN INICIAL - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        stats = {
            'seriales_consultados': 0,
            'registros_obtenidos': 0,
            'registros_nuevos': 0,
            'registros_existentes': 0,
            'registros_omitidos': 0,
            'errores': 0,
            'duracion_segundos': 0
        }
        
        try:
            # 1. Obtener lista de seriales conocidos
            seriales = list(EQUIPO_SERIAL_MAPPING.values())
            stats['seriales_consultados'] = len(seriales)
            
            logger.info(f"📋 Consultando CRM para {len(seriales)} seriales...")
            
            # 2. Consultar CRM
            df_mttos = self.crm_service.get_equipos_dataframe(seriales)
            
            if df_mttos is None or df_mttos.empty:
                logger.warning("⚠️ CRM: No se obtuvieron datos")
                return stats
            
            stats['registros_obtenidos'] = len(df_mttos)
            logger.info(f"✅ CRM: {len(df_mttos)} registros obtenidos")
            
            # Debug: mostrar columnas disponibles
            logger.debug(f"Columnas del CRM: {df_mttos.columns.tolist()}")
            
            # 3. Preparar datos para enviar al API
            logger.info("📤 Enviando datos al API de Mantenimientos...")
            
            for idx, row in df_mttos.iterrows():
                try:
                    # Preparar registro
                    record = self._prepare_record(row)
                    
                    if not record:
                        stats['registros_omitidos'] += 1
                        continue
                    
                    # Verificar si existe antes de insertar
                    serial = record['serial']
                    fecha = record['datetime_maintenance_end']
                    
                    exists = self.api_client.check_if_exists(serial, fecha)
                    
                    if exists:
                        stats['registros_existentes'] += 1
                        logger.debug(f"⏭️  Serial {serial} ya existe - omitiendo")
                        continue

                    # Enviar al API
                    success = self.api_client.upsert_mantenimiento(record)
                    
                    if success:
                        stats['registros_enviados'] += 1
                        logger.debug(f"✅ Serial {record['serial']} insertado")
                    else:
                        stats['errores'] += 1
                        logger.warning(f"⚠️ Error insertando serial: {record.get('serial', 'N/A')}")
                
                except Exception as e:
                    logger.error(f"❌ Error procesando registro: {str(e)}")
                    stats['errores'] += 1
                    continue
            
            # Calcular duración
            elapsed = (datetime.now() - start_time).total_seconds()
            stats['duracion_segundos'] = round(elapsed, 2)
            
            logger.info("=" * 80)
            logger.info(f"✅ SINCRONIZACIÓN COMPLETADA en {elapsed:.2f}s")
            logger.info(f"   📊 Registros obtenidos del CRM: {stats['registros_obtenidos']}")
            logger.info(f"   ✅ Registros enviados al API: {stats['registros_enviados']}")
            logger.info(f"   ⏭️ Registros omitidos (sin fecha): {stats['registros_omitidos']}")
            logger.info(f"   ❌ Errores: {stats['errores']}")
            logger.info("=" * 80)
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ ERROR EN SINCRONIZACIÓN: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            stats['errores'] += 1
            return stats
    
    def _prepare_record(self, row: pd.Series) -> Dict:
        """
        Prepara un registro del CRM para enviar al API
        Solo incluye campos que tengan datos reales del CRM
        
        Args:
            row: Fila del DataFrame del CRM
        
        Returns:
            Diccionario con datos preparados o None si hay error
        """
        try:
            serial = str(row.get('serial', '')).strip()
            
            if not serial or serial == 'nan':
                return None
            
            # Parsear fecha de mantenimiento - REQUERIDO
            hora_salida = row.get('hora_salida')
            fecha_creacion = row.get('fecha_creacion')
            
            if pd.isna(hora_salida):
                logger.debug(f"Serial {serial} sin fecha de mantenimiento - omitiendo")
                return None
            
            try:
                datetime_maintenance_end = pd.to_datetime(hora_salida).isoformat()
            except:
                logger.warning(f"Fecha inválida para serial {serial} - omitiendo")
                return None
            
            if pd.isna(fecha_creacion):
                logger.debug(f"Serial {serial} sin fecha de creacion ODS - omitiendo")
                return None
            
            try:
                datetime_ods_create = pd.to_datetime(fecha_creacion).isoformat()
            except:
                logger.warning(f"Fecha inválida para serial {serial} - omitiendo")
                return None
            
            # Generar UUID único para mtto_PK
            import uuid
            mtto_pk = str(uuid.uuid4())
            
            # Construir registro SOLO con campos que tengan datos
            record = {
                'mtto_PK': mtto_pk,  # REQUERIDO - Primary Key
                'serial': serial,     # REQUERIDO
                'datetime_maintenance_end': datetime_maintenance_end,  # REQUERIDO
                'datetime_ods_create':datetime_ods_create
            }
            
            cliente = row.get('cliente')
            record['customer_name'] = str(cliente)
    
            marca = row.get('marca')
            record['device_brand'] = str(marca)
            
            modelo = row.get('modelo')
            record['device_model'] = str(modelo)
            
            device_name = row.get('nombre_equipo')
            record['device_name'] = str(device_name)
            
            tipo_mantenimiento = row.get('tipo_mantenimiento')
            record['maintenance_type'] = str(tipo_mantenimiento)

            estado_reporte = row.get('estado_reporte')
            record['report_status'] = str(estado_reporte)
            
            device_id = row.get('id_equipos')
            record['device_id'] = str(device_id)
            
            tipo = row.get('linea')
            record['device_type'] = str(tipo)
            
            ods_name = row.get('nombre_ods')
            record['ods_name'] = ods_name

            nit = row.get('nit')
            record['nit'] = nit
            return record
            
        except Exception as e:
            logger.error(f"Error preparando registro: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None


# Singleton
_sync_startup_service = None


def get_sync_startup_service() -> SyncStartupService:
    """Obtiene instancia singleton del servicio de sincronización"""
    global _sync_startup_service
    if _sync_startup_service is None:
        _sync_startup_service = SyncStartupService()
    return _sync_startup_service