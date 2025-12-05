from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from app.models.schemas import TokenData, MaintenanceRecommendation
from app.auth.jwt_handler import get_current_active_user
from app.auth.users import user_db
from app.services.bigquery_service import get_bigquery_service
from app.services.analytics_service import get_analytics_service
from app.services.ml_service import get_ml_service
from app.services.mantenimientos_api_client import get_mantenimientos_api_client
from app.config.settings import get_settings
import pandas as pd
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/maintenance", tags=["Maintenance"])
settings = get_settings()


def format_maintenance_date(date) -> str:
    """Formatea fecha de mantenimiento"""
    if pd.isna(date) or date is None:
        return "Nunca"
    
    try:
        days_ago = (datetime.now().date() - date.date()).days
        
        if days_ago == 0:
            return "Hoy"
        elif days_ago == 1:
            return "Ayer"
        elif days_ago < 7:
            return f"Hace {days_ago} días"
        elif days_ago < 30:
            weeks = days_ago // 7
            return f"Hace {weeks} semana{'s' if weeks > 1 else ''}"
        else:
            return date.strftime("%d/%m/%Y")
    except:
        return date.strftime("%d/%m/%Y") if hasattr(date, 'strftime') else str(date)


@router.get("/recommendations", response_model=List[MaintenanceRecommendation])
async def get_maintenance_recommendations(
    risk_threshold: float = Query(0.8, ge=0.0, le=1.0),
    categoria: str = Query(None, regex="^(critico|alto|planificar|todos)$"),
    current_user: TokenData = Depends(get_current_active_user)
):
    """
    Obtiene recomendaciones de mantenimiento para dispositivos
    
    Args:
        risk_threshold: Umbral de riesgo
        categoria: Filtro por categoría (critico, alto, planificar, todos)
        current_user: Usuario autenticado
    
    Returns:
        Lista de recomendaciones de mantenimiento
    """
    try:
        # Obtener servicios
        bigquery_service = get_bigquery_service()
        analytics_service = get_analytics_service()
        ml_service = get_ml_service()
        api_client = get_mantenimientos_api_client()
        
        # Verificar permisos
        user_info = user_db.get_user_info(current_user.username)
        
        # Obtener datos
        dispositivos_excluir = [
            '10.102.148.11', '10.102.148.13', '10.102.148.16', '10.102.148.10',
            '10.102.148.19', '10.102.148.12', '10.102.148.20', '10.102.148.15',
            '10.102.148.21', '10.102.148.17', '10.102.148.18', '10.102.148.14',
            '10.102.148.23', '10.102.148.22'
        ]
        
        df_raw = bigquery_service.get_all_alarms(dispositivos_excluir)
        
        # Filtrar por usuario
        if user_info and user_info.role != "Administrador":
            df_raw = bigquery_service.filter_by_cliente(df_raw, user_info.cliente)
        
        df_raw = analytics_service.completar_seriales(df_raw)
        df = analytics_service.process_data(df_raw)
        
        # Obtener datos de mantenimiento desde API REST (CAMBIO)
        seriales = df_raw['Serial_dispositivo'].dropna().unique().tolist()
        df_mttos = api_client.get_mantenimientos_dataframe(seriales)
        
        maintenance_dict = {}
        client_dict = {}
        brand_dict = {}
        model_dict = {}
        
        if df_mttos is not None and not df_mttos.empty:
            maintenance_dict, client_dict, brand_dict, model_dict = api_client.get_maintenance_metadata(df_mttos)
        
        # Detectar fallas y construir intervalos
        df['is_failure_bool'] = ml_service.detect_failures(df, 'Descripcion', 'Severidad', settings.SEVERITY_THRESHOLD)
        intervals = ml_service.build_intervals(
            df, 'Dispositivo', 'Fecha_alarma', 'is_failure_bool',
            settings.SEVERITY_THRESHOLD, maintenance_dict
        )
        
        if intervals.empty:
            return []
        
        # Entrenar modelo
        try:
            rsf_model, features = ml_service.train_model(intervals)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"No se pudo entrenar modelo: {str(e)}")
        
        # Calcular recomendaciones para cada dispositivo
        recommendations = []
        available_devices = sorted(df['Dispositivo'].unique())
        
        for device in available_devices:
            try:
                prediction = ml_service.predict_risk(intervals, device, risk_threshold, 5000)
                
                if prediction and prediction['time_to_threshold'] > 0:
                    device_intervals = intervals[intervals['unit'] == device]
                    if len(device_intervals) > 0:
                        latest_interval = device_intervals.iloc[-1]
                        
                        # Obtener información del dispositivo
                        device_data = df[df['Dispositivo'] == device]
                        if device_data.shape[0] == 0:
                            continue
                        
                        serial = str(device_data['Serial_dispositivo'].iloc[0]) if pd.notna(device_data['Serial_dispositivo'].iloc[0]) else "N/A"
                        modelo = model_dict.get(serial, str(device_data['Modelo'].iloc[0]) if pd.notna(device_data['Modelo'].iloc[0]) else "N/A")
                        marca = brand_dict.get(serial, "N/A")
                        cliente = client_dict.get(serial, "No especificado")
                        
                        # Obtener último mantenimiento
                        last_maintenance = maintenance_dict.get(serial)
                        ultimo_mantenimiento = format_maintenance_date(last_maintenance)
                        
                        # Calcular riesgo actual
                        feature_values = [float(latest_interval.get(f, 0)) for f in features]
                        X_pred = pd.DataFrame([feature_values], columns=features)
                        surv_func = rsf_model.predict_survival_function(X_pred)[0]
                        current_time = float(latest_interval.get('current_time_elapsed', 0))
                        
                        current_risk = float((1 - np.interp(current_time, surv_func.x, surv_func.y, 
                                                      left=1.0, right=surv_func.y[-1])) * 100)
                        
                        # Categorizar
                        tiempo_dias = float(prediction['time_to_threshold']) / 24.0
                        if tiempo_dias < 7:
                            cat = "critico"
                        elif tiempo_dias < 30:
                            cat = "alto"
                        else:
                            cat = "planificar"
                        
                        # Filtrar por categoría si se especifica
                        if categoria and categoria != "todos" and cat != categoria:
                            continue
                        
                        # Obtener fallas y recomendaciones
                        fallas = analytics_service.get_device_failures(df, device)
                        recomendaciones = analytics_service.get_maintenance_recommendations(
                            {'equipo': device}, df
                        )
                        
                        recommendations.append(MaintenanceRecommendation(
                            equipo=device,
                            serial=serial,
                            marca=marca,
                            modelo=modelo,
                            cliente=cliente,
                            ultimo_mantenimiento=ultimo_mantenimiento,
                            tiempo_hasta_umbral=float(prediction['time_to_threshold']),
                            tiempo_hasta_umbral_dias=float(tiempo_dias),
                            riesgo_actual=float(current_risk),
                            categoria=cat,
                            fallas_detectadas=fallas,
                            recomendaciones=recomendaciones
                        ))
            except Exception as e:
                import traceback
                logger.error(f"Error procesando dispositivo {device}: {str(e)}")
                logger.error(traceback.format_exc())
                continue
        
        # Ordenar por prioridad
        recommendations.sort(key=lambda x: (
            {'critico': 0, 'alto': 1, 'planificar': 2}.get(x.categoria, 3),
            x.tiempo_hasta_umbral
        ))
        
        return recommendations
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error obteniendo recomendaciones: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error obteniendo recomendaciones: {str(e)}")


@router.get("/history/{serial}")
async def get_maintenance_history(
    serial: str,
    current_user: TokenData = Depends(get_current_active_user)
):
    """
    Obtiene historial de mantenimiento de un equipo por serial
    
    Args:
        serial: Número de serie del equipo
        current_user: Usuario autenticado
    
    Returns:
        Historial de mantenimiento
    """
    try:
        api_client = get_mantenimientos_api_client()
        
        # Consultar API de Mantenimientos (CAMBIO)
        mantenimientos_list = api_client.get_mantenimientos_by_seriales([serial])
        
        if not mantenimientos_list:
            return {
                "serial": serial,
                "mantenimientos": [],
                "total": 0
            }
        
        # Procesar datos
        df_mttos = pd.DataFrame(mantenimientos_list)
        
        # Renombrar columnas si es necesario
        if 'datetime_maintenance_end' in df_mttos.columns:
            df_mttos['hora_salida'] = pd.to_datetime(df_mttos['datetime_maintenance_end'], errors='coerce')
        
        if 'customer_name' in df_mttos.columns:
            df_mttos['cliente'] = df_mttos['customer_name']
        
        if 'device_brand' in df_mttos.columns:
            df_mttos['marca'] = df_mttos['device_brand']
        
        if 'device_model' in df_mttos.columns:
            df_mttos['modelo'] = df_mttos['device_model']
        
        df_mttos = df_mttos.dropna(subset=['hora_salida'])
        df_mttos = df_mttos.sort_values('hora_salida', ascending=False)
        
        mantenimientos = []
        for _, row in df_mttos.iterrows():
            mantenimientos.append({
                "fecha": row['hora_salida'].strftime('%Y-%m-%d %H:%M:%S'),
                "cliente": row.get('cliente', 'N/A'),
                "marca": row.get('marca', 'N/A'),
                "modelo": row.get('modelo', 'N/A')
            })
        
        return {
            "serial": serial,
            "mantenimientos": mantenimientos,
            "total": len(mantenimientos)
        }
        
    except Exception as e:
        import traceback
        print(f"Error obteniendo historial: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error obteniendo historial: {str(e)}")