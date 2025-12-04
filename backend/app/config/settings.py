from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache

class Settings(BaseSettings):
    """Configuración centralizada de la aplicación"""
    
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    APP_NAME: str = "CRAC Monitoring API"
    DEBUG: bool = False
    ALLOWED_ORIGINS: str = "http://localhost:8501"
    
    # JWT Configuration
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # BigQuery Configuration
    GCP_PROJECT_ID: str
    GCP_DATASET: str
    
    # GCP Service Account (JSON como string o ruta)
    GCP_SERVICE_ACCOUNT_TYPE: str
    GCP_SERVICE_ACCOUNT_PROJECT_ID: str
    GCP_SERVICE_ACCOUNT_PRIVATE_KEY_ID: str
    GCP_SERVICE_ACCOUNT_PRIVATE_KEY: str
    GCP_SERVICE_ACCOUNT_CLIENT_EMAIL: str
    GCP_SERVICE_ACCOUNT_CLIENT_ID: str
    GCP_SERVICE_ACCOUNT_AUTH_URI: str
    GCP_SERVICE_ACCOUNT_TOKEN_URI: str
    GCP_SERVICE_ACCOUNT_AUTH_PROVIDER_CERT_URL: str
    GCP_SERVICE_ACCOUNT_CLIENT_CERT_URL: str
    
    # CRM Configuration (YA NO SE USA DIRECTAMENTE - MANTENER POR COMPATIBILIDAD)
    CRM_BASE_URL: str = ""
    CRM_CLIENT_ID: str = ""
    CRM_CLIENT_SECRET: str = ""
    
    # PostgreSQL Configuration (NUEVO - Para consultar mantenimientos)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "eficiencia_energetica"
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    
    # Redis Configuration (opcional)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Model Configuration
    MODEL_CACHE_TTL: int = 3600
    SEVERITY_THRESHOLD: int = 6
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Convierte ALLOWED_ORIGINS string a lista"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    @property
    def gcp_credentials_dict(self) -> dict:
        """Retorna credenciales GCP como diccionario"""
        return {
            "type": self.GCP_SERVICE_ACCOUNT_TYPE,
            "project_id": self.GCP_SERVICE_ACCOUNT_PROJECT_ID,
            "private_key_id": self.GCP_SERVICE_ACCOUNT_PRIVATE_KEY_ID,
            "private_key": self.GCP_SERVICE_ACCOUNT_PRIVATE_KEY.replace('\\n', '\n'),
            "client_email": self.GCP_SERVICE_ACCOUNT_CLIENT_EMAIL,
            "client_id": self.GCP_SERVICE_ACCOUNT_CLIENT_ID,
            "auth_uri": self.GCP_SERVICE_ACCOUNT_AUTH_URI,
            "token_uri": self.GCP_SERVICE_ACCOUNT_TOKEN_URI,
            "auth_provider_x509_cert_url": self.GCP_SERVICE_ACCOUNT_AUTH_PROVIDER_CERT_URL,
            "client_x509_cert_url": self.GCP_SERVICE_ACCOUNT_CLIENT_CERT_URL
        }
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Singleton para obtener configuración"""
    return Settings()