import logging
from datetime import datetime
from typing import List, Dict
import pandas as pd
from app.services.crm_client import get_crm_client
from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class SyncService:
    """Servicio para sincronizar datos del CRM a PostgreSQL (tabla existente)"""
    
    def __init__(self):
        self.settings = get_settings()
        self.crm_client = get_crm_client()
    
    def sync_mantenimientos(self, seriales: List[str]) -> Dict:
        """
        Sincroniza mantenimientos desde CRM a PostgreSQL
        Usa INSERT ... ON CONFLICT UPDATE para evitar duplicados
        
        Args:
            seriales: Lista de seriales a sincronizar
        
        Returns:
            Dict con estadísticas de la sincronización
        """
        logger.info("=" * 80)
        logger.info(f"🔄 INICIANDO SINCRONIZACIÓN - {datetime.now().strftime('%Y-%m-%d %H%M:%S')}")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        stats = {
            'seriales_consultados': len(seriales),
            'registros_obtenidos': 0,
            'registros_insertados': 0,
            'registros_actualizados': 0,
            'errores': 0,
            'duracion_segundos': 0
        }
        
        try:
            # Obtener datos del CRM (método correcto get_equipos_info)
            logger.info(f"🔍 Consultando CRM para {len(seriales)} seriales...")
            equipos_response = self.crm_client.get_equipos_info(seriales)
            
            # Debug: ver qué nos devuelve el CRM
            logger.debug(f"Respuesta del CRM (tipo): {type(equipos_response)}")
            logger.debug(f"Respuesta del CRM (keys): {equipos_response.keys() if isinstance(equipos_response, dict) else 'No es dict'}")
            
            # Verificar respuesta
            if not equipos_response:
                logger.warning("⚠️ Respuesta del CRM es None o vacía")
                return stats
            
            # El CRM devuelve directamente un dict con 'data'
            if isinstance(equipos_response, dict) and 'data' in equipos_response:
                equipos = equipos_response['data']
            else:
                logger.warning(f"⚠️ Formato de respuesta inesperado del CRM: {type(equipos_response)}")
                logger.warning(f"Contenido: {str(equipos_response)[:200]}")
                return stats
            
            if not equipos:
                logger.warning("⚠️ Lista de equipos vacía del CRM")
                return stats
            
            stats['registros_obtenidos'] = len(equipos)
            logger.info(f"✅ Obtenidos {len(equipos)} equipos del CRM")
            
            # Conectar directamente con psycopg2
            import psycopg2
            conn = psycopg2.connect(
                host=self.settings.POSTGRES_HOST,
                port=self.settings.POSTGRES_PORT,
                database=self.settings.POSTGRES_DB,
                user=self.settings.POSTGRES_USER,
                password=self.settings.POSTGRES_PASSWORD
            )
            conn.autocommit = False
            
            try:
                cursor = conn.cursor()
                
                for equipo in equipos:
                    try:
                        # Extraer todos los campos del CRM
                        serial = str(equipo.get('serial', '')).strip()
                        if not serial:
                            logger.warning("⚠️ Serial vacío, omitiendo registro")
                            continue
                        
                        # Campos principales
                        device_id = str(equipo.get('id', ''))
                        device_name = str(equipo.get('equipo', serial))
                        device_brand = str(equipo.get('marca', ''))
                        device_model = str(equipo.get('modelo', ''))
                        device_type = str(equipo.get('tipo', 'CRAC'))
                        customer_name = str(equipo.get('cliente', ''))
                        nit = str(equipo.get('nit', ''))
                        
                        # Parsear fecha de mantenimiento
                        hora_salida_str = equipo.get('hora_salida')
                        datetime_maintenance_end = None
                        if hora_salida_str:
                            try:
                                datetime_maintenance_end = pd.to_datetime(hora_salida_str)
                            except Exception as e:
                                logger.warning(f"⚠️ Fecha inválida para serial {serial}: {e}")
                                continue
                        
                        # Campos adicionales
                        maintenance_type = str(equipo.get('tipo_mantenimiento', 'Preventivo'))
                        report_id = str(equipo.get('reporte_id', ''))
                        maintenance_remarks = str(equipo.get('observaciones', ''))
                        report_status = str(equipo.get('estado', 'Completado'))
                        
                        # Generar ods_name único (combinación de serial y fecha)
                        if datetime_maintenance_end:
                            ods_name = f"{serial}_{datetime_maintenance_end.strftime('%Y%m%d_%H%M%S')}"
                        else:
                            ods_name = f"{serial}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        
                        # INSERT con ON CONFLICT para actualizar si ya existe
                        query = """
                        INSERT INTO monitoreo_equipos.mantenimientos 
                        (
                            ods_name,
                            maintenance_type,
                            device_id,
                            device_name,
                            device_brand,
                            device_model,
                            device_type,
                            datetime_ods_create,
                            serial,
                            report_id,
                            datetime_maintenance_end,
                            maintenance_remarks,
                            report_status,
                            nit,
                            customer_name
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (ods_name) 
                        DO UPDATE SET
                            maintenance_type = EXCLUDED.maintenance_type,
                            device_id = EXCLUDED.device_id,
                            device_name = EXCLUDED.device_name,
                            device_brand = EXCLUDED.device_brand,
                            device_model = EXCLUDED.device_model,
                            device_type = EXCLUDED.device_type,
                            report_id = EXCLUDED.report_id,
                            datetime_maintenance_end = EXCLUDED.datetime_maintenance_end,
                            maintenance_remarks = EXCLUDED.maintenance_remarks,
                            report_status = EXCLUDED.report_status,
                            nit = EXCLUDED.nit,
                            customer_name = EXCLUDED.customer_name
                        RETURNING (xmax = 0) AS inserted;
                        """
                        
                        cursor.execute(query, (
                            ods_name,
                            maintenance_type,
                            device_id,
                            device_name,
                            device_brand,
                            device_model,
                            device_type,
                            datetime.now(),
                            serial,
                            report_id,
                            datetime_maintenance_end,
                            maintenance_remarks,
                            report_status,
                            nit,
                            customer_name
                        ))
                        
                        # Verificar si fue inserción o actualización
                        result = cursor.fetchone()
                        if result and result[0]:
                            stats['registros_insertados'] += 1
                            logger.debug(f"➕ Insertado: {serial}")
                        else:
                            stats['registros_actualizados'] += 1
                            logger.debug(f"🔄 Actualizado: {serial}")
                    
                    except Exception as e:
                        logger.error(f"❌ Error procesando equipo {equipo.get('serial', 'UNKNOWN')}: {e}")
                        stats['errores'] += 1
                        continue
                
                # Commit de todos los cambios
                conn.commit()
                logger.info("✅ Cambios guardados en PostgreSQL")
                
            except Exception as e:
                conn.rollback()
                logger.error(f"❌ Error en transacción: {e}")
                import traceback
                logger.error(traceback.format_exc())
                stats['errores'] += 1
            finally:
                cursor.close()
                conn.close()
        
        except Exception as e:
            logger.error(f"❌ Error general en sincronización: {e}")
            import traceback
            logger.error(traceback.format_exc())
            stats['errores'] += 1
        
        # Calcular duración
        elapsed = (datetime.now() - start_time).total_seconds()
        stats['duracion_segundos'] = round(elapsed, 2)
        
        logger.info("=" * 80)
        logger.info(f"✅ SINCRONIZACIÓN COMPLETADA en {elapsed:.2f}s")
        logger.info(f"   📊 Registros obtenidos: {stats['registros_obtenidos']}")
        logger.info(f"   ➕ Nuevos insertados: {stats['registros_insertados']}")
        logger.info(f"   🔄 Actualizados: {stats['registros_actualizados']}")
        logger.info(f"   ❌ Errores: {stats['errores']}")
        logger.info("=" * 80)
        
        return stats
    
    def get_mantenimientos_by_seriales(self, seriales: List[str]) -> List[Dict]:
        """
        Obtiene mantenimientos desde PostgreSQL por seriales
        
        Args:
            seriales: Lista de seriales
        
        Returns:
            Lista de diccionarios con mantenimientos
        """
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            conn = psycopg2.connect(
                host=self.settings.POSTGRES_HOST,
                port=self.settings.POSTGRES_PORT,
                database=self.settings.POSTGRES_DB,
                user=self.settings.POSTGRES_USER,
                password=self.settings.POSTGRES_PASSWORD
            )
            
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            placeholders = ','.join(['%s'] * len(seriales))
            query = f"""
                SELECT * FROM monitoreo_equipos.mantenimientos
                WHERE serial IN ({placeholders})
                ORDER BY datetime_maintenance_end DESC
            """
            
            cursor.execute(query, tuple(seriales))
            results = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo mantenimientos: {e}")
            return []


# Singleton
_sync_service = None


def get_sync_service() -> SyncService:
    """Obtiene instancia singleton del servicio de sincronización"""
    global _sync_service
    if _sync_service is None:
        _sync_service = SyncService()
    return _sync_service