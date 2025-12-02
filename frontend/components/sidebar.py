import streamlit as st
from typing import Tuple, List, Optional
import re


def clean_device_name(device_name: str) -> str:
    """Elimina IP del nombre del dispositivo"""
    if not isinstance(device_name, str):
        return device_name
    return re.sub(r'\s*\([^)]*\)$', '', device_name).strip()


def render_sidebar_login(api_client):
    """Renderiza el formulario de login en el sidebar"""
    st.sidebar.markdown('### 🔐 Inicia sesión')
    st.sidebar.markdown('Accede a tus dashboards, alertas y reportes.')
    
    with st.sidebar.form("sidebar_login_form"):
        username = st.text_input(
            "👤 **Usuario**",
            placeholder="Ingresa tu usuario",
            key="input-user"
        )
        password = st.text_input(
            "🔒 **Contraseña**",
            type="password",
            placeholder="Ingresa tu contraseña",
            key='input-pass'
        )
        
        submit = st.form_submit_button(
            "**Ingresar**",
            use_container_width=True,
            key="login_btn"
        )
        
        if submit:
            if username and password:
                with st.spinner("🔐 Autenticando..."):
                    if api_client.login(username, password):
                        # Obtener información del usuario
                        user_info = api_client.get_current_user()
                        if user_info:
                            st.session_state.authenticated = True
                            st.session_state.user_info = user_info
                            st.toast("✅ Login exitoso")
                            st.rerun()
                        else:
                            st.toast("❌ Error obteniendo información del usuario")
                    else:
                        st.toast("❌ Usuario o contraseña incorrectos")
            else:
                st.toast("⚠️ Por favor ingrese usuario y contraseña")


def render_sidebar_user_info(api_client):
    """Renderiza la información del usuario en el sidebar"""
    if st.session_state.authenticated and st.session_state.user_info:
        user_info = st.session_state.user_info
        
        with st.sidebar.expander(
            f"👋 Hola, **{st.session_state.user_info.get('username', 'Usuario')}**",
            expanded=False
        ):
            st.markdown(f"**🎯 Rol:** {user_info.get('role', 'N/A')}")
            st.markdown(f"**🏢 Cliente:** {user_info.get('cliente', 'N/A')}")
            
            if st.button(
                "🚪 **Cerrar Sesión**",
                use_container_width=True,
                key="logout_btn"
            ):
                st.session_state.authenticated = False
                st.session_state.token = None
                st.session_state.user_info = None
                st.toast("✅ Sesión cerrada exitosamente")
                st.rerun()


def render_control_panel(container, api_client) -> Tuple[float, Optional[List[str]]]:
    """
    Renderiza el panel de control con filtros
    
    Args:
        container: Contenedor de Streamlit
        api_client: Cliente de API
    
    Returns:
        Tuple (risk_threshold, device_filter)
    """
    # Slider de umbral de riesgo
    risk_threshold_decimal = container.slider(
        "⚠️ Umbral de riesgo (%)",
        min_value=1.0,
        max_value=100.0,
        value=80.0,
        step=0.1,
        format="%.1f%%",
        help="Probabilidad de falla a monitorear (80% = alto riesgo)"
    ) / 100
    
    # Obtener lista de dispositivos
    with st.spinner("Cargando dispositivos..."):
        devices = api_client.get_devices_list()
    
    if not devices:
        container.warning("⚠️ No se pudieron cargar los dispositivos")
        return risk_threshold_decimal, None
    
    # Limpiar nombres de dispositivos
    clean_device_names = sorted([clean_device_name(device) for device in devices])
    device_mapping = {clean_device_name(device): device for device in devices}
    
    # Multiselect de dispositivos
    device_filter_clean = container.multiselect(
        "🔍 Filtrar Equipos",
        options=clean_device_names,
        default=[],
        help="Vacío = todos los Equipos"
    )
    
    # Mapear de vuelta a nombres originales
    device_filter = [device_mapping[clean_name] for clean_name in device_filter_clean] if device_filter_clean else None
    
    return risk_threshold_decimal, device_filter