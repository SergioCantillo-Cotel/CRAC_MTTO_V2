from google.oauth2 import service_account
from google.cloud import bigquery
import pandas as pd
from typing import List, Optional
from datetime import datetime, timedelta
from app.config.settings import get_settings


class BigQueryService:
    """Servicio para interactuar con BigQuery"""
    
    def __init__(self):
        self.settings = get_settings()
        self._client = None
        self._credentials = None
    
    @property
    def credentials(self):
        """Lazy loading de credenciales"""
        if self._credentials is None:
            credentials_info = self.settings.gcp_credentials_dict
            self._credentials = service_account.Credentials.from_service_account_info(
                credentials_info
            )
        return self._credentials
    
    @property
    def client(self):
        """Lazy loading del cliente BigQuery"""
        if self._client is None:
            self._client = bigquery.Client(
                project=self.settings.GCP_PROJECT_ID,
                credentials=self.credentials
            )
        return self._client
    
    def get_all_alarms(self, dispositivos_excluir: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Obtiene todas las alarmas de dispositivos de enfriamiento
        
        Args:
            dispositivos_excluir: Lista de dispositivos a excluir (opcional)
        
        Returns:
            DataFrame con alarmas
        """
        sql_query = f"""
        SELECT
            FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S', t1.alarm_date) AS Fecha_alarma,
            t2.serial_number_device AS Serial_dispositivo,
            t2.model_device AS Modelo_equipo,
            t2.name_device AS Dispositivo,
            FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S', t1.alarm_resolution_date) AS Fecha_Resolucion,
            t1.description_alarm AS Descripcion,
            t1.severity AS Severidad
        FROM
            `{self.settings.GCP_PROJECT_ID}`.`{self.settings.GCP_DATASET}`.`alarmas` AS t1
        INNER JOIN
            `{self.settings.GCP_PROJECT_ID}`.`{self.settings.GCP_DATASET}`.`dispositivos` AS t2
        ON
            t1.device_id = t2.id_device
        WHERE
            LOWER(t2.type_device) = 'cooling device'
        ORDER BY
            t1.alarm_date;
        """
        
        try:
            query_job = self.client.query(sql_query)
            results = query_job.result()
            
            data = []
            for row in results:
                data.append({
                    'Fecha_alarma': row['Fecha_alarma'],
                    'Serial_dispositivo': row['Serial_dispositivo'],
                    'Modelo': row['Modelo_equipo'],
                    'Dispositivo': row['Dispositivo'],
                    'Fecha_Resolucion': row['Fecha_Resolucion'] if row['Fecha_Resolucion'] else None,
                    'Descripcion': row['Descripcion'],
                    'Severidad': row['Severidad']
                })
            
            df = pd.DataFrame(data)
            
            if not df.empty:
                # Procesar fechas
                df['Fecha_alarma'] = pd.to_datetime(df['Fecha_alarma'])
                if 'Fecha_Resolucion' in df.columns:
                    df['Fecha_Resolucion'] = pd.to_datetime(df['Fecha_Resolucion'], errors='coerce')
                
                # Filtrar dispositivos excluidos si se especifican
                if dispositivos_excluir:
                    df = df[~df['Dispositivo'].isin(dispositivos_excluir)]
            
            return df
            
        except Exception as e:
            raise Exception(f"Error consultando BigQuery: {str(e)}")
    
    def filter_by_cliente(self, df: pd.DataFrame, cliente: str) -> pd.DataFrame:
        """
        Filtra el DataFrame por cliente usando múltiples estrategias
        
        Args:
            df: DataFrame original
            cliente: Nombre del cliente a filtrar
        
        Returns:
            DataFrame filtrado
        """
        if not cliente or cliente == "Todos los clientes":
            return df.copy()
        
        # Estrategia 1: Buscar por nombre exacto en dispositivo
        mask1 = df["Dispositivo"].str.contains(cliente, case=False, na=False)
        
        # Estrategia 2: Buscar variaciones comunes del nombre
        # Ejemplo: "EAFIT" también busca "UNIVERSIDAD EAFIT", "U. EAFIT", etc.
        variaciones = self._get_client_variations(cliente)
        mask2 = df["Dispositivo"].str.contains('|'.join(variaciones), case=False, na=False, regex=True)
        
        # Combinar ambas estrategias (OR)
        final_mask = mask1 | mask2
        
        filtered_df = df[final_mask].copy()
        
        # Log para debugging
        print(f"🔍 Filtro por cliente '{cliente}':")
        print(f"   - Total registros: {len(df)}")
        print(f"   - Filtrados: {len(filtered_df)}")
        print(f"   - Dispositivos únicos: {filtered_df['Dispositivo'].nunique() if not filtered_df.empty else 0}")
        
        return filtered_df
    
    def _get_client_variations(self, cliente: str) -> list:
        """
        Genera variaciones comunes del nombre del cliente
        
        Args:
            cliente: Nombre del cliente
        
        Returns:
            Lista de variaciones a buscar
        """
        # Mapeo de clientes conocidos a sus variaciones
        variations_map = {
            'EAFIT': ['EAFIT', 'UNIVERSIDAD EAFIT', 'U\\.? EAFIT', 'UNIV\\.? EAFIT'],
            'UNIVERSIDAD EAFIT': ['EAFIT', 'UNIVERSIDAD EAFIT', 'U\\.? EAFIT'],
            'UNICAUCA': ['UNICAUCA', 'UNIVERSIDAD DEL CAUCA', 'U\\.? CAUCA', 'UNIV\\.? CAUCA'],
            'UNIVERSIDAD DEL CAUCA': ['UNICAUCA', 'UNIVERSIDAD DEL CAUCA', 'U\\.? CAUCA'],
            'FANALCA': ['FANALCA'],
            'SPIA': ['SPIA'],
            'METRO': ['METRO', 'METRO TALLERES', 'METRO PCC'],
            'UTP': ['UTP', 'UNIVERSIDAD TECNOLOGICA DE PEREIRA', 'U\\.? PEREIRA']
        }
        
        # Buscar variaciones conocidas
        cliente_upper = cliente.upper()
        for key, variations in variations_map.items():
            if key in cliente_upper or cliente_upper in key:
                return variations
        
        # Si no hay variaciones conocidas, retornar el cliente original
        return [cliente]


# Singleton
_bigquery_service = None


def get_bigquery_service() -> BigQueryService:
    """Obtiene instancia singleton del servicio BigQuery"""
    global _bigquery_service
    if _bigquery_service is None:
        _bigquery_service = BigQueryService()
    return _bigquery_service