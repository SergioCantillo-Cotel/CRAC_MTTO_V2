from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Configuración del servicio de sincronización CRM"""
    
    # API Configuration
    APP_NAME: str = "CRM Sync API"
    DEBUG: bool = False
    
    # CRM Configuration
    CRM_BASE_URL: str = 'https://crmcotel.com.co'
    CRM_CLIENT_ID: str = 'cd031831-d1f0-0a8b-b0a0-69123cd994f5'
    CRM_CLIENT_SECRET: str = 'Api.v8*'
    
    # PostgreSQL Configuration
    POSTGRES_HOST: str = "host.docker.internal"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "eficiencia_energetica"
    POSTGRES_USER: str = 'api_writter_monitoreo_sedes_telemetria'
    POSTGRES_PASSWORD: str = 'Cotelia_2025*'
    
    # Sync Configuration
    SYNC_INTERVAL_MINUTES: int = 60  # Sincronizar cada hora
    BATCH_SIZE: int = 50  # Tamaño de lote para consultas
    
    @property
    def database_url(self) -> str:
        """URL de conexión a PostgreSQL"""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Singleton para obtener configuración"""
    return Settings()