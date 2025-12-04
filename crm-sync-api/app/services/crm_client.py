import requests
import urllib3
import time
import logging
from typing import List, Optional, Dict
from app.config.settings import get_settings

# Deshabilitar advertencias SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class CRMClient:
    """Cliente para interactuar con el CRM API"""
    
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
                logger.info("✅ Token CRM obtenido exitosamente")
                return True
            else:
                logger.error(f"❌ Error obteniendo token CRM: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Excepción obteniendo token CRM: {e}")
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
    
    def get_equipos_info(self, seriales: List[str]) -> Optional[List[Dict]]:
        """
        Obtiene información de equipos por sus números de serie
        
        Args:
            seriales: Lista de números de serie
        
        Returns:
            Lista de equipos o None si hay error
        """
        if not self.ensure_valid_token():
            logger.error("❌ No se pudo obtener token válido")
            return None
        
        headers = self.base_headers.copy()
        headers["Authorization"] = f"Bearer {self.access_token}"
        
        # Convertir a lista Python limpia
        seriales_list = [str(s).strip() for s in seriales if s]
        
        data = {"seriales": seriales_list}
        
        try:
            logger.info(f"🔍 Consultando CRM para {len(seriales_list)} seriales...")
            response = requests.post(
                self.equipos_url,
                json=data,
                headers=headers,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                equipos = result.get('data', [])
                logger.info(f"✅ Obtenidos {len(equipos)} equipos del CRM")
                return equipos
            else:
                logger.error(f"❌ Error consultando CRM: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Excepción consultando CRM: {e}")
            return None
    
    def get_all_equipos_batch(self, seriales: List[str], batch_size: int = 50) -> List[Dict]:
        """
        Obtiene información de equipos en lotes
        
        Args:
            seriales: Lista completa de seriales
            batch_size: Tamaño de cada lote
        
        Returns:
            Lista completa de equipos
        """
        all_equipos = []
        
        for i in range(0, len(seriales), batch_size):
            batch = seriales[i:i + batch_size]
            logger.info(f"📦 Procesando lote {i//batch_size + 1} ({len(batch)} seriales)")
            
            equipos = self.get_equipos_info(batch)
            if equipos:
                all_equipos.extend(equipos)
            
            # Pequeña pausa entre lotes
            if i + batch_size < len(seriales):
                time.sleep(1)
        
        logger.info(f"✅ Total de equipos obtenidos: {len(all_equipos)}")
        return all_equipos


# Singleton
_crm_client = None


def get_crm_client() -> CRMClient:
    """Obtiene instancia singleton del cliente CRM"""
    global _crm_client
    if _crm_client is None:
        _crm_client = CRMClient()
    return _crm_client