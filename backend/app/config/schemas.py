from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============== AUTH SCHEMAS ==============
class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


class UserInfo(BaseModel):
    username: str
    name: str
    role: str
    cliente: str


# ============== DEVICE SCHEMAS ==============
class DeviceBase(BaseModel):
    dispositivo: str
    serial: Optional[str] = None
    modelo: Optional[str] = None
    marca: Optional[str] = None


class DeviceAlarm(BaseModel):
    fecha_alarma: datetime
    serial_dispositivo: Optional[str]
    modelo: Optional[str]
    dispositivo: str
    fecha_resolucion: Optional[datetime]
    descripcion: str
    severidad: int


class DeviceWithRisk(DeviceBase):
    tiempo_hasta_umbral: Optional[float]
    tiempo_hasta_umbral_dias: Optional[float]
    riesgo_actual: float
    total_alarmas: int
    tiempo_transcurrido: float
    tiempo_transcurrido_dias: float
    categoria_riesgo: str  # critico, alto, medio, bajo


# ============== PREDICTION SCHEMAS ==============
class PredictionRequest(BaseModel):
    dispositivo: str
    risk_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    max_time: int = Field(default=5000, gt=0)


class PredictionResponse(BaseModel):
    dispositivo: str
    tiempo_hasta_umbral: Optional[float]
    riesgo_actual: float
    tiempo_transcurrido: float
    curva_riesgo: Optional[List[dict]]  # [{tiempo, riesgo}]


class SurvivalCurvePoint(BaseModel):
    tiempo_dias: float
    riesgo_porcentaje: float


class BatchPredictionRequest(BaseModel):
    dispositivos: List[str]
    risk_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    max_time: int = Field(default=5000, gt=0)


# ============== MAINTENANCE SCHEMAS ==============
class MaintenanceRecord(BaseModel):
    serial: str
    hora_salida: datetime
    cliente: Optional[str]
    marca: Optional[str]
    modelo: Optional[str]


class MaintenanceRecommendation(BaseModel):
    equipo: str
    serial: str
    marca: str
    modelo: str
    cliente: str
    ultimo_mantenimiento: Optional[str]
    tiempo_hasta_umbral: float
    tiempo_hasta_umbral_dias: float
    riesgo_actual: float
    categoria: str  # critico, alto, planificar
    fallas_detectadas: List[str]
    recomendaciones: List[str]


# ============== ANALYTICS SCHEMAS ==============
class DeviceStatistics(BaseModel):
    total_devices: int
    devices_critical: int
    devices_high: int
    devices_medium: int
    devices_low: int
    average_risk: float


class TopDevicesResponse(BaseModel):
    devices: List[DeviceWithRisk]
    statistics: DeviceStatistics


# ============== RESPONSE WRAPPERS ==============
class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[dict] = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    detail: Optional[str] = None