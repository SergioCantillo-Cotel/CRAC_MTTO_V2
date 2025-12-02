import requests
import urllib3
import pandas as pd
import time
from typing import List, Dict, Optional
from app.config.settings import get_settings

# Deshabilitar advertencias SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CRMService:
    """Servicio para interactuar con el CRM API"""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.CRM_BASE_URL
        self.client_id = self.settings.CRM_CLIENT_ID
        self.client_secret = self.settings.CRM_CLIENT_SECRET
        
        self.access_token = None
        self.token_expiry = None
        
        self.token_url = f"{self.base_url}/crm/Api/access_token"
        self.equipos_url = f"{self.base_url}/crm/Api/V8/custom/IA/equipos-info"
        
        self.base_headers = {
            "Content-Type": "application/vnd.api+json",
            "Accept": "application/vnd.api+json"
        }
    
    def get_access_token(self) -> bool:
        """Obtiene un nuevo token de acceso"""
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        
        try:
            response = requests.post(
                self.token_url,
                json=data,
                headers=self.base_headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                tokens = response.json()
                self.access_token = tokens.get('access_token')
                self.token_expiry = time.time() + 3600
                return True
            else:
                print(f"Error obteniendo token CRM: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Excepción obteniendo token CRM: {e}")
            return False
    
    def is_token_valid(self) -> bool:
        """Verifica si el token actual es válido"""
        if not self.access_token or not self.token_expiry:
            return False
        return time.time() < self.token_expiry - 300
    
    def ensure_valid_token(self) -> bool:
        """Garantiza que tenemos un token válido"""
        if not self.is_token_valid():
            return self.get_access_token()
        return True
    
    def get_equipos_info(self, seriales: List[str]) -> Optional[Dict]:
        """
        Obtiene información de equipos por sus números de serie
        
        Args:
            seriales: Lista de números de serie
        
        Returns:
            Dict con respuesta del API o None si hay error
        """
        if not self.ensure_valid_token():
            return None
        
        headers = self.base_headers.copy()
        headers["Authorization"] = f"Bearer {self.access_token}"
        
        # Convertir a lista Python si es numpy array
        if hasattr(seriales, 'tolist'):
            seriales_list = seriales.tolist()
        else:
            seriales_list = list(seriales)
        
        data = {"seriales": seriales_list}
        
        try:
            response = requests.post(
                self.equipos_url,
                json=data,
                headers=headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error consultando CRM: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Excepción consultando CRM: {e}")
            return None
    
    def get_equipos_dataframe(self, seriales: List[str]) -> Optional[pd.DataFrame]:
        """
        Obtiene información de equipos como DataFrame
        
        Args:
            seriales: Lista de números de serie
        
        Returns:
            DataFrame con información o None si hay error
        """
        response_data = self.get_equipos_info(seriales)
        
        if response_data and 'data' in response_data:
            df = pd.DataFrame(response_data['data'])
            return df
        
        return None
    
    def get_maintenance_metadata(self, df_mttos: pd.DataFrame) -> tuple:
        """
        Obtiene metadatos de mantenimiento de forma optimizada
        
        Args:
            df_mttos: DataFrame con datos de mantenimiento
        
        Returns:
            Tuple (last_maintenance_dict, client_dict, brand_dict, model_dict)
        """
        if df_mttos.empty:
            return {}, {}, {}, {}
        
        try:
            # Ordenar y obtener últimos registros
            last_records = df_mttos.sort_values('hora_salida', ascending=False)
            last_records = last_records.drop_duplicates('serial', keep='first')
            
            # Crear diccionarios
            last_maintenance_dict = dict(zip(
                last_records['serial'],
                last_records['hora_salida']
            ))
            
            client_dict = {}
            if 'cliente' in last_records.columns:
                client_dict = dict(zip(last_records['serial'], last_records['cliente']))
            
            brand_dict = {}
            if 'marca' in last_records.columns:
                brand_dict = dict(zip(last_records['serial'], last_records['marca']))
            
            model_dict = {}
            if 'modelo' in last_records.columns:
                model_dict = dict(zip(last_records['serial'], last_records['modelo']))
            
            return last_maintenance_dict, client_dict, brand_dict, model_dict
            
        except Exception as e:
            print(f"Error procesando metadatos mantenimiento: {e}")
            return {}, {}, {}, {}


# Singleton
_crm_service = None


def get_crm_service() -> CRMService:
    """Obtiene instancia singleton del servicio CRM"""
    global _crm_service
    if _crm_service is None:
        _crm_service = CRMService()
    return _crm_service