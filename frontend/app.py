import streamlit as st
import pandas as pd
from PIL import Image
import streamlit.components.v1 as components

# Importaciones locales
from services.api_client import get_api_client
from components.sidebar import render_sidebar_login, render_sidebar_user_info, render_control_panel
from components.tabs import render_tab1, render_tab2, render_tab3
from utils.formatters import load_custom_css

# Configuración de página
st.set_page_config(
    page_title="Command Center CRAC",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cargar estilos CSS
load_custom_css()

# Configuración pandas
pd.set_option('future.no_silent_downcasting', True)

# Logo
try:
    image = Image.open('img/cotel_small.png')
    st.logo(image, size='large')
except:
    pass

# Título
st.markdown(
    "<h2 style='color: white; margin-top: 10px; margin-bottom: 1rem; line-height: 1.2; padding-bottom: 0;'>"
    "🏢 Command Center - Gestión Predictiva CRAC</h2>",
    unsafe_allow_html=True
)


def init_session_state():
    """Inicializa el estado de la sesión"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'token' not in st.session_state:
        st.session_state.token = None
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None


def render_public_interface():
    """Interfaz pública cuando no hay usuario autenticado"""
    components.html("""
    <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
    .welcome-text {
        background: #113738;
        padding: 30px;
        border-radius: 15px;
        border-left: 6px solid #203a28;
        margin: 20px 0px;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
        font-family: 'Manrope', sans-serif;
        color: white;
    }
    .welcome-text h4 {
        color: white;
        margin-top:0px;
        margin-bottom: 20px;
        font-weight: 700;
        font-size: 1.6rem;
    }
    .welcome-text p {
        color: white;
        margin-bottom: 15px;
        font-size: 1.0rem;
    }
    .welcome-text ul {
        color: white;
        margin-left: 10px;
        line-height: 1.5;
        font-size: 1.0rem;
    }
    .welcome-text li {
        color: white;
        margin-bottom: 12px;
        padding-left: 10px;
    }
    .welcome-text strong {
        color: white;
    }
    </style>
    <div class="welcome-text">
        <h4>¡Bienvenido al Sistema de Monitoreo CRAC!</h4>
        <p>Esta plataforma te permite:</p>
        <ul>
            <li>📊 <strong>Monitorear</strong> el estado de los equipos CRAC</li>
            <li>📈 <strong>Predecir</strong> fallas antes de que ocurran</li>
            <li>🎯 <strong>Optimizar</strong> el mantenimiento preventivo</li>
        </ul>
    </div>
    """, height=500)


def render_authenticated_interface():
    """Interfaz para usuarios autenticados"""
    try:
        api_client = get_api_client()
        
        # Verificar token
        if not api_client.validate_token():
            st.error("Sesión expirada. Por favor inicie sesión nuevamente.")
            st.session_state.authenticated = False
            st.session_state.token = None
            st.rerun()
            return
        
        # Crear tabs
        tab1, tab2, tab3 = st.tabs([
            "📊 Resumen",
            "📈 Proyección de Riesgo",
            "🎯 Recomendaciones de Mantenimiento"
        ])
        
        # Panel de control en sidebar
        container = st.sidebar.expander("Panel de Control", expanded=True, icon="🎛️")
        risk_threshold, device_filter = render_control_panel(container, api_client)
        
        # Renderizar tabs
        with tab1:
            with st.spinner("🔄 Cargando datos de dispositivos..."):
                render_tab1(api_client, risk_threshold, device_filter)
        
        with tab2:
            with st.spinner("📊 Calculando proyecciones de riesgo..."):
                render_tab2(api_client, risk_threshold, device_filter)
        
        with tab3:
            with st.spinner("🎯 Generando recomendaciones de mantenimiento..."):
                render_tab3(api_client, risk_threshold, device_filter)
        
    except Exception as e:
        st.error(f"❌ Error en la aplicación: {str(e)}")


def main():
    """Función principal"""
    # Inicializar sesión
    init_session_state()
    
    # Obtener cliente API
    api_client = get_api_client()
    
    # Renderizar login/user info en sidebar
    if not st.session_state.authenticated:
        render_sidebar_login(api_client)
    else:
        render_sidebar_user_info(api_client)
    
    # Renderizar contenido principal
    if st.session_state.authenticated:
        render_authenticated_interface()
    else:
        render_public_interface()


if __name__ == "__main__":
    main()