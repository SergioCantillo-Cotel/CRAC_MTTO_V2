import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Optional, List
from components.charts import create_top_devices_chart, create_risk_pie_chart, create_risk_curves
from utils.formatters import clean_device_name, hours_to_days_hours, format_maintenance_date


def custom_metric(label: str, value: str, hint: str = "", color: str = "#ffffff", bg_color: str = "#0D2A2B"):
    """Métrica personalizada con hint"""
    html = f"""
    <div style="background-color: {bg_color};padding: 1rem;border-radius: 0.5rem;text-align: center;cursor: help;" title="{hint}">
        <div style="font-size: 14px;color: #ffffff;margin-bottom: 2px;font-weight: 400;">
            {label}
        </div>
        <div style="font-size: 24px;color: {color};font-weight: 500;line-height: 0.8;">
            {value}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_tab1(api_client, risk_threshold: float, device_filter: Optional[List[str]] = None):
    """
    Renderiza Tab 1: Resumen
    
    Args:
        api_client: Cliente de API
        risk_threshold: Umbral de riesgo (0-1)
        device_filter: Filtro opcional de dispositivos
    """
    priority_col, summary_col = st.columns([3, 1])
    
    with priority_col:
        try:
            # Obtener top dispositivos con prioridad
            response = api_client.get_top_priority_devices(
                risk_threshold=risk_threshold,
                top_n=5
            )
            
            if response and response.get('devices'):
                devices = response['devices']
                statistics = response.get('statistics', {})
                
                # Aplicar filtro de dispositivos si existe
                if device_filter:
                    devices = [d for d in devices if d['dispositivo'] in device_filter]
                
                if devices:
                    # Crear gráfico de barras
                    fig = create_top_devices_chart(devices, risk_threshold)
                    cont_top5 = st.container(key='cont-top5')
                    cont_top5.plotly_chart(fig, width='content', config={'displayModeBar': False})
                else:
                    st.info("📊 No hay dispositivos con riesgo identificado para los filtros actuales")
            else:
                st.info("📊 No hay datos de dispositivos disponibles")
                
        except Exception as e:
            st.error(f"❌ Error cargando prioridades: {str(e)}")
    
    with summary_col:
        try:
            # Obtener estadísticas
            response = api_client.get_top_priority_devices(
                risk_threshold=risk_threshold,
                top_n=20  # Obtener todos para estadísticas
            )
            
            if response and response.get('devices'):
                devices = response['devices']
                statistics = response.get('statistics', {})
                
                # Aplicar filtro si existe
                if device_filter:
                    devices = [d for d in devices if d['dispositivo'] in device_filter]
                    # Recalcular estadísticas
                    statistics = calculate_statistics_from_devices(devices)
                
                render_summary_statistics(statistics)
            else:
                st.toast("📊 Esperando datos del modelo")
                
        except Exception as e:
            st.error(f"❌ Error cargando estadísticas: {str(e)}")
    
    render_footer()


def render_tab2(api_client, risk_threshold: float, device_filter: Optional[List[str]] = None):
    """
    Renderiza Tab 2: Proyección de Riesgo
    
    Args:
        api_client: Cliente de API
        risk_threshold: Umbral de riesgo (0-1)
        device_filter: Filtro opcional de dispositivos
    """
    try:
        # Obtener lista de dispositivos
        devices_list = api_client.get_devices_list()
        
        # Aplicar filtro si existe
        if device_filter:
            devices_list = [d for d in devices_list if d in device_filter]
        
        if not devices_list:
            st.info("📊 No hay dispositivos disponibles con los filtros actuales")
            return
        
        # Slider para número de dispositivos
        top_n = st.slider(
            "❄️ Número de equipos a mostrar",
            key="slider_tab2",
            min_value=1,
            max_value=len(devices_list),
            value=min(5, len(devices_list))
        )
        
        # Obtener predicciones batch
        with st.spinner("Calculando proyecciones de riesgo..."):
            predictions = api_client.get_batch_predictions(
                dispositivos=devices_list[:top_n],
                risk_threshold=risk_threshold,
                max_time=5000,
                include_curve=True
            )
        
        if predictions:
            # Crear gráfico de curvas de riesgo
            fig = create_risk_curves(predictions, risk_threshold)
            st.plotly_chart(fig, width='content', config={'displayModeBar': True})
        else:
            st.info("📊 No se pudieron calcular proyecciones para los dispositivos seleccionados")
    
    except Exception as e:
        st.error(f"❌ Error en proyecciones: {str(e)}")
    
    render_footer()


def render_tab3(api_client, risk_threshold: float, device_filter: Optional[List[str]] = None):
    """
    Renderiza Tab 3: Recomendaciones de Mantenimiento
    
    Args:
        api_client: Cliente de API
        risk_threshold: Umbral de riesgo (0-1)
        device_filter: Filtro opcional de dispositivos
    """
    try:
        # Obtener recomendaciones
        with st.spinner("Generando recomendaciones de mantenimiento..."):
            recommendations = api_client.get_maintenance_recommendations(
                risk_threshold=risk_threshold,
                categoria="todos"
            )
        
        if not recommendations:
            st.info("✅ No hay equipos que requieran mantenimiento inmediato")
            return
        
        # Aplicar filtro de dispositivos si existe
        if device_filter:
            recommendations = [r for r in recommendations if r['equipo'] in device_filter]
        
        if not recommendations:
            st.info("✅ No hay equipos que requieran mantenimiento con los filtros actuales")
            return
        
        # Separar por categoría
        critico = [r for r in recommendations if r['categoria'] == 'critico']
        alto = [r for r in recommendations if r['categoria'] == 'alto']
        planificar = [r for r in recommendations if r['categoria'] == 'planificar']
        
        # Renderizar secciones
        if critico:
            render_maintenance_section(critico, "🚨 MANTENIMIENTO INMEDIATO REQUERIDO", "exp-rojo", "critico")
        
        if alto:
            render_maintenance_section(alto, "⚠️ MANTENIMIENTO PRÓXIMO", "exp-amarillo", "alto")
        
        if planificar:
            render_maintenance_section(planificar, "📅 MANTENIMIENTO PLANIFICADO", "exp-azul", "planificar")
    
    except Exception as e:
        st.error(f"❌ Error generando recomendaciones: {str(e)}")
    
    render_footer()


def calculate_statistics_from_devices(devices: List[dict]) -> dict:
    """Calcula estadísticas desde lista de dispositivos"""
    df = pd.DataFrame(devices)
    if df.empty:
        return {
            'total_devices': 0,
            'devices_critical': 0,
            'devices_high': 0,
            'devices_medium': 0,
            'devices_low': 0,
            'average_risk': 0.0
        }
    
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
        'average_risk': float(df['riesgo_actual'].mean())
    }


def render_summary_statistics(statistics: dict):
    """Renderiza estadísticas de resumen"""
    cont_alert = st.container(key='cont-alert')
    
    col1, col2 = cont_alert.columns(2)
    
    with col1:
        custom_metric(
            "🔴 Crítico",
            statistics.get('devices_critical', 0),
            hint="Equipos que requieren atención inmediata"
        )
        custom_metric(
            "🟠 Alto",
            statistics.get('devices_high', 0),
            hint="Equipos que requieren mantenimiento próximamente"
        )
    
    with col2:
        custom_metric(
            "🟡 Medio",
            statistics.get('devices_medium', 0),
            hint="Equipos para planificación a mediano plazo"
        )
        custom_metric(
            "🟢 Bajo",
            statistics.get('devices_low', 0),
            hint="Equipos con bajo riesgo inmediato"
        )
    
    # Gráfico de dona
    if statistics.get('total_devices', 0) > 0:
        fig = create_risk_pie_chart(statistics)
        cont_alert.plotly_chart(fig, width='content', config={'displayModeBar': False})


def render_maintenance_section(recommendations: List[dict], title: str, container_key: str, categoria: str):
    """Renderiza una sección de mantenimiento"""
    with st.container(key=container_key):
        with st.expander(f"{title}: {len(recommendations)} equipo(s)", expanded=True):
            # Crear filas de 2 columnas
            for i in range(0, len(recommendations), 2):
                cols = st.columns(2)
                for j in range(2):
                    if i + j < len(recommendations):
                        with cols[j]:
                            render_device_card(recommendations[i + j], categoria)


def render_device_card(recommendation: dict, categoria: str):
    """Renderiza una tarjeta de dispositivo"""
    # Colores según categoría
    color_config = {
        'critico': {'bg': '#fef2f2', 'border': '#ef4444', 'text': '#dc2626', 'icon': '❄️'},
        'alto': {'bg': '#fffbeb', 'border': '#f59e0b', 'text': '#d97706', 'icon': '❄️'},
        'planificar': {'bg': '#f0f9ff', 'border': '#0ea5e9', 'text': '#0369a1', 'icon': '❄️'}
    }
    
    config = color_config.get(categoria, color_config['planificar'])
    
    device_name = clean_device_name(recommendation['equipo'])
    
    with st.expander(f"{config['icon']} {device_name}", expanded=False):
        # Información principal
        st.markdown(f"""
        <div style='background-color: {config['bg']}; border-left: 5px solid {config['border']}; 
                    padding: 15px; margin: 10px 0; border-radius: 5px;'>
            <p style='margin: 0px 0; font-size: 12px; color:#000000;'>
            <strong>🔢 Serial:</strong> {recommendation['serial']}<br>
            <strong>🏢 Cliente:</strong> {recommendation['cliente']}<br>
            <strong>🏷️ Marca:</strong> {recommendation['marca']}<br>
            <strong>📋 Modelo:</strong> {recommendation['modelo']}<br>
            <strong>🔧 Último mantenimiento:</strong> {recommendation['ultimo_mantenimiento']}<br>
            <strong>⏱️ Tiempo hasta umbral:</strong> {hours_to_days_hours(recommendation['tiempo_hasta_umbral'])}<br>
            <strong>📊 Riesgo actual:</strong> {recommendation['riesgo_actual']:.1f}%
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Expander secundario
        with st.expander("🔍 Análisis Técnico y Recomendaciones", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.text("Fallas Detectadas")
                fallas = recommendation.get('fallas_detectadas', [])
                if fallas:
                    for falla in fallas:
                        st.write(f"• {falla}")
                else:
                    st.info("✅ No se detectaron fallas críticas")
            
            with col2:
                st.text("Acciones Recomendadas")
                recomendaciones = recommendation.get('recomendaciones', [])
                for rec in recomendaciones:
                    st.write(f"• {rec}")


def render_footer():
    """Renderiza el footer con timestamp"""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    st.markdown(
        f"<div style='text-align: center; color: #fff; font-size: 12px; padding: 0px;'>"
        f"Última actualización: {timestamp}"
        f"</div>",
        unsafe_allow_html=True
    )