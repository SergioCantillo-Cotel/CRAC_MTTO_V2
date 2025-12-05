#!/usr/bin/env python3
"""
Script de verificación de conexión al API de Mantenimientos
Prueba la conexión y funcionalidad básica del API REST externo
"""

import sys
import requests
from datetime import datetime

# Colores para terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

# Configuración del API
API_BASE_URL = "https://api-bd-eficiencia-energetica-853514779938.us-central1.run.app"
BEARER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYXBpX2NydWRfbW9uaXRvcmVvX2VxdWlwb3MiLCJleHAiOjE3NTEzMzQ3MjAwfQ.k17feSqkWCD8lmddcPRMvYcjogxdvcdKOHrXhRElm04"

HEADERS = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Accept-Profile": "monitoreo_equipos",  # Especificar esquema PostgREST
    "Content-Profile": "monitoreo_equipos"
}


def print_header():
    """Imprime encabezado del script"""
    print("=" * 80)
    print(f"{BLUE}API de Mantenimientos - Test de Conexión{RESET}")
    print("=" * 80)
    print()


def print_success(message):
    """Imprime mensaje de éxito"""
    print(f"{GREEN}✅ {message}{RESET}")


def print_error(message):
    """Imprime mensaje de error"""
    print(f"{RED}❌ {message}{RESET}")


def print_warning(message):
    """Imprime mensaje de advertencia"""
    print(f"{YELLOW}⚠️  {message}{RESET}")


def print_info(message):
    """Imprime mensaje informativo"""
    print(f"{BLUE}ℹ️  {message}{RESET}")


def test_basic_connection():
    """Prueba conexión básica al API"""
    print_info("Test 1: Conexión básica al API...")
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/mantenimientos",
            headers=HEADERS,
            params={'limit': 1},
            timeout=10
        )
        
        if response.status_code == 200:
            print_success("Conexión exitosa al API")
            return True
        elif response.status_code == 401:
            print_error("Error de autenticación - Token inválido o expirado")
            return False
        else:
            print_error(f"Error en respuesta: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print_error("Timeout - El API no responde en tiempo")
        return False
    except requests.exceptions.ConnectionError:
        print_error("Error de conexión - No se puede alcanzar el API")
        return False
    except Exception as e:
        print_error(f"Error inesperado: {str(e)}")
        return False


def test_query_by_serial():
    """Prueba consulta por serial específico"""
    print_info("Test 2: Consulta por serial...")
    
    test_serial = "JK1142005099"  # Serial conocido de prueba
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/mantenimientos",
            headers=HEADERS,
            params={'serial': f'eq.{test_serial}'},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, list):
                mantenimientos = data
            elif isinstance(data, dict) and 'data' in data:
                mantenimientos = data['data']
            else:
                print_warning(f"Formato de respuesta inesperado: {type(data)}")
                return False
            
            print_success(f"Consulta exitosa - Encontrados {len(mantenimientos)} registros para serial {test_serial}")
            
            if mantenimientos:
                print_info("Ejemplo de registro:")
                record = mantenimientos[0]
                print(f"  Serial: {record.get('serial', 'N/A')}")
                print(f"  Cliente: {record.get('customer_name', 'N/A')}")
                print(f"  Marca: {record.get('device_brand', 'N/A')}")
                print(f"  Modelo: {record.get('device_model', 'N/A')}")
                print(f"  Fecha: {record.get('datetime_maintenance_end', 'N/A')}")
            
            return True
        else:
            print_error(f"Error en consulta: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Error en consulta: {str(e)}")
        return False


def test_query_multiple_serials():
    """Prueba consulta con múltiples seriales"""
    print_info("Test 3: Consulta con múltiples seriales...")
    
    test_serials = ["JK1142005099", "JK2117000712", "JK2117000986"]
    serials_str = ','.join(test_serials)
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/mantenimientos",
            headers=HEADERS,
            params={'serial': f'in.({serials_str})'},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, list):
                mantenimientos = data
            elif isinstance(data, dict) and 'data' in data:
                mantenimientos = data['data']
            else:
                mantenimientos = []
            
            print_success(f"Consulta exitosa - Encontrados {len(mantenimientos)} registros para {len(test_serials)} seriales")
            
            # Contar por serial
            if mantenimientos:
                from collections import Counter
                serial_counts = Counter([m.get('serial') for m in mantenimientos])
                print_info("Distribución por serial:")
                for serial, count in serial_counts.items():
                    print(f"  {serial}: {count} registros")
            
            return True
        else:
            print_error(f"Error en consulta: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Error en consulta: {str(e)}")
        return False


def test_token_expiration():
    """Verifica la fecha de expiración del token"""
    print_info("Test 4: Verificación de expiración del token...")
    
    import json
    import base64
    
    try:
        # Decodificar payload del JWT (segunda parte)
        parts = BEARER_TOKEN.split('.')
        if len(parts) != 3:
            print_error("Token JWT inválido - formato incorrecto")
            return False
        
        # Agregar padding si es necesario
        payload = parts[1]
        payload += '=' * (4 - len(payload) % 4)
        
        decoded = base64.b64decode(payload)
        payload_data = json.loads(decoded)
        
        # Obtener fecha de expiración
        exp_timestamp = payload_data.get('exp')
        if exp_timestamp:
            exp_date = datetime.fromtimestamp(exp_timestamp)
            now = datetime.now()
            
            if now > exp_date:
                print_error(f"Token EXPIRADO desde: {exp_date.strftime('%Y-%m-%d %H:%M:%S')}")
                print_warning("Necesitas solicitar un nuevo token")
                return False
            else:
                days_left = (exp_date - now).days
                print_success(f"Token válido hasta: {exp_date.strftime('%Y-%m-%d %H:%M:%S')}")
                print_info(f"Días restantes: {days_left}")
                
                if days_left < 7:
                    print_warning(f"Token expira pronto - Considera renovarlo")
                
                return True
        else:
            print_warning("No se pudo determinar fecha de expiración")
            return True
            
    except Exception as e:
        print_warning(f"No se pudo verificar expiración: {str(e)}")
        return True


def test_response_format():
    """Verifica el formato de respuesta esperado"""
    print_info("Test 5: Verificación de formato de respuesta...")
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/mantenimientos",
            headers=HEADERS,
            params={'limit': 1},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, list):
                mantenimientos = data
            elif isinstance(data, dict) and 'data' in data:
                mantenimientos = data['data']
            else:
                print_error("Formato de respuesta no reconocido")
                return False
            
            if mantenimientos:
                record = mantenimientos[0]
                required_fields = ['serial', 'datetime_maintenance_end', 'customer_name', 
                                 'device_brand', 'device_model']
                
                missing_fields = [field for field in required_fields if field not in record]
                
                if missing_fields:
                    print_warning(f"Campos faltantes: {', '.join(missing_fields)}")
                else:
                    print_success("Formato de respuesta correcto - Todos los campos presentes")
                
                print_info("Campos disponibles:")
                for key in record.keys():
                    print(f"  - {key}")
                
                return len(missing_fields) == 0
            else:
                print_warning("No hay registros para verificar formato")
                return True
                
        else:
            print_error(f"Error obteniendo datos: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Error verificando formato: {str(e)}")
        return False


def main():
    """Función principal"""
    print_header()
    
    print_info("Configuración:")
    print(f"  URL Base: {API_BASE_URL}")
    print(f"  Token: {'*' * 20}...{BEARER_TOKEN[-10:]}")
    print()
    
    # Ejecutar tests
    tests = [
        ("Conexión básica", test_basic_connection),
        ("Consulta por serial", test_query_by_serial),
        ("Consulta múltiples seriales", test_query_multiple_serials),
        ("Expiración de token", test_token_expiration),
        ("Formato de respuesta", test_response_format)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            print()
        except Exception as e:
            print_error(f"Error ejecutando test '{test_name}': {str(e)}")
            results.append((test_name, False))
            print()
    
    # Resumen
    print("=" * 80)
    print(f"{BLUE}Resumen de Tests{RESET}")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{GREEN}✅ PASSED{RESET}" if result else f"{RED}❌ FAILED{RESET}"
        print(f"{status} - {test_name}")
    
    print()
    print(f"Total: {passed}/{total} tests pasaron")
    
    if passed == total:
        print()
        print_success("¡Todos los tests pasaron! El API está listo para usar.")
        return True
    elif passed >= 3:
        print()
        print_warning("Algunos tests fallaron, pero la funcionalidad básica funciona.")
        return True
    else:
        print()
        print_error("Múltiples tests fallaron. Revisa la configuración.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)