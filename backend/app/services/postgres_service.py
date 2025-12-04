import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Configuración de PostgreSQL
POSTGRES_CONFIG = {
    'host': '127.0.0.1',
    'port': 5432,
    'database': 'eficiencia_energetica',
    'user': 'api_crud_monitoreo_equipos',
    'password': ''  # Se carga desde settings o .pgpass
}


class PostgresService:
    """Servicio para consultar mantenimientos desde PostgreSQL"""
    
    def __init__(self):
        self._connection = None
        # Intentar usar settings si están disponibles
        try:
            from app.config.settings import get_settings
            self.settings = get_settings()
            self.config = {
                'host': getattr(self.settings, 'POSTGRES_HOST', POSTGRES_CONFIG['host']),
                'port': getattr(self.settings, 'POSTGRES_PORT', POSTGRES_CONFIG['port']),
                'database': getattr(self.settings, 'POSTGRES_DB', POSTGRES_CONFIG['database']),
                'user': getattr(self.settings, 'POSTGRES_USER', POSTGRES_CONFIG['user']),
                'password': getattr(self.settings, 'POSTGRES_PASSWORD', POSTGRES_CONFIG['password'])
            }
        except:
            self.config = POSTGRES_CONFIG
    
    def _get_connection(self):
        """Obtiene conexión a PostgreSQL"""
        if self._connection is None or self._connection.closed:
            try:
                self._connection = psycopg2.connect(**self.config)
                logger.info("✅ Conexión a PostgreSQL establecida")
            except Exception as e:
                logger.error(f"❌ Error conectando a PostgreSQL: {e}")
                raise
        return self._connection
    
    def get_mantenimientos_dataframe(self, seriales: List[str]) -> Optional[pd.DataFrame]:
        """
        Obtiene mantenimientos como DataFrame desde la tabla real
        
        Estructura de la tabla:
        - serial (text)
        - datetime_maintenance_end (timestamp)
        - customer_name (text)
        - device_brand (text)
        - device_model (text)
        
        Args:
            seriales: Lista de números de serie
        
        Returns:
            DataFrame con mantenimientos o None si hay error
        """
        if not seriales:
            return pd.DataFrame()
        
        try:
            conn = self._get_connection()
            
            # Preparar query con placeholders
            placeholders = ','.join(['%s'] * len(seriales))
            
            # Query adaptada a la estructura real de la tabla
            query = f"""
                SELECT 
                    serial,
                    datetime_maintenance_end as hora_salida,
                    customer_name as cliente,
                    device_brand as marca,
                    device_model as modelo
                FROM monitoreo_equipos.mantenimientos
                WHERE serial IN ({placeholders})
                    AND datetime_maintenance_end IS NOT NULL
                ORDER BY datetime_maintenance_end DESC
            """
            
            # Ejecutar query
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, tuple(seriales))
                results = cursor.fetchall()
            
            if not results:
                logger.warning(f"⚠️ No se encontraron mantenimientos para los seriales consultados")
                return pd.DataFrame()
            
            # Convertir a DataFrame
            df = pd.DataFrame(results)
            
            # Renombrar columnas para compatibilidad con código existente
            # (ya están renombradas en el SELECT)
            
            logger.info(f"✅ Obtenidos {len(df)} registros de mantenimiento desde PostgreSQL")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Error consultando mantenimientos: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def get_maintenance_metadata(self, df_mttos: pd.DataFrame) -> Tuple[Dict, Dict, Dict, Dict]:
        """
        Obtiene metadatos de mantenimiento de forma optimizada
        
        Args:
            df_mttos: DataFrame con datos de mantenimiento
        
        Returns:
            Tuple (last_maintenance_dict, client_dict, brand_dict, model_dict)
        """
        if df_mttos is None or df_mttos.empty:
            return {}, {}, {}, {}
        
        try:
            # Asegurar que 'serial' es string y 'hora_salida' es datetime
            df_mttos['serial'] = df_mttos['serial'].astype(str).str.strip()
            df_mttos['hora_salida'] = pd.to_datetime(df_mttos['hora_salida'], errors='coerce')
            
            # Eliminar filas sin fecha válida
            df_mttos = df_mttos.dropna(subset=['hora_salida'])
            
            if df_mttos.empty:
                return {}, {}, {}, {}
            
            # Ordenar y obtener últimos registros por serial
            last_records = df_mttos.sort_values('hora_salida', ascending=False)
            last_records = last_records.drop_duplicates('serial', keep='first')
            
            # Crear diccionarios
            last_maintenance_dict = dict(zip(
                last_records['serial'],
                last_records['hora_salida']
            ))
            
            client_dict = {}
            if 'cliente' in last_records.columns:
                # Limpiar valores None y convertir a string
                client_dict = {
                    serial: str(cliente) if pd.notna(cliente) else 'No especificado'
                    for serial, cliente in zip(last_records['serial'], last_records['cliente'])
                }
            
            brand_dict = {}
            if 'marca' in last_records.columns:
                brand_dict = {
                    serial: str(marca) if pd.notna(marca) else 'N/A'
                    for serial, marca in zip(last_records['serial'], last_records['marca'])
                }
            
            model_dict = {}
            if 'modelo' in last_records.columns:
                model_dict = {
                    serial: str(modelo) if pd.notna(modelo) else 'N/A'
                    for serial, modelo in zip(last_records['serial'], last_records['modelo'])
                }
            
            logger.info(f"✅ Metadatos procesados: {len(last_maintenance_dict)} seriales únicos")
            
            return last_maintenance_dict, client_dict, brand_dict, model_dict
            
        except Exception as e:
            logger.error(f"❌ Error procesando metadatos mantenimiento: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}, {}, {}, {}
    
    def test_connection(self) -> bool:
        """
        Prueba la conexión a PostgreSQL
        
        Returns:
            True si la conexión es exitosa, False en caso contrario
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            logger.info("✅ Test de conexión PostgreSQL exitoso")
            return True
        except Exception as e:
            logger.error(f"❌ Test de conexión PostgreSQL falló: {e}")
            return False
    
    def get_table_info(self) -> Dict:
        """
        Obtiene información de la tabla mantenimientos
        
        Returns:
            Dict con información de la tabla
        """
        try:
            conn = self._get_connection()
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Verificar si la tabla existe
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'monitoreo_equipos' 
                        AND table_name = 'mantenimientos'
                    );
                """)
                exists = cursor.fetchone()['exists']
                
                if not exists:
                    return {'exists': False}
                
                # Contar registros
                cursor.execute("SELECT COUNT(*) as count FROM monitoreo_equipos.mantenimientos;")
                count = cursor.fetchone()['count']
                
                # Contar seriales únicos
                cursor.execute("SELECT COUNT(DISTINCT serial) as unique_serials FROM monitoreo_equipos.mantenimientos WHERE serial IS NOT NULL;")
                unique_serials = cursor.fetchone()['unique_serials']
                
                # Obtener rango de fechas
                cursor.execute("""
                    SELECT 
                        MIN(datetime_maintenance_end) as first_date,
                        MAX(datetime_maintenance_end) as last_date
                    FROM monitoreo_equipos.mantenimientos
                    WHERE datetime_maintenance_end IS NOT NULL;
                """)
                date_range = cursor.fetchone()
                
                return {
                    'exists': True,
                    'total_records': count,
                    'unique_serials': unique_serials,
                    'first_date': date_range['first_date'].isoformat() if date_range['first_date'] else None,
                    'last_date': date_range['last_date'].isoformat() if date_range['last_date'] else None
                }
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo info de tabla: {e}")
            return {'exists': False, 'error': str(e)}
    
    def close(self):
        """Cierra la conexión"""
        if self._connection and not self._connection.closed:
            self._connection.close()
            logger.info("✅ Conexión a PostgreSQL cerrada")


# Singleton
_postgres_service = None


def get_postgres_service() -> PostgresService:
    """Obtiene instancia singleton del servicio PostgreSQL"""
    global _postgres_service
    if _postgres_service is None:
        _postgres_service = PostgresService()
    return _postgres_service