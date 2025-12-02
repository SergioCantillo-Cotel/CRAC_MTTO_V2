import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from app.services.ml_service import get_ml_service
from app.services.bigquery_service import get_bigquery_service
from app.services.crm_service import get_crm_service


# Mapeo de equipos a seriales
EQUIPO_SERIAL_MAPPING = {
    "FANALCA-Aire APC 1 (172.19.1.46)": "JK1142005099",
    "FANALCA-Aire APC 2 (172.19.1.47)": "JK2117000712",
    "FANALCA-Aire APC 3 (172.19.1.44)": "JK2117000986",
    "SPIA-A.A#1 (172.20.196.104)": "SCA131150",
    "SPIA-A.A#2 (172.20.196.105)": "SCA131148",
    "SPIA-A.A#3 (172.20.196.106)": "SCA131149",
    "EAFIT-Bloque 18-1-Direccion Informatica (10.65.0.13)": "UCV101363",
    "EAFIT-Bloque 18-2-Direccion Informatica (10.65.0.14)": "UCV105388",
    "EAFIT-Bloque 19-1-Centro de Computo APOLO (10.65.0.15)": "JK1821004033",
    "EAFIT - Bloque 19 - 2- Centro de Computo APOLO (10.65.0.16)": "JK1831002840",
    "Metro Talleres - Aire 1 (172.17.205.89)": "UK1008210542",
    "Metro Talleres - Aire 2 (172.17.205.93)": "JK16400002252",
    "Metro Talleres - Aire 3 (172.17.205.92)": "JK1905003685",
    "Metro PCC - Aire Rack 4 (172.17.205.104)": "JK1213009088",
    "Metro PCC - Aire Giax 5 (172.17.204.30)": "2016-1091A",
    "Metro PCC - Aire Gfax 8 (172.17.204.33)": "2016-1094A",
    "UTP-AIRE 1 Datacenter (10.100.101.85)": "JK2147003126",
    "UTP-AIRE 2 Datacenter (10.100.101.84)": "JK2147003130",
    "UTP-AIRE 3 Datacenter (10.100.101.86)": "JK2230004923",
    "UNICAUCA-AIRE 1-PASILLO A (10.200.100.27)": "JK1923002790",
    "UNICAUCA-AIRE 2-PASILLO B (10.200.100.29)": "JK1743000230",
    "UNICAUCA-AIRE 3-PASILLO A (10.200.100.28)": "JK1811002605",
    "UNICAUCA-AIRE 4-PASILLO B (10.200.100.30)": "JK1923002792"
}


class AnalyticsService:
    """Servicio para análisis y cálculos de dispositivos"""
    
    def __init__(self):
        self.ml_service = get_ml_service()
        self.bigquery_service = get_bigquery_service()
        self.crm_service = get_crm_service()
    
    def completar_seriales(self, df: pd.DataFrame) -> pd.DataFrame:
        """Completa seriales faltantes usando el mapeo"""
        if 'Serial_dispositivo' not in df.columns:
            df['Serial_dispositivo'] = None
        
        def buscar_serial(nombre_equipo):
            if pd.isna(nombre_equipo):
                return None
            
            nombre_equipo = str(nombre_equipo).strip()
            
            # Búsqueda exacta
            if nombre_equipo in EQUIPO_SERIAL_MAPPING:
                return EQUIPO_SERIAL_MAPPING[nombre_equipo]
            
            # Búsqueda flexible
            nombre_limpio = nombre_equipo.split('(')[0].strip()
            for key, value in EQUIPO_SERIAL_MAPPING.items():
                key_limpio = key.split('(')[0].strip()
                if nombre_limpio == key_limpio:
                    return value
                if (nombre_limpio in key_limpio or key_limpio in nombre_limpio) and len(nombre_limpio) > 3:
                    return value
            
            return None
        
        df['Serial_dispositivo'] = df['Dispositivo'].apply(buscar_serial)
        return df
    
    def process_data(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Procesa datos crudos de BigQuery"""
        if df_raw.empty:
            return pd.DataFrame()
        
        df_raw.columns = [c.strip() for c in df_raw.columns]
        
        # Mapeo de columnas
        col_map = {}
        for c in df_raw.columns:
            lc = c.lower()
            if any(x in lc for x in ['fecha', 'date']) and any(x in lc for x in ['alar', 'alarm']):
                col_map['Fecha_alarma'] = c
            elif any(x in lc for x in ['dispositivo', 'device']) and 'serial' not in lc:
                col_map['Dispositivo'] = c
            elif any(x in lc for x in ['serial', 'serie']):
                col_map['Serial_dispositivo'] = c
            elif any(x in lc for x in ['model', 'modelo']):
                col_map['Modelo'] = c
            elif any(x in lc for x in ['severidad', 'severity']):
                col_map['Severidad'] = c
            elif any(x in lc for x in ['descripcion', 'description']):
                col_map['Descripcion'] = c
            elif any(x in lc for x in ['resolucion', 'resolution']):
                col_map['Fecha_Resolucion'] = c
        
        required = ['Fecha_alarma', 'Dispositivo', 'Severidad']
        missing_cols = [r for r in required if r not in col_map]
        if missing_cols:
            raise ValueError(f"Columnas faltantes: {missing_cols}")
        
        df = df_raw.rename(columns={v: k for k, v in col_map.items()})
        
        # Procesar fechas
        df['Fecha_alarma'] = pd.to_datetime(df['Fecha_alarma'], errors='coerce')
        if df['Fecha_alarma'].dt.tz is not None:
            df['Fecha_alarma'] = df['Fecha_alarma'].dt.tz_localize(None)
        
        if 'Fecha_Resolucion' in df.columns:
            df['Fecha_Resolucion'] = pd.to_datetime(df['Fecha_Resolucion'], errors='coerce')
            if df['Fecha_Resolucion'].dt.tz is not None:
                df['Fecha_Resolucion'] = df['Fecha_Resolucion'].dt.tz_localize(None)
        
        # Limpiar datos
        df['Dispositivo'] = df['Dispositivo'].astype(str).str.strip()
        if 'Serial_dispositivo' in df.columns:
            df['Serial_dispositivo'] = df['Serial_dispositivo'].astype(str).str.strip()
        df['Severidad'] = pd.to_numeric(df['Severidad'], errors='coerce').fillna(0).astype(int)
        
        df = df.dropna(subset=['Fecha_alarma', 'Dispositivo']).copy()
        
        return df
    
    def calculate_device_statistics(self, maintenance_data: List[dict]) -> Dict:
        """Calcula estadísticas de dispositivos"""
        if not maintenance_data:
            return {
                'total_devices': 0,
                'devices_critical': 0,
                'devices_high': 0,
                'devices_medium': 0,
                'devices_low': 0,
                'average_risk': 0.0
            }
        
        df = pd.DataFrame(maintenance_data)
        
        critico = len(df[df['tiempo_hasta_umbral_dias'] < 7])
        alto = len(df[(df['tiempo_hasta_umbral_dias'] >= 7) & (df['tiempo_hasta_umbral_dias'] < 30)])
        medio = len(df[(df['tiempo_hasta_umbral_dias'] >= 30) & (df['tiempo_hasta_umbral_dias'] < 90)])
        bajo = len(df[df['tiempo_hasta_umbral_dias'] >= 90])
        
        return {
            'total_devices': len(df),
            'devices_critical': critico,
            'devices_high': alto,
            'devices_medium': medio,
            'devices_low': bajo,
            'average_risk': float(df['riesgo_actual'].mean()) if len(df) > 0 else 0.0
        }
    
    def get_device_failures(self, df: pd.DataFrame, device: str) -> List[str]:
        """Obtiene fallas detectadas para un dispositivo"""
        device_data = df[df['Dispositivo'] == device]
        if device_data.empty:
            return []
        
        failure_mapping = {
            'Low Superheat Critical': 'Refrigerante inundando compresor - Riesgo de daño mecánico',
            'Compressor High Head Condition': 'Condición de alta presión del compresor - Sobre esfuerzo mecánico',
            'Returned from Idle Due To Leak Detected': 'Fuga de refrigerante detectada - Pérdida de capacidad',
            'Compressor Drive Failure': 'Fallo en accionamiento del compresor - Problema eléctrico',
            "El valor de 'Humedad de suministro' (93 % RH)": 'Alta humedad de suministro',
            "El valor de 'Humedad de suministro' (94 % RH)": 'Alta humedad de suministro'
        }
        
        detected_failures = []
        desc_col = 'Descripcion' if 'Descripcion' in device_data.columns else 'Dispositivo'
        desc_series = device_data[desc_col].astype(str).str.upper()
        
        for keyword, description in failure_mapping.items():
            if desc_series.str.contains(keyword.upper(), case=False, na=False, regex=False).any():
                if description not in detected_failures:
                    detected_failures.append(description)
        
        return detected_failures
    
    def get_maintenance_recommendations(self, device_data: dict, df: pd.DataFrame) -> List[str]:
        """Genera recomendaciones de mantenimiento basadas en fallas"""
        failures = self.get_device_failures(df, device_data['equipo'])
        recommendations = []
        
        if not failures:
            recommendations.extend([
                "Limpieza general de componentes",
                "Verificación de sistemas eléctricos",
                "Calibración de sensores",
                "Revisión preventiva estándar"
            ])
        else:
            for failure in failures:
                if "refrigerante" in failure.lower():
                    recommendations.extend([
                        "Verificar niveles de refrigerante",
                        "Inspeccionar posibles fugas",
                        "Revisar válvulas de expansión"
                    ])
                if "compresor" in failure.lower():
                    recommendations.extend([
                        "Chequear motor del compresor",
                        "Verificar arrancadores",
                        "Revisar presiones de trabajo"
                    ])
                if "humedad" in failure.lower():
                    recommendations.extend([
                        "Calibrar sensores de humedad",
                        "Limpiar bandejas de drenaje",
                        "Verificar filtros de aire"
                    ])
        
        return list(dict.fromkeys(recommendations))  # Eliminar duplicados
    
    def clean_device_name(self, device_name: str) -> str:
        """Elimina IP del nombre del dispositivo"""
        if pd.isna(device_name) or not isinstance(device_name, str):
            return device_name
        return device_name.split('(')[0].strip()


# Singleton
_analytics_service = None


def get_analytics_service() -> AnalyticsService:
    """Obtiene instancia singleton del servicio de analíticas"""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = AnalyticsService()
    return _analytics_service