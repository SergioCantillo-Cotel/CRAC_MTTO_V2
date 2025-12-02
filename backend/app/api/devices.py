from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from app.models.schemas import TokenData
from app.auth.jwt_handler import get_current_active_user
from app.auth.users import user_db
from app.services.preload_service import get_preload_service
from app.config.settings import get_settings
import pandas as pd

router = APIRouter(prefix="/devices", tags=["Devices"])
settings = get_settings()


@router.get("/alarms")
async def get_device_alarms(
    current_user: TokenData = Depends(get_current_active_user),
    dispositivos: Optional[str] = Query(None),
    limit: int = Query(100, le=1000)
):
    """
    Obtiene alarmas de dispositivos según permisos del usuario
    """
    try:
        # Obtener datos pre-cargados
        user_info = user_db.get_user_info(current_user.username)
        cliente = user_info.cliente if user_info and user_info.role != "Administrador" else None
        
        preload_service = get_preload_service()
        data = preload_service.get_cached_data(cliente)
        
        df_raw = data.get('df_raw')
        if df_raw is None or df_raw.empty:
            return {
                "success": True,
                "data": [],
                "total": 0,
                "message": "No hay alarmas disponibles"
            }
        
        # Filtrar por dispositivos si se especifican
        if dispositivos:
            dispositivos_list = [d.strip() for d in dispositivos.split(',')]
            df_raw = df_raw[df_raw['Dispositivo'].isin(dispositivos_list)]
        
        # Limitar resultados
        df_raw = df_raw.head(limit)
        
        # Convertir a diccionarios JSON
        alarms = []
        for _, row in df_raw.iterrows():
            alarm_dict = {
                "fecha_alarma": row['Fecha_alarma'].isoformat() if pd.notna(row['Fecha_alarma']) else None,
                "serial_dispositivo": str(row.get('Serial_dispositivo')) if pd.notna(row.get('Serial_dispositivo')) else None,
                "modelo": str(row.get('Modelo')) if pd.notna(row.get('Modelo')) else None,
                "dispositivo": str(row['Dispositivo']),
                "fecha_resolucion": row.get('Fecha_Resolucion').isoformat() if pd.notna(row.get('Fecha_Resolucion')) else None,
                "descripcion": str(row['Descripcion']),
                "severidad": int(row['Severidad'])
            }
            alarms.append(alarm_dict)
        
        return {
            "success": True,
            "data": alarms,
            "total": len(alarms),
            "message": f"Se obtuvieron {len(alarms)} alarmas",
            "last_update": data['last_update'].isoformat() if data['last_update'] else None
        }
        
    except Exception as e:
        import traceback
        print(f"Error en get_device_alarms: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error obteniendo alarmas: {str(e)}")


@router.get("/list")
async def get_devices_list(
    current_user: TokenData = Depends(get_current_active_user)
):
    """
    Obtiene lista de dispositivos disponibles para el usuario
    
    Returns:
        Lista de dispositivos únicos
    """
    try:
        # Obtener datos pre-cargados
        user_info = user_db.get_user_info(current_user.username)
        cliente = user_info.cliente if user_info and user_info.role != "Administrador" else None
        
        preload_service = get_preload_service()
        data = preload_service.get_cached_data(cliente)
        
        df_raw = data.get('df_raw')
        if df_raw is None or df_raw.empty:
            return {
                "devices": [],
                "total": 0,
                "message": "No hay dispositivos disponibles"
            }
        
        devices = sorted(df_raw['Dispositivo'].unique().tolist())
        
        return {
            "devices": devices,
            "total": len(devices),
            "last_update": data['last_update'].isoformat() if data['last_update'] else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo dispositivos: {str(e)}")


@router.get("/top-priority")
async def get_top_priority_devices(
    risk_threshold: float = Query(0.8, ge=0.0, le=1.0),
    top_n: int = Query(5, ge=1, le=20),
    current_user: TokenData = Depends(get_current_active_user)
):
    """
    Obtiene dispositivos con mayor prioridad de mantenimiento usando datos pre-cargados
    """
    try:
        # Obtener datos pre-cargados
        user_info = user_db.get_user_info(current_user.username)
        cliente = user_info.cliente if user_info and user_info.role != "Administrador" else None
        
        preload_service = get_preload_service()
        data = preload_service.get_cached_data(cliente)
        
        intervals = data['intervals']
        model = data['model']
        features = data['features']
        brand_dict = data['brand_dict']
        model_dict = data['model_dict']
        df_processed = data['df_processed']
        
        if intervals.empty or model is None:
            return {
                "success": True,
                "devices": [],
                "statistics": {
                    'total_devices': 0, 'devices_critical': 0, 'devices_high': 0,
                    'devices_medium': 0, 'devices_low': 0, 'average_risk': 0.0
                },
                "message": "No hay datos suficientes para calcular riesgos",
                "last_update": data['last_update'].isoformat() if data['last_update'] else None
            }
        
        # Importar servicios solo para cálculos
        from app.services.ml_service import get_ml_service
        from app.services.analytics_service import get_analytics_service
        
        ml_service = get_ml_service()
        analytics_service = get_analytics_service()
        
        # Calcular riesgo para cada dispositivo
        maintenance_data = []
        available_devices = sorted(df_processed['Dispositivo'].unique())
        
        for device in available_devices:
            prediction = ml_service.predict_risk(intervals, device, risk_threshold, 5000)
            
            if prediction and prediction['time_to_threshold'] > 0:
                device_intervals = intervals[intervals['unit'] == device]
                if len(device_intervals) > 0:
                    latest_interval = device_intervals.iloc[-1]
                    
                    device_data = df_processed[df_processed['Dispositivo'] == device]
                    serial = str(device_data['Serial_dispositivo'].iloc[0]) if not device_data.empty and pd.notna(device_data['Serial_dispositivo'].iloc[0]) else "N/A"
                    modelo = str(model_dict.get(serial, device_data['Modelo'].iloc[0] if not device_data.empty and pd.notna(device_data['Modelo'].iloc[0]) else "N/A"))
                    marca = str(brand_dict.get(serial, "N/A"))
                    
                    feature_values = [float(latest_interval.get(f, 0)) for f in features]
                    X_pred = pd.DataFrame([feature_values], columns=features)
                    surv_func = model.predict_survival_function(X_pred)[0]
                    current_time = float(latest_interval.get('current_time_elapsed', 0))
                    
                    import numpy as np
                    current_risk = float((1 - np.interp(current_time, surv_func.x, surv_func.y, left=1.0, right=surv_func.y[-1])) * 100)
                    
                    tiempo_dias = prediction['time_to_threshold'] / 24.0
                    if tiempo_dias < 7:
                        categoria = "critico"
                    elif tiempo_dias < 30:
                        categoria = "alto"
                    elif tiempo_dias < 90:
                        categoria = "medio"
                    else:
                        categoria = "bajo"
                    
                    maintenance_data.append({
                        'dispositivo': str(device),
                        'serial': serial,
                        'marca': marca,
                        'modelo': modelo,
                        'tiempo_hasta_umbral': float(prediction['time_to_threshold']),
                        'tiempo_hasta_umbral_dias': float(tiempo_dias),
                        'riesgo_actual': current_risk,
                        'total_alarmas': int(latest_interval['total_alarms']),
                        'tiempo_transcurrido': float(prediction['current_time']),
                        'tiempo_transcurrido_dias': float(prediction['current_time'] / 24.0),
                        'categoria_riesgo': categoria
                    })
        
        if maintenance_data:
            maint_df = pd.DataFrame(maintenance_data)
            maint_df = maint_df.sort_values(['tiempo_hasta_umbral', 'riesgo_actual'], ascending=[True, False])
            top_devices = maint_df.head(top_n)
            devices_list = top_devices.to_dict('records')
            statistics = analytics_service.calculate_device_statistics(maintenance_data)
            
            return {
                "success": True,
                "devices": devices_list,
                "statistics": statistics,
                "message": f"Se obtuvieron {len(devices_list)} dispositivos prioritarios",
                "last_update": data['last_update'].isoformat() if data['last_update'] else None
            }
        
        return {
            "success": True,
            "devices": [],
            "statistics": {
                'total_devices': 0, 'devices_critical': 0, 'devices_high': 0,
                'devices_medium': 0, 'devices_low': 0, 'average_risk': 0.0
            },
            "message": "No se encontraron dispositivos con riesgo",
            "last_update": data['last_update'].isoformat() if data['last_update'] else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error en top_priority_devices: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error calculando prioridades: {str(e)}")