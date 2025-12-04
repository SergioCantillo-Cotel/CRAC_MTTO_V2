"""
Lista de seriales conocidos de equipos CRAC
Estos seriales se utilizan para la sincronización automática con el CRM
"""

# Seriales de equipos CRAC conocidos
KNOWN_SERIALS = [
    # FANALCA
    "JK1142005099",  # FANALCA-Aire APC 1 (172.19.1.46)
    "JK2117000712",  # FANALCA-Aire APC 2 (172.19.1.47)
    "JK2117000986",  # FANALCA-Aire APC 3 (172.19.1.44)
    
    # SPIA
    "SCA131150",     # SPIA-A.A#1 (172.20.196.104)
    "SCA131148",     # SPIA-A.A#2 (172.20.196.105)
    "SCA131149",     # SPIA-A.A#3 (172.20.196.106)
    
    # EAFIT
    "UCV101363",     # EAFIT-Bloque 18-1-Direccion Informatica (10.65.0.13)
    "UCV105388",     # EAFIT-Bloque 18-2-Direccion Informatica (10.65.0.14)
    "JK1821004033",  # EAFIT-Bloque 19-1-Centro de Computo APOLO (10.65.0.15)
    "JK1831002840",  # EAFIT - Bloque 19 - 2- Centro de Computo APOLO (10.65.0.16)
    
    # Metro
    "UK1008210542",  # Metro Talleres - Aire 1 (172.17.205.89)
    "JK16400002252", # Metro Talleres - Aire 2 (172.17.205.93)
    "JK1905003685",  # Metro Talleres - Aire 3 (172.17.205.92)
    "JK1213009088",  # Metro PCC - Aire Rack 4 (172.17.205.104)
    "2016-1091A",    # Metro PCC - Aire Giax 5 (172.17.204.30)
    "2016-1094A",    # Metro PCC - Aire Gfax 8 (172.17.204.33)
    
    # UTP
    "JK2147003126",  # UTP-AIRE 1 Datacenter (10.100.101.85)
    "JK2147003130",  # UTP-AIRE 2 Datacenter (10.100.101.84)
    "JK2230004923",  # UTP-AIRE 3 Datacenter (10.100.101.86)
    
    # UNICAUCA
    "JK1923002790",  # UNICAUCA-AIRE 1-PASILLO A (10.200.100.27)
    "JK1743000230",  # UNICAUCA-AIRE 2-PASILLO B (10.200.100.29)
    "JK1811002605",  # UNICAUCA-AIRE 3-PASILLO A (10.200.100.28)
    "JK1923002792",  # UNICAUCA-AIRE 4-PASILLO B (10.200.100.30)
]

# Mapeo de serial a información del equipo (opcional, para referencia)
SERIAL_INFO = {
    "JK1142005099": {
        "dispositivo": "FANALCA-Aire APC 1",
        "ip": "172.19.1.46",
        "cliente": "FANALCA",
        "ubicacion": "Datacenter Principal"
    },
    "JK2117000712": {
        "dispositivo": "FANALCA-Aire APC 2",
        "ip": "172.19.1.47",
        "cliente": "FANALCA",
        "ubicacion": "Datacenter Principal"
    },
    "JK2117000986": {
        "dispositivo": "FANALCA-Aire APC 3",
        "ip": "172.19.1.44",
        "cliente": "FANALCA",
        "ubicacion": "Datacenter Principal"
    },
    "SCA131150": {
        "dispositivo": "SPIA-A.A#1",
        "ip": "172.20.196.104",
        "cliente": "SPIA",
        "ubicacion": "Sala de Cómputo"
    },
    "SCA131148": {
        "dispositivo": "SPIA-A.A#2",
        "ip": "172.20.196.105",
        "cliente": "SPIA",
        "ubicacion": "Sala de Cómputo"
    },
    "SCA131149": {
        "dispositivo": "SPIA-A.A#3",
        "ip": "172.20.196.106",
        "cliente": "SPIA",
        "ubicacion": "Sala de Cómputo"
    },
    "UCV101363": {
        "dispositivo": "EAFIT-Bloque 18-1",
        "ip": "10.65.0.13",
        "cliente": "UNIVERSIDAD EAFIT",
        "ubicacion": "Dirección Informática"
    },
    "UCV105388": {
        "dispositivo": "EAFIT-Bloque 18-2",
        "ip": "10.65.0.14",
        "cliente": "UNIVERSIDAD EAFIT",
        "ubicacion": "Dirección Informática"
    },
    "JK1821004033": {
        "dispositivo": "EAFIT-Bloque 19-1",
        "ip": "10.65.0.15",
        "cliente": "UNIVERSIDAD EAFIT",
        "ubicacion": "Centro de Cómputo APOLO"
    },
    "JK1831002840": {
        "dispositivo": "EAFIT-Bloque 19-2",
        "ip": "10.65.0.16",
        "cliente": "UNIVERSIDAD EAFIT",
        "ubicacion": "Centro de Cómputo APOLO"
    },
    "UK1008210542": {
        "dispositivo": "Metro Talleres - Aire 1",
        "ip": "172.17.205.89",
        "cliente": "METRO",
        "ubicacion": "Talleres"
    },
    "JK16400002252": {
        "dispositivo": "Metro Talleres - Aire 2",
        "ip": "172.17.205.93",
        "cliente": "METRO",
        "ubicacion": "Talleres"
    },
    "JK1905003685": {
        "dispositivo": "Metro Talleres - Aire 3",
        "ip": "172.17.205.92",
        "cliente": "METRO",
        "ubicacion": "Talleres"
    },
    "JK1213009088": {
        "dispositivo": "Metro PCC - Aire Rack 4",
        "ip": "172.17.205.104",
        "cliente": "METRO",
        "ubicacion": "PCC"
    },
    "2016-1091A": {
        "dispositivo": "Metro PCC - Aire Giax 5",
        "ip": "172.17.204.30",
        "cliente": "METRO",
        "ubicacion": "PCC"
    },
    "2016-1094A": {
        "dispositivo": "Metro PCC - Aire Gfax 8",
        "ip": "172.17.204.33",
        "cliente": "METRO",
        "ubicacion": "PCC"
    },
    "JK2147003126": {
        "dispositivo": "UTP-AIRE 1",
        "ip": "10.100.101.85",
        "cliente": "UTP",
        "ubicacion": "Datacenter"
    },
    "JK2147003130": {
        "dispositivo": "UTP-AIRE 2",
        "ip": "10.100.101.84",
        "cliente": "UTP",
        "ubicacion": "Datacenter"
    },
    "JK2230004923": {
        "dispositivo": "UTP-AIRE 3",
        "ip": "10.100.101.86",
        "cliente": "UTP",
        "ubicacion": "Datacenter"
    },
    "JK1923002790": {
        "dispositivo": "UNICAUCA-AIRE 1",
        "ip": "10.200.100.27",
        "cliente": "UNIVERSIDAD DEL CAUCA",
        "ubicacion": "PASILLO A"
    },
    "JK1743000230": {
        "dispositivo": "UNICAUCA-AIRE 2",
        "ip": "10.200.100.29",
        "cliente": "UNIVERSIDAD DEL CAUCA",
        "ubicacion": "PASILLO B"
    },
    "JK1811002605": {
        "dispositivo": "UNICAUCA-AIRE 3",
        "ip": "10.200.100.28",
        "cliente": "UNIVERSIDAD DEL CAUCA",
        "ubicacion": "PASILLO A"
    },
    "JK1923002792": {
        "dispositivo": "UNICAUCA-AIRE 4",
        "ip": "10.200.100.30",
        "cliente": "UNIVERSIDAD DEL CAUCA",
        "ubicacion": "PASILLO B"
    },
}

def get_serial_info(serial: str) -> dict:
    """
    Obtiene información de un serial
    
    Args:
        serial: Número de serie
    
    Returns:
        Diccionario con información del equipo o vacío si no existe
    """
    return SERIAL_INFO.get(serial, {})


def get_serials_by_cliente(cliente: str) -> list:
    """
    Obtiene lista de seriales por cliente
    
    Args:
        cliente: Nombre del cliente
    
    Returns:
        Lista de seriales del cliente
    """
    return [
        serial for serial, info in SERIAL_INFO.items()
        if cliente.upper() in info.get('cliente', '').upper()
    ]


def is_known_serial(serial: str) -> bool:
    """
    Verifica si un serial está en la lista de seriales conocidos
    
    Args:
        serial: Número de serie
    
    Returns:
        True si el serial es conocido, False en caso contrario
    """
    return serial in KNOWN_SERIALS