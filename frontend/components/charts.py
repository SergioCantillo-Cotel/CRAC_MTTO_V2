import plotly.graph_objects as go
from typing import List, Dict
from utils.formatters import clean_device_name
import plotly.express as px

def create_top_devices_chart(devices: List[dict], risk_threshold: float) -> go.Figure:
    """
    Crea gráfico de barras horizontales con top dispositivos prioritarios
    
    Args:
        devices: Lista de dispositivos con información de riesgo
        risk_threshold: Umbral de riesgo configurado
    
    Returns:
        Figura de Plotly
    """
    fig = go.Figure()
    
    # Invertir orden para mostrar mayor prioridad arriba
    devices = list(reversed(devices))
    
    for device in devices:
        # Determinar color según días hasta umbral
        tiempo_dias = device['tiempo_hasta_umbral_dias']
        if tiempo_dias < 7:
            color = '#ef4444'
        elif tiempo_dias < 30:
            color = '#f59e0b'
        else:
            color = '#22c55e'
        
        device_name = clean_device_name(device['dispositivo'])
        
        # Crear etiqueta con marca y modelo si están disponibles
        if device.get('marca', 'N/A') != 'N/A' and device.get('modelo', 'N/A') != 'N/A':
            device_label = f"{device_name}"
        elif device.get('marca', 'N/A') != 'N/A':
            device_label = f"{device_name} ({device['marca']})"
        else:
            device_label = device_name
        
        fig.add_trace(go.Bar(
            y=[device_label],
            x=[tiempo_dias],
            orientation='h',
            name=device_name,
            marker_color=color,
            showlegend=False,
            hovertemplate=(
                f"<b>{device_name}</b><br>" +
                f"Serial: {device.get('serial', 'N/A')}<br>" +
                f"Marca: {device.get('marca', 'N/A')}<br>" +
                f"Modelo: {device.get('modelo', 'N/A')}<br>" +
                f"Tiempo hasta {int(risk_threshold*100)}% riesgo: {tiempo_dias:.1f} días<br>" +
                f"Riesgo actual: {device['riesgo_actual']:.1f}%<br>" +
                f"Total alarmas: {device.get('total_alarmas', 'N/A')}<extra></extra>"
            )
        ))
    
    fig.update_layout(
        paper_bgcolor='#0D2A2B',
        plot_bgcolor='#0D2A2B',
        height=360,
        title={
            'text': f"🔧 Top {len(devices)} Equipos con Prioridad de Mantenimiento",
            'x': 0.5,
            'font': {'color': "#ffffff", 'family': 'Manrope'},
            'xanchor': 'center',
        },
        xaxis_title="Días hasta umbral de riesgo",
        yaxis_title="Equipos",
        margin=dict(l=30, r=40, t=55, b=30),
        xaxis=dict(
            showline=True,
            linecolor='white',
            showgrid=False,
            zeroline=False,
            title_font=dict(color='white', family='Manrope'),
            tickfont=dict(color='white', family='Manrope')
        ),
        yaxis=dict(
            title_font=dict(color='white', family='Manrope'),
            tickfont=dict(color='white', family='Manrope')
        )
    )
    
    return fig


def create_risk_pie_chart(statistics: Dict) -> go.Figure:
    """
    Crea gráfico de dona con distribución de riesgos
    
    Args:
        statistics: Diccionario con estadísticas de dispositivos
    
    Returns:
        Figura de Plotly
    """
    fig = go.Figure(data=[go.Pie(
        labels=['Crítico', 'Alto', 'Medio', 'Bajo'],
        values=[
            statistics.get('devices_critical', 0),
            statistics.get('devices_high', 0),
            statistics.get('devices_medium', 0),
            statistics.get('devices_low', 0)
        ],
        marker_colors=['#ef4444', '#f59e0b', '#eab308', '#22c55e'],
        hole=.4,
        rotation=90
    )])
    
    fig.update_layout(
        paper_bgcolor='#0D2A2B',
        height=200,
        margin=dict(l=10, r=0, t=30, b=10),
        showlegend=False,
        title_x=0.5,
        title='',
        font=dict(color='white', family='Manrope'),
    )
    
    return fig


def create_risk_curves(predictions: List[dict], risk_threshold: float) -> go.Figure:
    """
    Crea gráfico de curvas de riesgo para múltiples dispositivos
    
    Args:
        predictions: Lista de predicciones con curvas de riesgo
        risk_threshold: Umbral de riesgo configurado
    
    Returns:
        Figura de Plotly
    """
    fig = go.Figure()
    colors = px.colors.qualitative.Plotly
    
    for i, prediction in enumerate(predictions):
        if not prediction.get('curva_riesgo'):
            continue
        
        device_name = clean_device_name(prediction['dispositivo'])
        curve_points = prediction['curva_riesgo']
        
        # Extraer datos de la curva
        tiempos = [point['tiempo_dias'] for point in curve_points]
        riesgos = [point['riesgo_porcentaje'] for point in curve_points]
        
        # Determinar color según riesgo actual
        current_risk = prediction['riesgo_actual']
        if current_risk > 70:
            color = '#ef4444'
        elif current_risk > 40:
            color = '#f59e0b'
        else:
            color = colors[i % len(colors)]
        
        # Línea de curva de riesgo
        fig.add_trace(go.Scatter(
            x=tiempos,
            y=riesgos,
            mode='lines',
            name=device_name,
            line=dict(width=2.5, color=color),
            showlegend=False,
            hovertemplate=(
                f"<b>{device_name}</b><br>" +
                "Días desde ahora: %{x:.1f}<br>" +
                "Riesgo de falla: %{y:.1f}%<extra></extra>"
            )
        ))
        
        # Punto actual
        fig.add_trace(go.Scatter(
            x=[0],
            y=[current_risk],
            mode='markers',
            marker=dict(
                size=12,
                color=color,
                symbol='diamond',
                line=dict(width=2, color='white')
            ),
            showlegend=False,
            name=f"{device_name} - Actual",
            hovertemplate=(
                f"<b>{device_name} - AHORA</b><br>" +
                f"<b>Riesgo actual: {current_risk:.1f}%</b><extra></extra>"
            )
        ))
        
        # Punto de umbral si está disponible
        tiempo_hasta_umbral = prediction.get('tiempo_hasta_umbral')
        if tiempo_hasta_umbral:
            threshold_x_days = tiempo_hasta_umbral / 24.0
            threshold_y = risk_threshold * 100
            
            fig.add_trace(go.Scatter(
                x=[threshold_x_days],
                y=[threshold_y],
                mode='markers',
                marker=dict(
                    size=10,
                    color=color,
                    symbol='x',
                    line=dict(width=2, color='black')
                ),
                showlegend=False,
                name=f"{device_name} - Umbral {int(risk_threshold*100)}%",
                hovertemplate=(
                    f"<b>{device_name}</b><br>" +
                    f"Tiempo hasta {int(risk_threshold*100)}% riesgo: {threshold_x_days:.1f} días<br>" +
                    f"Riesgo: {threshold_y:.1f}%<extra></extra>"
                )
            ))
    
    # Línea horizontal del umbral
    risk_threshold_percent = risk_threshold * 100
    fig.add_hline(
        y=risk_threshold_percent,
        line_dash="dash",
        line_color="red",
    )
    
    fig.update_layout(
        paper_bgcolor='#113738',
        plot_bgcolor='#113738',
        height=270,width=1200,
        xaxis_title="Días desde ahora",
        yaxis_title="Probabilidad de Falla (%)",
        margin=dict(l=10, r=10, t=30, b=0),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5
        ),
        hovermode="closest",
        xaxis=dict(
            range=[0, 220],
            showline=True,
            linecolor='white',
            showgrid=False,
            zeroline=False,
            title_font=dict(color='white', family='Manrope'),
            tickfont=dict(color='white', family='Manrope')
        ),
        yaxis=dict(
            title_font=dict(color='white', family='Manrope'),
            tickfont=dict(color='white', family='Manrope'),
            ticksuffix="%",
            range=[0, 100]
        ),
        font=dict(family='Manrope', color='white')
    )
    
    return fig