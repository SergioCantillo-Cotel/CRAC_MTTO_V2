import logging
from datetime import datetime
from typing import List, Dict
import pandas as pd
from app.services.crm_service import get_crm_service
from app.services.mantenimientos_api_client import get_mantenimientos_api_client
from app.services.analytics_service import EQUIPO_SERIAL_MAPPING

logger = logging.getLogger(__name__)


class SyncStartupService:
    """
    Servicio para sincronizar datos del CRM al API de Mantenimientos al inicio
    
    VERSIÓN OPTIMIZADA:
    - Verificación de existencia en batch (1 petición vs 550)
    - Inserción en batch (1 petición vs N individuales)
    - Verificación por serial + id_reporte + observaciones_reporte
    - Tiempo estimado: 6-10 segundos vs 300 segundos (50x más rápido)
    """
    
    def __init__(self):
        self.crm_service = get_crm_service()
        self.api_client = get_mantenimientos_api_client()
    
    def sync_on_startup(self) -> Dict:
        """
        Sincroniza datos del CRM al API de Mantenimientos al iniciar el backend
        
        OPTIMIZACIÓN:
        - Obtiene todos los registros existentes en 1 sola petición
        - Verifica duplicados en memoria O(1)
        - Inserta registros nuevos en batch
        
        Returns:
            Dict con estadísticas de sincronización
        """
        logger.info("=" * 80)
        logger.info(f"🔄 SINCRONIZACIÓN INICIAL (OPTIMIZADA) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        stats = {
            'seriales_consultados': 0,
            'registros_obtenidos': 0,
            'registros_nuevos': 0,
            'registros_existentes': 0,
            'registros_omitidos': 0,
            'registros_enviados': 0,
            'errores': 0,
            'duracion_segundos': 0,
            'tiempo_verificacion': 0,
            'tiempo_preparacion': 0,
            'tiempo_insercion': 0
        }
        
        try:
            # ========== FASE 1: OBTENER DATOS DEL CRM ==========
            fase1_start = datetime.now()
            
            # 1. Obtener lista de seriales conocidos
            seriales = list(EQUIPO_SERIAL_MAPPING.values())
            stats['seriales_consultados'] = len(seriales)
            
            logger.info(f"📋 [FASE 1/4] Consultando CRM para {len(seriales)} seriales...")
            
            # 2. Consultar CRM
            df_mttos = self.crm_service.get_equipos_dataframe(seriales)
            
            if df_mttos is None or df_mttos.empty:
                logger.warning("⚠️ CRM: No se obtuvieron datos")
                return stats
            
            stats['registros_obtenidos'] = len(df_mttos)
            logger.info(f"✅ CRM: {len(df_mttos)} registros obtenidos en {(datetime.now() - fase1_start).total_seconds():.2f}s")
            
            # ========== FASE 2: VERIFICACIÓN EN BATCH ==========
            fase2_start = datetime.now()
            
            logger.info(f"🚀 [FASE 2/4] Obteniendo registros existentes en batch...")
            
            # OPTIMIZACIÓN CLAVE: Obtener TODOS los registros existentes de una vez
            existing_keys = self.api_client.get_existing_keys_batch(seriales)
            
            stats['tiempo_verificacion'] = (datetime.now() - fase2_start).total_seconds()
            logger.info(f"✅ Verificación batch completada en {stats['tiempo_verificacion']:.2f}s")
            logger.info(f"   Claves existentes encontradas: {len(existing_keys)}")
            
            # ========== FASE 3: PREPARAR DATOS ==========
            fase3_start = datetime.now()
            
            logger.info(f"🔧 [FASE 3/4] Preparando registros para inserción...")
            
            records_to_insert = []
            
            for idx, row in df_mttos.iterrows():
                try:
                    # Preparar registro
                    record = self._prepare_record(row)
                    
                    if not record:
                        stats['registros_omitidos'] += 1
                        continue
                    
                    # Verificar si existe usando el conjunto en memoria (O(1))
                    serial = record['serial']
                    id_reporte = record.get('report_id')
                    maintenance_remarks = record.get('maintenance_remarks')
                    
                    # OPTIMIZACIÓN: Verificación en memoria en lugar de petición HTTP
                    exists = self.api_client.check_if_exists_in_set(
                        serial, id_reporte, maintenance_remarks, existing_keys
                    )
                    
                    if exists:
                        stats['registros_existentes'] += 1
                        key_str = f"{serial}"
                        if id_reporte:
                            key_str += f" (ID: {id_reporte})"
                        if maintenance_remarks:
                            key_str += f" (Obs: {maintenance_remarks[:30]}...)"
                        logger.debug(f"⏭️  {key_str} ya existe - omitiendo")
                        continue
                    
                    # Agregar a lista de inserción
                    records_to_insert.append(record)
                
                except Exception as e:
                    logger.error(f"❌ Error preparando registro: {str(e)}")
                    stats['errores'] += 1
                    continue
            
            stats['tiempo_preparacion'] = (datetime.now() - fase3_start).total_seconds()
            logger.info(f"✅ Preparación completada en {stats['tiempo_preparacion']:.2f}s")
            logger.info(f"   Registros a insertar: {len(records_to_insert)}")
            
            # ========== FASE 4: INSERCIÓN EN BATCH ==========
            if records_to_insert:
                fase4_start = datetime.now()
                
                logger.info(f"📤 [FASE 4/4] Insertando {len(records_to_insert)} registros en batch...")
                
                # OPTIMIZACIÓN CLAVE: Insertar todos de una vez
                exitosos, fallidos = self.api_client.upsert_mantenimiento_batch(records_to_insert)
                
                stats['registros_enviados'] = exitosos
                stats['registros_nuevos'] = exitosos
                stats['errores'] += fallidos
                
                stats['tiempo_insercion'] = (datetime.now() - fase4_start).total_seconds()
                logger.info(f"✅ Inserción batch completada en {stats['tiempo_insercion']:.2f}s")
            else:
                logger.info(f"⏭️  [FASE 4/4] No hay registros nuevos para insertar")
            
            # ========== RESUMEN FINAL ==========
            elapsed = (datetime.now() - start_time).total_seconds()
            stats['duracion_segundos'] = round(elapsed, 2)
            
            logger.info("=" * 80)
            logger.info(f"✅ SINCRONIZACIÓN COMPLETADA en {elapsed:.2f}s")
            logger.info(f"   📊 Registros obtenidos del CRM: {stats['registros_obtenidos']}")
            logger.info(f"   ✅ Registros nuevos insertados: {stats['registros_nuevos']}")
            logger.info(f"   ⏭️  Registros ya existentes: {stats['registros_existentes']}")
            logger.info(f"   ⏭️  Registros omitidos (sin datos): {stats['registros_omitidos']}")
            logger.info(f"   ❌ Errores: {stats['errores']}")
            logger.info("")
            logger.info(f"   ⏱️  TIEMPOS DE EJECUCIÓN:")
            logger.info(f"      - Verificación batch: {stats['tiempo_verificacion']:.2f}s")
            logger.info(f"      - Preparación datos: {stats['tiempo_preparacion']:.2f}s")
            logger.info(f"      - Inserción batch: {stats['tiempo_insercion']:.2f}s")
            logger.info(f"      - Total: {elapsed:.2f}s")
            
            # Calcular mejora vs método antiguo
            if stats['registros_obtenidos'] > 0:
                tiempo_antiguo_estimado = stats['registros_obtenidos'] * 0.55  # 0.55s por registro
                mejora_porcentaje = ((tiempo_antiguo_estimado - elapsed) / tiempo_antiguo_estimado) * 100
                logger.info(f"   🚀 OPTIMIZACIÓN: ~{mejora_porcentaje:.0f}% más rápido que método anterior")
                logger.info(f"      (Estimado antiguo: {tiempo_antiguo_estimado:.0f}s vs Actual: {elapsed:.0f}s)")
            
            logger.info("=" * 80)
            
            return stats
            
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            stats['duracion_segundos'] = round(elapsed, 2)
            
            logger.error(f"❌ ERROR EN SINCRONIZACIÓN: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            stats['errores'] += 1
            return stats
    
    def _prepare_record(self, row: pd.Series) -> Dict:
        """
        Prepara un registro del CRM para enviar al API
        
        CAMBIO: Ahora incluye report_id y maintenance_remarks para verificación de duplicados
        
        Args:
            row: Fila del DataFrame del CRM
        
        Returns:
            Diccionario con datos preparados o None si hay error
        """
        try:
            serial = str(row.get('serial', '')).strip()
            
            if not serial or serial == 'nan':
                return None
            
            # ========== CAMPOS REQUERIDOS ==========
            
            # 1. Fecha de mantenimiento - REQUERIDO
            hora_salida = row.get('hora_salida')
            if pd.isna(hora_salida):
                logger.debug(f"Serial {serial} sin fecha de mantenimiento - omitiendo")
                return None
            
            try:
                datetime_maintenance_end = pd.to_datetime(hora_salida).isoformat()
            except:
                logger.warning(f"Fecha inválida para serial {serial} - omitiendo")
                return None
            
            # 2. Fecha de creación ODS - REQUERIDO
            fecha_creacion = row.get('fecha_creacion')
            if pd.isna(fecha_creacion):
                logger.debug(f"Serial {serial} sin fecha de creacion ODS - omitiendo")
                return None
            
            try:
                datetime_ods_create = pd.to_datetime(fecha_creacion).isoformat()
            except:
                logger.warning(f"Fecha inválida para serial {serial} - omitiendo")
                return None
            
            # 3. Generar UUID único para mtto_PK
            import uuid
            mtto_pk = str(uuid.uuid4())
            
            # ========== CONSTRUIR REGISTRO BASE ==========
            
            record = {
                'mtto_PK': mtto_pk,
                'serial': serial,
                'datetime_maintenance_end': datetime_maintenance_end,
                'datetime_ods_create': datetime_ods_create,

                # Campos para verificación de duplicados (siempre presentes)
                'report_id': None,
                'maintenance_remarks': None,
                
                # Campos adicionales (siempre presentes, pueden ser None)
                'customer_name': None,
                'device_brand': None,
                'device_model': None,
                'device_name': None,
                'maintenance_type': None,
                'report_status': None,
                'device_id': None,
                'device_type': None,
                'ods_name': None,
                'nit': None
            }
            
            # ========== CAMPOS PARA VERIFICACIÓN DE DUPLICADOS ==========
            
            # ID del reporte (NUEVO - para verificación)
            id_reporte = row.get('reporte')
            if pd.notna(id_reporte) and str(id_reporte).strip() and str(id_reporte).strip() != 'nan':
                record['report_id'] = str(id_reporte).strip()
            
            # Observaciones del reporte (NUEVO - para verificación)
            observaciones_reporte = row.get('observaciones_reporte')
            if pd.notna(observaciones_reporte) and str(observaciones_reporte).strip() and str(observaciones_reporte).strip() != 'nan':
                record['maintenance_remarks'] = str(observaciones_reporte).strip()
            
            # Cliente
            cliente = row.get('cliente')
            if pd.notna(cliente) and str(cliente).strip() != 'nan':
                record['customer_name'] = str(cliente)
            
            # Marca
            marca = row.get('marca')
            if pd.notna(marca) and str(marca).strip() != 'nan':
                record['device_brand'] = str(marca)
            
            # Modelo
            modelo = row.get('modelo')
            if pd.notna(modelo) and str(modelo).strip() != 'nan':
                record['device_model'] = str(modelo)
            
            # Nombre del equipo
            device_name = row.get('nombre_equipo')
            if pd.notna(device_name) and str(device_name).strip() != 'nan':
                record['device_name'] = str(device_name)
            
            # Tipo de mantenimiento
            tipo_mantenimiento = row.get('tipo_mantenimiento')
            if pd.notna(tipo_mantenimiento) and str(tipo_mantenimiento).strip() != 'nan':
                record['maintenance_type'] = str(tipo_mantenimiento)
            
            # Estado del reporte
            estado_reporte = row.get('estado_reporte')
            if pd.notna(estado_reporte) and str(estado_reporte).strip() != 'nan':
                record['report_status'] = str(estado_reporte)
            
            # ID del equipo
            device_id = row.get('id_equipos')
            if pd.notna(device_id) and str(device_id).strip() != 'nan':
                record['device_id'] = str(device_id)
            
            # Tipo de dispositivo
            tipo = row.get('linea')
            if pd.notna(tipo) and str(tipo).strip() != 'nan':
                record['device_type'] = str(tipo)
            
            # Nombre ODS
            ods_name = row.get('nombre_ods')
            if pd.notna(ods_name) and str(ods_name).strip() != 'nan':
                record['ods_name'] = str(ods_name)
            
            # NIT
            nit = row.get('nit')
            if pd.notna(nit) and str(nit).strip() != 'nan':
                record['nit'] = str(nit)
            
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