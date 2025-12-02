import requests
import streamlit as st
from typing import Optional, List, Dict
import os
from dotenv import load_dotenv

load_dotenv()


class APIClient:
    """Cliente para comunicación con el backend FastAPI"""
    
    def __init__(self):
        self.base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        self.api_prefix = "/api/v1"
        self._token = None
    
    @property
    def token(self) -> Optional[str]:
        """Obtiene token de la sesión de Streamlit"""
        if 'token' in st.session_state:
            return st.session_state.token
        return self._token
    
    @token.setter
    def token(self, value: str):
        """Guarda token en la sesión"""
        self._token = value
        st.session_state.token = value
    
    @property
    def headers(self) -> Dict:
        """Headers con autenticación"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """
        Realiza una petición HTTP al backend
        
        Args:
            method: Método HTTP (GET, POST, etc.)
            endpoint: Endpoint de la API
            **kwargs: Argumentos adicionales para requests
        
        Returns:
            Respuesta JSON o None si hay error
        """
        url = f"{self.base_url}{self.api_prefix}{endpoint}"
        kwargs['headers'] = self.headers
        
        try:
            response = requests.request(method, url, **kwargs, timeout=120)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                st.error("Sesión expirada. Por favor inicie sesión nuevamente.")
                st.session_state.authenticated = False
                st.session_state.token = None
                st.rerun()
            else:
                st.error(f"Error HTTP: {e.response.status_code}")
                try:
                    error_detail = e.response.json().get('detail', str(e))
                    st.error(f"Detalle: {error_detail}")
                except:
                    st.error(f"Detalle: {str(e)}")
            return None
        except requests.exceptions.Timeout:
            st.error("⏱️ Timeout: La solicitud tardó demasiado tiempo")
            return None
        except requests.exceptions.ConnectionError:
            st.error("🔌 Error de conexión: No se pudo conectar al servidor")
            return None
        except Exception as e:
            st.error(f"Error inesperado: {str(e)}")
            return None
    
    # ============= AUTH ENDPOINTS =============
    
    def login(self, username: str, password: str) -> bool:
        """
        Inicia sesión y obtiene token
        
        Args:
            username: Nombre de usuario
            password: Contraseña
        
        Returns:
            True si login exitoso, False en caso contrario
        """
        data = {"username": username, "password": password}
        response = self._make_request("POST", "/auth/login", json=data)
        
        if response and 'access_token' in response:
            self.token = response['access_token']
            return True
        return False
    
    def get_current_user(self) -> Optional[Dict]:
        """
        Obtiene información del usuario actual
        
        Returns:
            Información del usuario o None
        """
        return self._make_request("GET", "/auth/me")
    
    def validate_token(self) -> bool:
        """
        Valida si el token actual es válido
        
        Returns:
            True si es válido, False en caso contrario
        """
        response = self._make_request("POST", "/auth/validate")
        return response is not None and response.get('valid', False)
    
    # ============= DEVICE ENDPOINTS =============
    
    def get_devices_list(self) -> List[str]:
        """
        Obtiene lista de dispositivos disponibles
        
        Returns:
            Lista de nombres de dispositivos
        """
        response = self._make_request("GET", "/devices/list")
        if response:
            return response.get('devices', [])
        return []
    
    def get_device_alarms(self, dispositivos: Optional[List[str]] = None, limit: int = 100) -> List[Dict]:
        """
        Obtiene alarmas de dispositivos
        
        Args:
            dispositivos: Lista opcional de dispositivos para filtrar
            limit: Número máximo de alarmas
        
        Returns:
            Lista de alarmas
        """
        params = {"limit": limit}
        if dispositivos:
            # Convertir lista a string separado por comas
            params['dispositivos'] = ','.join(dispositivos)
        
        response = self._make_request("GET", "/devices/alarms", params=params)
        
        if response and response.get('success'):
            return response.get('data', [])
        return []
    
    def get_top_priority_devices(self, risk_threshold: float = 0.8, top_n: int = 5) -> Optional[Dict]:
        """
        Obtiene dispositivos con mayor prioridad de mantenimiento
        
        Args:
            risk_threshold: Umbral de riesgo
            top_n: Número de dispositivos a retornar
        
        Returns:
            Dict con dispositivos y estadísticas
        """
        params = {"risk_threshold": risk_threshold, "top_n": top_n}
        response = self._make_request("GET", "/devices/top-priority", params=params)
        
        if response and response.get('success'):
            return {
                'devices': response.get('devices', []),
                'statistics': response.get('statistics', {})
            }
        return None
    
    # ============= PREDICTION ENDPOINTS =============
    
    def get_device_prediction(self, dispositivo: str, risk_threshold: float = 0.8,
                             max_time: int = 5000, include_curve: bool = False) -> Optional[Dict]:
        """
        Obtiene predicción de riesgo para un dispositivo
        
        Args:
            dispositivo: Nombre del dispositivo
            risk_threshold: Umbral de riesgo
            max_time: Tiempo máximo de proyección
            include_curve: Si incluir curva de supervivencia
        
        Returns:
            Predicción o None
        """
        params = {
            "risk_threshold": risk_threshold,
            "max_time": max_time,
            "include_curve": include_curve
        }
        return self._make_request("GET", f"/predictions/{dispositivo}", params=params)
    
    def get_batch_predictions(self, dispositivos: List[str], risk_threshold: float = 0.8,
                             max_time: int = 5000, include_curve: bool = False) -> List[Dict]:
        """
        Obtiene predicciones para múltiples dispositivos
        
        Args:
            dispositivos: Lista de dispositivos
            risk_threshold: Umbral de riesgo
            max_time: Tiempo máximo de proyección
            include_curve: Si incluir curvas
        
        Returns:
            Lista de predicciones
        """
        data = {
            "dispositivos": dispositivos,
            "risk_threshold": risk_threshold,
            "max_time": max_time
        }
        params = {"include_curve": include_curve}
        
        response = self._make_request("POST", "/predictions/batch", json=data, params=params)
        return response if response else []
    
    # ============= MAINTENANCE ENDPOINTS =============
    
    def get_maintenance_recommendations(self, risk_threshold: float = 0.8,
                                       categoria: Optional[str] = None) -> List[Dict]:
        """
        Obtiene recomendaciones de mantenimiento
        
        Args:
            risk_threshold: Umbral de riesgo
            categoria: Filtro por categoría (critico, alto, planificar, todos)
        
        Returns:
            Lista de recomendaciones
        """
        params = {"risk_threshold": risk_threshold}
        if categoria:
            params["categoria"] = categoria
        
        response = self._make_request("GET", "/maintenance/recommendations", params=params)
        return response if response else []
    
    def get_maintenance_history(self, serial: str) -> Optional[Dict]:
        """
        Obtiene historial de mantenimiento de un equipo
        
        Args:
            serial: Número de serie
        
        Returns:
            Historial de mantenimiento
        """
        return self._make_request("GET", f"/maintenance/history/{serial}")


# Singleton
_api_client = None


def get_api_client() -> APIClient:
    """Obtiene instancia singleton del cliente API"""
    global _api_client
    if _api_client is None:
        _api_client = APIClient()
    return _api_client