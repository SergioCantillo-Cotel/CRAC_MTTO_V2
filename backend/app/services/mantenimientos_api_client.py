import requests
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)


class MantenimientosAPIClient:
    """Cliente para consumir el API REST de Mantenimientos en GCP"""
    
    def __init__(self):
        # Importar settings
        from app.config.settings import get_settings
        settings = get_settings()
        
        # Configuración del API desde settings
        self.base_url = settings.MANTENIMIENTOS_API_URL
        self.bearer_token = settings.MANTENIMIENTOS_API_TOKEN
        
        self.headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Profile": "monitoreo_equipos",  # Especificar esquema correcto
            "Content-Profile": "monitoreo_equipos"  # Para POST/PATCH
        }
    
    def _make_request(self, method: str, endpoint: str, headers: Dict = None, **kwargs) -> Optional[Dict]:
        """
        Realiza una petición HTTP al API
        
        Args:
            method: Método HTTP (GET, POST, etc.)
            endpoint: Endpoint del API
            headers: Headers personalizados (opcional)
            **kwargs: Argumentos adicionales para requests
        
        Returns:
            Respuesta JSON o None si hay error
        """
        url = f"{self.base_url}{endpoint}"
        
        # Usar headers personalizados o defaults
        request_headers = headers if headers else self.headers
        kwargs['headers'] = request_headers
        
        try:
            logger.debug(f"Realizando {method} a {url}")
            response = requests.request(method, url, **kwargs, timeout=30)
            response.raise_for_status()
            
            # PostgREST puede retornar 201 sin body en algunos casos
            if response.status_code == 201:
                return {}  # Success sin contenido
            
            return response.json() if response.text else {}
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error HTTP {e.response.status_code}: {e.response.text}")
            return None
        except requests.exceptions.Timeout:
            logger.error(f"Timeout en petición a {url}")
            return None
        except requests.exceptions.ConnectionError:
            logger.error(f"Error de conexión a {url}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado: {str(e)}")
            return None
    
    def get_mantenimientos_by_seriales(self, seriales: List[str]) -> List[Dict]:
        """
        Obtiene mantenimientos filtrados por seriales
        
        Args:
            seriales: Lista de números de serie
        
        Returns:
            Lista de mantenimientos
        """
        if not seriales:
            logger.warning("Lista de seriales vacía")
            return []
        
        try:
            # El API espera un query parameter con los seriales
            # Formato: ?serial=eq.SERIAL1&serial=eq.SERIAL2...
            # O usar IN: ?serial=in.(SERIAL1,SERIAL2,SERIAL3)
            
            seriales_str = ','.join(seriales)
            params = {'serial': f'in.({seriales_str})'}
            
            logger.info(f"🔍 Consultando mantenimientos para {len(seriales)} seriales")
            
            response = self._make_request(
                "GET", 
                "/mantenimientos",
                params=params
            )
            
            if response is None:
                logger.error("❌ Error obteniendo mantenimientos del API")
                return []
            
            # La respuesta puede ser una lista directa o un dict con 'data'
            if isinstance(response, list):
                mantenimientos = response
            elif isinstance(response, dict) and 'data' in response:
                mantenimientos = response['data']
            else:
                logger.warning(f"Formato de respuesta inesperado: {type(response)}")
                return []
            
            logger.info(f"✅ Obtenidos {len(mantenimientos)} mantenimientos del API")
            return mantenimientos
            
        except Exception as e:
            logger.error(f"❌ Error consultando mantenimientos: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def get_mantenimientos_dataframe(self, seriales: List[str]) -> Optional[pd.DataFrame]:
        """
        Obtiene mantenimientos como DataFrame
        
        Args:
            seriales: Lista de números de serie
        
        Returns:
            DataFrame con mantenimientos o None si hay error
        """
        mantenimientos = self.get_mantenimientos_by_seriales(seriales)
        
        if not mantenimientos:
            logger.warning("No se obtuvieron mantenimientos")
            return pd.DataFrame()
        
        try:
            df = pd.DataFrame(mantenimientos)
            
            # Renombrar columnas para compatibilidad con código existente
            # El API devuelve: datetime_maintenance_end, customer_name, device_brand, device_model
            # El código espera: hora_salida, cliente, marca, modelo
            column_mapping = {
                'datetime_maintenance_end': 'hora_salida',
                'customer_name': 'cliente',
                'device_brand': 'marca',
                'device_model': 'modelo'
            }
            
            df = df.rename(columns=column_mapping)
            
            # Asegurar que existe la columna 'serial'
            if 'serial' not in df.columns:
                logger.error("Columna 'serial' no encontrada en respuesta del API")
                return pd.DataFrame()
            
            logger.info(f"✅ DataFrame creado con {len(df)} registros")
            return df
            
        except Exception as e:
            logger.error(f"❌ Error creando DataFrame: {str(e)}")
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
            logger.error(f"❌ Error procesando metadatos: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {}, {}, {}, {}
    
    def check_if_exists(self, serial: str, fecha_mantenimiento: str) -> bool:
        """
        Verifica si ya existe un registro para este serial y fecha
        
        Args:
            serial: Número de serie
            fecha_mantenimiento: Fecha del mantenimiento (ISO format)
        
        Returns:
            True si existe, False si no
        """
        try:
            # Buscar por serial y fecha aproximada (mismo día)
            # Extraer solo la fecha (sin hora)
            fecha_str = fecha_mantenimiento.split('T')[0]
            
            response = self._make_request(
                "GET",
                f"/mantenimientos?serial=eq.{serial}&datetime_maintenance_end=gte.{fecha_str}T00:00:00&datetime_maintenance_end=lte.{fecha_str}T23:59:59&limit=1"
            )
            
            if response is None:
                return False
            
            # Si response es lista y tiene elementos, existe
            if isinstance(response, list) and len(response) > 0:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error verificando existencia: {str(e)}")
            return False
    
    def upsert_mantenimiento(self, data: Dict) -> bool:
        """
        Inserta o actualiza un mantenimiento (UPSERT)
        Primero verifica si existe, luego decide si INSERT o UPDATE
        
        Args:
            data: Diccionario con datos del mantenimiento
        
        Returns:
            True si exitoso, False en caso contrario
        """
        try:
            serial = data.get('serial')
            fecha = data.get('datetime_maintenance_end')
            
            if not serial or not fecha:
                logger.error("Serial o fecha faltante")
                return False
            
            # Verificar si ya existe
            exists = self.check_if_exists(serial, fecha)
            
            if exists:
                logger.debug(f"⏭️  Serial {serial} ({fecha.split('T')[0]}) ya existe - omitiendo")
                return True  # No es error, simplemente ya existe
            
            # Si no existe, insertar
            logger.debug(f"📝 Insertando nuevo mantenimiento: {serial}")
            
            # PostgREST requiere array de objetos para insert
            headers = self.headers.copy()
            
            response = self._make_request(
                "POST",
                "/mantenimientos",
                json=[data],  # PostgREST espera array
                headers=headers
            )
            
            # PostgREST retorna 201 Created en success
            if response is not None:
                logger.debug(f"✅ Mantenimiento insertado: {serial}")
                return True
            else:
                logger.error(f"❌ Error insertando mantenimiento: {serial}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error en upsert_mantenimiento: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def test_connection(self) -> bool:
        """
        Prueba la conexión al API
        
        Returns:
            True si la conexión es exitosa, False en caso contrario
        """
        try:
            logger.info("🔍 Probando conexión al API de Mantenimientos...")
            
            # Hacer una consulta simple con limit=1
            response = self._make_request(
                "GET",
                "/mantenimientos",
                params={'limit': 1}
            )
            
            if response is not None:
                logger.info("✅ Conexión al API exitosa")
                return True
            else:
                logger.error("❌ Conexión al API falló")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error probando conexión: {str(e)}")
            return False
    
    def get_table_info(self) -> Dict:
        """
        Obtiene información sobre los datos disponibles en el API
        
        Returns:
            Dict con estadísticas
        """
        try:
            # Obtener todos los registros (o un sample grande)
            response = self._make_request(
                "GET",
                "/mantenimientos",
                params={'limit': 10000}  # Ajustar según necesidad
            )
            
            if response is None:
                return {'exists': False, 'error': 'No se pudo conectar al API'}
            
            mantenimientos = response if isinstance(response, list) else response.get('data', [])
            
            if not mantenimientos:
                return {
                    'exists': True,
                    'total_records': 0,
                    'unique_serials': 0
                }
            
            df = pd.DataFrame(mantenimientos)
            
            # Calcular estadísticas
            total_records = len(df)
            unique_serials = df['serial'].nunique() if 'serial' in df.columns else 0
            
            # Rango de fechas
            first_date = None
            last_date = None
            
            if 'datetime_maintenance_end' in df.columns:
                df['datetime_maintenance_end'] = pd.to_datetime(df['datetime_maintenance_end'], errors='coerce')
                df = df.dropna(subset=['datetime_maintenance_end'])
                
                if not df.empty:
                    first_date = df['datetime_maintenance_end'].min().isoformat()
                    last_date = df['datetime_maintenance_end'].max().isoformat()
            
            return {
                'exists': True,
                'total_records': total_records,
                'unique_serials': unique_serials,
                'first_date': first_date,
                'last_date': last_date
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo info: {str(e)}")
            return {'exists': False, 'error': str(e)}


# Singleton
_mantenimientos_api_client = None


def get_mantenimientos_api_client() -> MantenimientosAPIClient:
    """Obtiene instancia singleton del cliente del API de Mantenimientos"""
    global _mantenimientos_api_client
    if _mantenimientos_api_client is None:
        _mantenimientos_api_client = MantenimientosAPIClient()
    return _mantenimientos_api_client