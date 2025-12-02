from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from app.models.schemas import (TokenData, PredictionResponse, SurvivalCurvePoint,
                                BatchPredictionRequest)
from app.auth.jwt_handler import get_current_active_user
from app.auth.users import user_db
from app.services.bigquery_service import get_bigquery_service
from app.services.analytics_service import get_analytics_service
from app.services.ml_service import get_ml_service
from app.services.crm_service import get_crm_service
from app.config.settings import get_settings
import pandas as pd

router = APIRouter(prefix="/predictions", tags=["Predictions"])
settings = get_settings()


@router.get("/{dispositivo}", response_model=PredictionResponse)
async def get_device_prediction(
    dispositivo: str,
    risk_threshold: float = Query(0.8, ge=0.0, le=1.0),
    max_time: int = Query(5000, gt=0),
    include_curve: bool = Query(False),
    current_user: TokenData = Depends(get_current_active_user)
):
    """
    Obtiene predicción de riesgo para un dispositivo específico
    
    Args:
        dispositivo: Nombre del dispositivo
        risk_threshold: Umbral de riesgo
        max_time: Tiempo máximo de proyección (horas)
        include_curve: Si incluir curva completa de supervivencia
        current_user: Usuario autenticado
    
    Returns:
        Predicción de riesgo del dispositivo
    """
    try:
        # Verificar permisos
        user_info = user_db.get_user_info(current_user.username)
        
        # Obtener servicios
        bigquery_service = get_bigquery_service()
        analytics_service = get_analytics_service()
        ml_service = get_ml_service()
        crm_service = get_crm_service()
        
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
        
        # Verificar que el dispositivo existe
        if dispositivo not in df_raw['Dispositivo'].values:
            raise HTTPException(status_code=404, detail=f"Dispositivo '{dispositivo}' no encontrado")
        
        df_raw = analytics_service.completar_seriales(df_raw)
        df = analytics_service.process_data(df_raw)
        
        # Obtener datos de mantenimiento
        seriales = df_raw['Serial_dispositivo'].unique()
        df_mttos = crm_service.get_equipos_dataframe(seriales)
        
        maintenance_dict = {}
        if df_mttos is not None and not df_mttos.empty:
            df_mttos['serial'] = df_mttos['serial'].str.strip()
            df_mttos['hora_salida'] = pd.to_datetime(df_mttos['hora_salida'], errors='coerce')
            df_mttos = df_mttos.dropna(subset=['hora_salida'])
            maintenance_dict, _, _, _ = crm_service.get_maintenance_metadata(df_mttos)
        
        # Detectar fallas y construir intervalos
        df['is_failure_bool'] = ml_service.detect_failures(df, 'Descripcion', 'Severidad', settings.SEVERITY_THRESHOLD)
        intervals = ml_service.build_intervals(
            df, 'Dispositivo', 'Fecha_alarma', 'is_failure_bool',
            settings.SEVERITY_THRESHOLD, maintenance_dict
        )
        
        if intervals.empty:
            raise HTTPException(status_code=400, detail="No se pudieron generar intervalos")
        
        # Entrenar modelo
        try:
            rsf_model, features = ml_service.train_model(intervals)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"No se pudo entrenar modelo: {str(e)}")
        
        # Hacer predicción
        prediction = ml_service.predict_risk(intervals, dispositivo, risk_threshold, max_time)
        
        if not prediction:
            raise HTTPException(status_code=404, detail=f"No se pudo calcular predicción para '{dispositivo}'")
        
        # Calcular riesgo actual
        device_intervals = intervals[intervals['unit'] == dispositivo]
        if device_intervals.empty:
            raise HTTPException(status_code=404, detail=f"No hay intervalos para '{dispositivo}'")
        
        latest_interval = device_intervals.iloc[-1]
        feature_values = [float(latest_interval.get(f, 0)) for f in features]
        X_pred = pd.DataFrame([feature_values], columns=features)
        surv_func = rsf_model.predict_survival_function(X_pred)[0]
        current_time = float(latest_interval.get('current_time_elapsed', 0))
        
        import numpy as np
        current_risk = (1 - np.interp(current_time, surv_func.x, surv_func.y, left=1.0, right=surv_func.y[-1])) * 100
        
        # Construir respuesta
        response = PredictionResponse(
            dispositivo=dispositivo,
            tiempo_hasta_umbral=prediction['time_to_threshold'],
            riesgo_actual=current_risk,
            tiempo_transcurrido=prediction['current_time'],
            curva_riesgo=None
        )
        
        # Agregar curva si se solicita
        if include_curve:
            curve_points = ml_service.get_survival_curve(intervals, dispositivo, max_time, 500)
            if curve_points:
                response.curva_riesgo = curve_points
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en predicción: {str(e)}")


@router.post("/batch", response_model=List[PredictionResponse])
async def get_batch_predictions(
    request: BatchPredictionRequest,
    include_curve: bool = Query(False),
    current_user: TokenData = Depends(get_current_active_user)
):
    """
    Obtiene predicciones para múltiples dispositivos
    
    Args:
        request: Lista de dispositivos y parámetros
        include_curve: Si incluir curvas de supervivencia
        current_user: Usuario autenticado
    
    Returns:
        Lista de predicciones
    """
    try:
        # Obtener servicios
        bigquery_service = get_bigquery_service()
        analytics_service = get_analytics_service()
        ml_service = get_ml_service()
        crm_service = get_crm_service()
        
        # Verificar permisos
        user_info = user_db.get_user_info(current_user.username)
        
        # Obtener datos una sola vez
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
        
        # Obtener datos de mantenimiento
        seriales = df_raw['Serial_dispositivo'].unique()
        df_mttos = crm_service.get_equipos_dataframe(seriales)
        
        maintenance_dict = {}
        if df_mttos is not None and not df_mttos.empty:
            df_mttos['serial'] = df_mttos['serial'].str.strip()
            df_mttos['hora_salida'] = pd.to_datetime(df_mttos['hora_salida'], errors='coerce')
            df_mttos = df_mttos.dropna(subset=['hora_salida'])
            maintenance_dict, _, _, _ = crm_service.get_maintenance_metadata(df_mttos)
        
        # Detectar fallas y construir intervalos
        df['is_failure_bool'] = ml_service.detect_failures(df, 'Descripcion', 'Severidad', settings.SEVERITY_THRESHOLD)
        intervals = ml_service.build_intervals(
            df, 'Dispositivo', 'Fecha_alarma', 'is_failure_bool',
            settings.SEVERITY_THRESHOLD, maintenance_dict
        )
        
        if intervals.empty:
            return []
        
        # Entrenar modelo una vez
        try:
            rsf_model, features = ml_service.train_model(intervals)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"No se pudo entrenar modelo: {str(e)}")
        
        # Hacer predicciones para cada dispositivo
        predictions = []
        
        for dispositivo in request.dispositivos:
            if dispositivo not in df['Dispositivo'].values:
                continue
            
            prediction = ml_service.predict_risk(
                intervals, dispositivo, request.risk_threshold, request.max_time
            )
            
            if not prediction:
                continue
            
            # Calcular riesgo actual
            device_intervals = intervals[intervals['unit'] == dispositivo]
            if device_intervals.empty:
                continue
            
            latest_interval = device_intervals.iloc[-1]
            feature_values = [float(latest_interval.get(f, 0)) for f in features]
            X_pred = pd.DataFrame([feature_values], columns=features)
            surv_func = rsf_model.predict_survival_function(X_pred)[0]
            current_time = float(latest_interval.get('current_time_elapsed', 0))
            
            import numpy as np
            current_risk = (1 - np.interp(current_time, surv_func.x, surv_func.y, 
                                         left=1.0, right=surv_func.y[-1])) * 100
            
            pred_response = PredictionResponse(
                dispositivo=dispositivo,
                tiempo_hasta_umbral=prediction['time_to_threshold'],
                riesgo_actual=current_risk,
                tiempo_transcurrido=prediction['current_time'],
                curva_riesgo=None
            )
            
            if include_curve:
                curve_points = ml_service.get_survival_curve(intervals, dispositivo, request.max_time, 500)
                if curve_points:
                    pred_response.curva_riesgo = curve_points
            
            predictions.append(pred_response)
        
        return predictions
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en predicciones batch: {str(e)}")