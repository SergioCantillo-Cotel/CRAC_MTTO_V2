import streamlit as st
import pandas as pd
import re
from datetime import datetime


def clean_device_name(device_name: str) -> str:
    """
    Elimina la parte del IP entre paréntesis del nombre del dispositivo
    
    Args:
        device_name: Nombre del dispositivo con IP
    
    Returns:
        Nombre limpio sin IP
    
    Example:
        "FANALCA-Aire APC 1 (172.19.1.46)" -> "FANALCA-Aire APC 1"
    """
    if pd.isna(device_name) or not isinstance(device_name, str):
        return device_name
    
    cleaned_name = re.sub(r'\s*\([^)]*\)$', '', device_name).strip()
    return cleaned_name


def hours_to_days_hours(hours) -> str:
    """
    Convierte horas a formato días y horas
    
    Args:
        hours: Número de horas
    
    Returns:
        String formateado (ej: "2d 5h", "12h", "N/A")
    """
    if pd.isna(hours) or hours is None or hours < 0:
        return "N/A"
    
    try:
        days = int(hours // 24)
        remaining_hours = int(round(hours % 24))
        
        if days == 0:
            return f"{remaining_hours}h"
        elif remaining_hours == 0:
            return f"{days}d"
        else:
            return f"{days}d {remaining_hours}h"
    except (ValueError, TypeError):
        return "N/A"


def format_maintenance_date(date_str: str) -> str:
    """
    Formatea la fecha de mantenimiento de manera amigable
    
    Args:
        date_str: Fecha en formato string o datetime
    
    Returns:
        String formateado de forma amigable
    """
    if pd.isna(date_str) or date_str is None or date_str == "Nunca":
        return "Nunca"
    
    try:
        # Si es string, intentar convertir a datetime
        if isinstance(date_str, str):
            date = pd.to_datetime(date_str)
        else:
            date = date_str
        
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
        return str(date_str)


def format_risk_percentage(risk: float) -> str:
    """
    Formatea el porcentaje de riesgo con color
    
    Args:
        risk: Valor de riesgo (0-100)
    
    Returns:
        HTML formateado con color
    """
    if risk >= 70:
        color = "#ef4444"
        emoji = "🔴"
    elif risk >= 40:
        color = "#f59e0b"
        emoji = "🟠"
    else:
        color = "#22c55e"
        emoji = "🟢"
    
    return f"<span style='color: {color}; font-weight: bold;'>{emoji} {risk:.1f}%</span>"


def format_time_until_threshold(hours: float) -> str:
    """
    Formatea el tiempo hasta umbral con emoji según urgencia
    
    Args:
        hours: Horas hasta alcanzar umbral
    
    Returns:
        String formateado con emoji
    """
    days = hours / 24.0
    time_str = hours_to_days_hours(hours)
    
    if days < 1:
        emoji = "🚨"
    elif days < 7:
        emoji = "⚠️"
    elif days < 30:
        emoji = "⏰"
    else:
        emoji = "✅"
    
    return f"{emoji} {time_str}"


def load_custom_css(file_path: str = "styles/style.css"):
    """
    Carga CSS personalizado desde archivo
    
    Args:
        file_path: Ruta al archivo CSS
    """
    try:
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    css_content = f.read()
                st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
                return
            except UnicodeDecodeError:
                continue
            except FileNotFoundError:
                # Si no existe el archivo, usar CSS por defecto
                load_default_css()
                return
        
        # Si todas las codificaciones fallan
        with open(file_path, 'rb') as f:
            raw_content = f.read()
            css_content = raw_content.decode('utf-8', errors='ignore')
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
            
    except Exception as e:
        print(f"Error cargando CSS: {str(e)}")
        load_default_css()


def load_default_css():
    """Carga CSS por defecto si no existe archivo"""
    default_css = """
    <style>
    body, h1, h2, h3, h4, h5, h6, p, .stDataFrame, .stButton>button, .stMetricValue {
        font-family: 'Manrope' !important;
        color: #FFFFFF;
    }
    
    .block-container {
        padding-top: 1rem !important;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    
    section[data-testid="stSidebar"] > div {
        background-color: #0D2A2B;
    }
    
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: white !important;
    }
    
    .stButton > button {
        background-color: #FFED00 !important;
        color: #000000 !important;
        border: none;
        border-radius: 8px;
        font-weight: bold;
    }
    
    .stButton > button:hover {
        background-color: #E6D600 !important;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #113738 !important;
        color: white !important;
        border-radius: 10px 10px 0 0;
    }
    
    .stTabs [data-baseweb="tab-panel"] {
        background-color: #113738;
        padding: 30px;
        border-radius: 0 0 10px 10px;
    }
    </style>
    """
    st.markdown(default_css, unsafe_allow_html=True)


def format_number(number: float, decimals: int = 1) -> str:
    """
    Formatea un número con separadores de miles y decimales
    
    Args:
        number: Número a formatear
        decimals: Número de decimales
    
    Returns:
        String formateado
    """
    if pd.isna(number):
        return "N/A"
    
    try:
        return f"{number:,.{decimals}f}"
    except:
        return str(number)


def get_risk_category(dias_hasta_umbral: float) -> tuple:
    """
    Obtiene categoría y configuración de color según días hasta umbral
    
    Args:
        dias_hasta_umbral: Días hasta alcanzar umbral de riesgo
    
    Returns:
        Tuple (categoria, color_config)
    """
    if dias_hasta_umbral < 7:
        return 'critico', {'bg': '#fef2f2', 'border': '#ef4444', 'text': '#dc2626', 'icon': '🚨'}
    elif dias_hasta_umbral < 30:
        return 'alto', {'bg': '#fffbeb', 'border': '#f59e0b', 'text': '#d97706', 'icon': '⚠️'}
    elif dias_hasta_umbral < 90:
        return 'medio', {'bg': '#fef9c3', 'border': '#eab308', 'text': '#ca8a04', 'icon': '⏰'}
    else:
        return 'bajo', {'bg': '#f0f9ff', 'border': '#22c55e', 'text': '#16a34a', 'icon': '✅'}