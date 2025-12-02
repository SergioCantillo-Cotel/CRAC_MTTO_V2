import numpy as np
import pandas as pd
from sksurv.ensemble import RandomSurvivalForest
from sksurv.util import Surv
from sklearn.impute import SimpleImputer
from typing import Tuple, Optional, List
from datetime import datetime, timedelta
import warnings


class MLService:
    """Servicio para entrenamiento y predicciones del modelo de supervivencia"""
    
    def __init__(self):
        self.model = None
        self.features = ['total_alarms', 'alarms_last_24h', 'time_since_last_alarm_h']
        self.rsf_params = {
            "n_estimators": 250,
            "max_features": "sqrt",
            "n_jobs": -1,
            "random_state": 42
        }
    
    def detect_failures(self, df: pd.DataFrame, desc_col: str = 'Descripcion', 
                       sev_col: str = 'Severidad', sev_thr: Optional[int] = None) -> pd.Series:
        """
        Detecta fallas basado en palabras clave
        
        Args:
            df: DataFrame con datos de alarmas
            desc_col: Columna de descripción
            sev_col: Columna de severidad
            sev_thr: Umbral de severidad (opcional)
        
        Returns:
            Serie booleana indicando fallas
        """
        keywords = [
            'Low Superheat Critical',
            'Compressor High Head Condition',
            'Returned from Idle Due To Leak Detected',
            'Compressor Drive Failure',
            "El valor de 'Humedad de suministro' (93 % RH) ha sido muy alto durante mucho tiempo",
            "El valor de 'Humedad de suministro' (94 % RH) ha sido muy alto durante mucho tiempo",
        ]
        
        exclude_words = ['cleared', 'corrected', 'restored', 'ok', 'normal', 'return to normal', 'solucionado']
        
        if desc_col not in df.columns:
            return pd.Series(False, index=df.index)
        
        desc_match = (
            df[desc_col].astype(str).str.contains('|'.join(keywords), case=False, na=False) &
            ~df[desc_col].astype(str).str.contains('|'.join(exclude_words), case=False, na=False)
        )
        
        return desc_match
    
    def build_intervals(self, df: pd.DataFrame, id_col: str, time_col: str,
                       is_failure_col: str, sev_thr: int,
                       last_maintenance_dict: Optional[dict] = None) -> pd.DataFrame:
        """
        Construye intervalos de supervivencia desde datos de alarmas
        
        Args:
            df: DataFrame con datos
            id_col: Columna de identificación de dispositivo
            time_col: Columna de tiempo
            is_failure_col: Columna booleana de fallas
            sev_thr: Umbral de severidad
            last_maintenance_dict: Diccionario con últimos mantenimientos
        
        Returns:
            DataFrame con intervalos de supervivencia
        """
        df = df.sort_values([id_col, time_col]).reset_index(drop=True)
        recs = []
        now = pd.Timestamp.now().tz_localize(None)
        
        for unit, g in df.groupby(id_col):
            g = g.reset_index(drop=True)
            
            # Procesar tiempos
            if pd.api.types.is_datetime64_any_dtype(g[time_col]):
                try:
                    times = g[time_col].dt.tz_localize(None) if g[time_col].dt.tz is not None else g[time_col]
                except Exception:
                    times = pd.to_datetime(g[time_col], errors='coerce').dt.tz_localize(None)
            else:
                times = pd.to_datetime(g[time_col], errors='coerce').dt.tz_localize(None)
            
            times = times.to_numpy(dtype='datetime64[ns]')
            is_fail = g[is_failure_col].to_numpy(dtype=bool)
            n = len(g)
            
            if n == 0:
                continue
            
            # Obtener fecha de último mantenimiento
            last_maintenance_time = None
            if last_maintenance_dict:
                device_data = df[df[id_col] == unit]
                if not device_data.empty and 'Serial_dispositivo' in device_data.columns:
                    serial = device_data['Serial_dispositivo'].iloc[0]
                    last_maintenance_time = last_maintenance_dict.get(serial)
                    if last_maintenance_time is not None:
                        last_maintenance_time = pd.Timestamp(last_maintenance_time).tz_localize(None)
            
            # Calcular tiempo base
            last_critical_time = self._get_last_critical_alarm_time(df, unit, sev_thr, id_col, time_col)
            
            if last_maintenance_time is not None:
                if last_critical_time is not None:
                    start_time = max(last_maintenance_time, pd.Timestamp(last_critical_time).tz_localize(None))
                else:
                    start_time = last_maintenance_time
                current_time_elapsed = (now - start_time).total_seconds() / 3600.0
            else:
                if last_critical_time is not None:
                    last_critical_time = pd.Timestamp(last_critical_time).tz_localize(None)
                    current_time_elapsed = (now - last_critical_time).total_seconds() / 3600.0
                else:
                    current_time_elapsed = 0.0
            
            start_idx = 0
            fail_indices = np.where(is_fail)[0]
            
            if len(fail_indices) == 0:
                # No hay fallas
                start_time = pd.Timestamp(times[start_idx])
                duration_h = (now - start_time).total_seconds() / 3600.0
                last_alarm_time = pd.Timestamp(times[-1]) if n > 0 else None
                time_since_last_alarm_h = (now - last_alarm_time).total_seconds() / 3600.0 if last_alarm_time else np.nan
                
                recs.append({
                    'unit': unit,
                    'start': start_time,
                    'end': now,
                    'duration_hours': float(duration_h),
                    'event': 0,
                    'total_alarms': int(n),
                    'alarms_last_24h': 0,
                    'time_since_last_alarm_h': float(time_since_last_alarm_h) if not np.isnan(time_since_last_alarm_h) else np.nan,
                    'current_time_elapsed': float(current_time_elapsed),
                    'last_critical_time': last_critical_time,
                    'last_maintenance_time': last_maintenance_time
                })
            else:
                # Procesar fallas
                for fi in fail_indices:
                    end_idx = fi
                    if end_idx <= start_idx:
                        start_idx = end_idx
                        continue
                    
                    start_time = pd.Timestamp(times[start_idx])
                    end_time = pd.Timestamp(times[end_idx])
                    duration_h = (end_time - start_time).total_seconds() / 3600.0
                    total_alarms = end_idx - start_idx
                    
                    lookback_time = start_time - timedelta(hours=24)
                    alarms_last_24h = int(np.sum((times >= np.datetime64(lookback_time)) & (times < np.datetime64(start_time))))
                    
                    last_alarm_before_idx = start_idx - 1
                    if last_alarm_before_idx >= 0:
                        last_alarm_time = pd.Timestamp(times[last_alarm_before_idx])
                        time_since_last_alarm_h = (start_time - last_alarm_time).total_seconds() / 3600.0
                    else:
                        time_since_last_alarm_h = np.nan
                    
                    recs.append({
                        'unit': unit,
                        'start': start_time,
                        'end': end_time,
                        'duration_hours': float(duration_h),
                        'event': 1,
                        'total_alarms': int(total_alarms),
                        'alarms_last_24h': int(alarms_last_24h),
                        'time_since_last_alarm_h': float(time_since_last_alarm_h) if not np.isnan(time_since_last_alarm_h) else np.nan,
                        'current_time_elapsed': float(current_time_elapsed),
                        'last_critical_time': last_critical_time,
                        'last_maintenance_time': last_maintenance_time
                    })
                    start_idx = end_idx
                
                # Intervalo final censurado
                if start_idx < n:
                    start_time = pd.Timestamp(times[start_idx])
                    duration_h = (now - start_time).total_seconds() / 3600.0
                    total_alarms = n - start_idx
                    lookback_time = start_time - timedelta(hours=24)
                    alarms_last_24h = int(np.sum((times >= np.datetime64(lookback_time)) & (times < np.datetime64(start_time))))
                    last_alarm_time = pd.Timestamp(times[-1])
                    time_since_last_alarm_h = (now - last_alarm_time).total_seconds() / 3600.0
                    
                    recs.append({
                        'unit': unit,
                        'start': start_time,
                        'end': now,
                        'duration_hours': float(duration_h),
                        'event': 0,
                        'total_alarms': int(total_alarms),
                        'alarms_last_24h': int(alarms_last_24h),
                        'time_since_last_alarm_h': float(time_since_last_alarm_h),
                        'current_time_elapsed': float(current_time_elapsed),
                        'last_critical_time': last_critical_time,
                        'last_maintenance_time': last_maintenance_time
                    })
        
        return pd.DataFrame(recs)
    
    def _get_last_critical_alarm_time(self, df, device, sev_thr, id_col, time_col):
        """Obtiene tiempo de última alarma crítica"""
        device_alarms = df[df[id_col] == device]
        if device_alarms.empty:
            return None
        if sev_thr is not None:
            critical_alarms = device_alarms[device_alarms['Severidad'] >= sev_thr]
        else:
            critical_alarms = device_alarms
        if len(critical_alarms) > 0:
            return critical_alarms[time_col].max()
        else:
            return device_alarms[time_col].max() if len(device_alarms) > 0 else None
    
    def train_model(self, intervals: pd.DataFrame) -> Tuple[RandomSurvivalForest, List[str]]:
        """
        Entrena el modelo Random Survival Forest
        
        Args:
            intervals: DataFrame con intervalos de supervivencia
        
        Returns:
            Tuple (modelo_entrenado, lista_de_features)
        """
        if len(intervals) == 0:
            raise ValueError("No hay intervalos para entrenar")
        
        missing_features = [f for f in self.features if f not in intervals.columns]
        if missing_features:
            raise ValueError(f"Faltan características: {missing_features}")
        
        X_df = intervals[self.features].copy()
        
        # Imputar valores faltantes
        imputer = SimpleImputer(strategy='median')
        X_imputed = imputer.fit_transform(X_df)
        X_df = pd.DataFrame(X_imputed, columns=self.features, index=X_df.index)
        
        events = intervals['event'].astype(bool).to_numpy()
        times = intervals['duration_hours'].to_numpy()
        
        n_samples = len(events)
        n_events = int(np.sum(events))
        
        if n_events == 0:
            raise ValueError(f"No hay eventos para entrenar (todos censurados)")
        
        if n_events < 3:
            raise ValueError(f"Muy pocos eventos ({n_events}), mínimo 3 requeridos")
        
        if n_samples < 10:
            raise ValueError(f"Muy pocas muestras ({n_samples}), mínimo 10 requeridas")
        
        if np.std(times) == 0:
            raise ValueError("No hay variabilidad en tiempos de supervivencia")
        
        y = Surv.from_arrays(event=events, time=times)
        rsf = RandomSurvivalForest(**self.rsf_params)
        rsf.fit(X_df, y)
        
        self.model = rsf
        return rsf, self.features
    
    def predict_risk(self, intervals: pd.DataFrame, device: str,
                    risk_threshold: float = 0.8, max_time: int = 5000) -> dict:
        """
        Predice el riesgo para un dispositivo específico
        
        Args:
            intervals: DataFrame con intervalos
            device: Nombre del dispositivo
            risk_threshold: Umbral de riesgo
            max_time: Tiempo máximo de proyección
        
        Returns:
            Dict con predicción de riesgo
        """
        if self.model is None:
            raise ValueError("Modelo no entrenado")
        
        if device not in intervals['unit'].values:
            return None
        
        device_intervals = intervals[intervals['unit'] == device]
        if len(device_intervals) == 0:
            return None
        
        latest_interval = device_intervals.iloc[-1]
        
        feature_values = []
        for feature in self.features:
            val = latest_interval.get(feature, 0)
            feature_values.append(0.0 if pd.isna(val) else float(val))
        
        X_pred = pd.DataFrame([feature_values], columns=self.features)
        
        surv_funcs = self.model.predict_survival_function(X_pred)
        if len(surv_funcs) == 0:
            return None
        
        surv_func = surv_funcs[0]
        current_time = float(latest_interval.get('current_time_elapsed', 0))
        
        # Buscar punto de umbral
        time_points = np.linspace(current_time, current_time + max_time, 500)
        
        for time_point in time_points:
            survival_prob = np.interp(time_point, surv_func.x, surv_func.y,
                                    left=1.0, right=surv_func.y[-1])
            risk = 1 - survival_prob
            if risk >= risk_threshold:
                time_to_threshold = time_point - current_time
                return {
                    'time_to_threshold': time_to_threshold,
                    'risk': risk,
                    'current_time': current_time
                }
        
        final_risk = 1 - np.interp(current_time + max_time, surv_func.x, surv_func.y,
                                  left=1.0, right=surv_func.y[-1])
        return {
            'time_to_threshold': max_time,
            'risk': final_risk,
            'current_time': current_time
        }
    
    def get_survival_curve(self, intervals: pd.DataFrame, device: str,
                          max_time: int = 5000, n_points: int = 500) -> Optional[List[dict]]:
        """
        Obtiene curva de supervivencia para un dispositivo
        
        Args:
            intervals: DataFrame con intervalos
            device: Nombre del dispositivo
            max_time: Tiempo máximo
            n_points: Número de puntos en la curva
        
        Returns:
            Lista de puntos {tiempo_dias, riesgo_porcentaje}
        """
        if self.model is None:
            return None
        
        device_intervals = intervals[intervals['unit'] == device]
        if len(device_intervals) == 0:
            return None
        
        latest_interval = device_intervals.iloc[-1]
        feature_values = [float(latest_interval.get(f, 0)) for f in self.features]
        X_pred = pd.DataFrame([feature_values], columns=self.features)
        
        surv_func = self.model.predict_survival_function(X_pred)[0]
        current_time = float(latest_interval.get('current_time_elapsed', 0))
        
        plot_times = np.linspace(0, max_time, n_points)
        adjusted_times = plot_times + current_time
        survival_probs = np.interp(adjusted_times, surv_func.x, surv_func.y,
                                  left=1.0, right=surv_func.y[-1])
        failure_risk = (1 - survival_probs) * 100
        
        return [
            {'tiempo_dias': float(t / 24.0), 'riesgo_porcentaje': float(r)}
            for t, r in zip(plot_times, failure_risk)
        ]


# Singleton
_ml_service = None


def get_ml_service() -> MLService:
    """Obtiene instancia singleton del servicio ML"""
    global _ml_service
    if _ml_service is None:
        _ml_service = MLService()
    return _ml_service