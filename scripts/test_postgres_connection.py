#!/usr/bin/env python3
"""
Script de verificación de conexión a PostgreSQL
Prueba la conexión con las credenciales configuradas
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Colores para terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header():
    """Imprime encabezado del script"""
    print("=" * 80)
    print(f"{BLUE}PostgreSQL Connection Test{RESET}")
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

def load_env_file(env_path):
    """Carga archivo .env"""
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print_success(f"Archivo .env cargado desde: {env_path}")
        return True
    else:
        print_error(f"Archivo .env no encontrado en: {env_path}")
        return False

def get_postgres_config():
    """Obtiene configuración de PostgreSQL desde variables de entorno"""
    config = {
        'host': os.getenv('POSTGRES_HOST', '127.0.0.1'),
        'port': int(os.getenv('POSTGRES_PORT', 5432)),
        'database': os.getenv('POSTGRES_DB', 'eficiencia_energetica'),
        'user': os.getenv('POSTGRES_USER', 'api_crud_monitoreo_sedes_telemetria'),
        'password': os.getenv('POSTGRES_PASSWORD', '')
    }
    
    print_info("Configuración de PostgreSQL:")
    print(f"  Host: {config['host']}")
    print(f"  Port: {config['port']}")
    print(f"  Database: {config['database']}")
    print(f"  User: {config['user']}")
    print(f"  Password: {'*' * len(config['password']) if config['password'] else '(no configurada)'}")
    print()
    
    return config

def test_connection(config):
    """Prueba la conexión a PostgreSQL"""
    print_info("Probando conexión a PostgreSQL...")
    
    try:
        # Intentar conexión
        conn = psycopg2.connect(**config)
        print_success("Conexión establecida exitosamente")
        
        # Obtener información del servidor
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print_info(f"Versión de PostgreSQL: {version}")
        
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        print_error(f"Error de conexión: {str(e)}")
        print()
        print_warning("Posibles causas:")
        print("  1. PostgreSQL no está corriendo")
        print("  2. Credenciales incorrectas")
        print("  3. Firewall bloqueando el puerto")
        print("  4. Host o puerto incorrectos")
        return False
        
    except Exception as e:
        print_error(f"Error inesperado: {str(e)}")
        return False

def test_table_exists(config):
    """Verifica si la tabla mantenimientos existe"""
    print_info("Verificando tabla 'mantenimientos'...")
    
    try:
        conn = psycopg2.connect(**config)
        
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Verificar si la tabla existe
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'mantenimientos'
                );
            """)
            exists = cursor.fetchone()['exists']
            
            if exists:
                print_success("Tabla 'mantenimientos' existe")
                
                # Obtener count de registros
                cursor.execute("SELECT COUNT(*) as count FROM mantenimientos;")
                count = cursor.fetchone()['count']
                print_info(f"Registros en tabla: {count}")
                
                # Obtener estructura de la tabla
                cursor.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns
                    WHERE table_name = 'mantenimientos'
                    ORDER BY ordinal_position;
                """)
                columns = cursor.fetchall()
                
                print_info("Estructura de la tabla:")
                for col in columns:
                    print(f"  - {col['column_name']}: {col['data_type']}")
                
                return True
            else:
                print_warning("Tabla 'mantenimientos' NO existe")
                print()
                print_info("Ejecuta el script de inicialización:")
                print("  psql -h 127.0.0.1 -p 5432 -U api_crud_monitoreo_equipos -d eficiencia_energetica")
                print("  \\i database/init_mantenimientos.sql")
                return False
        
        conn.close()
        
    except Exception as e:
        print_error(f"Error verificando tabla: {str(e)}")
        return False

def test_insert_permission(config):
    """Verifica permisos de escritura"""
    print_info("Verificando permisos de escritura...")
    
    try:
        conn = psycopg2.connect(**config)
        conn.autocommit = False
        
        with conn.cursor() as cursor:
            # Intentar insertar un registro de prueba
            cursor.execute("""
                INSERT INTO mantenimientos (serial, hora_salida, cliente, marca, modelo)
                VALUES ('TEST_SERIAL', NOW(), 'TEST_CLIENTE', 'TEST_MARCA', 'TEST_MODELO')
                RETURNING id;
            """)
            test_id = cursor.fetchone()[0]
            
            # Eliminar registro de prueba
            cursor.execute("DELETE FROM mantenimientos WHERE id = %s;", (test_id,))
            
            # Rollback para no afectar datos reales
            conn.rollback()
            
            print_success("Permisos de escritura verificados correctamente")
            return True
        
    except psycopg2.Error as e:
        conn.rollback()
        print_warning(f"Permisos limitados: {str(e)}")
        print_info("El usuario puede tener permisos de solo lectura")
        return False
        
    except Exception as e:
        print_error(f"Error verificando permisos: {str(e)}")
        return False
    finally:
        conn.close()

def generate_connection_command(config):
    """Genera comando de conexión"""
    print()
    print_info("Comando para conectar manualmente:")
    cmd = f"psql -h {config['host']} -p {config['port']} -U {config['user']} -d {config['database']}"
    print(f"  {cmd}")
    print()

def main():
    """Función principal"""
    print_header()
    
    # Determinar qué archivo .env cargar
    if len(sys.argv) > 1:
        env_path = sys.argv[1]
    else:
        # Intentar detectar automáticamente
        if os.path.exists('crm-sync-api/.env'):
            env_path = 'crm-sync-api/.env'
        elif os.path.exists('backend/.env'):
            env_path = 'backend/.env'
        elif os.path.exists('.env'):
            env_path = '.env'
        else:
            print_error("No se encontró archivo .env")
            print_info("Uso: python test_postgres_connection.py [ruta_al_.env]")
            return False
    
    # Cargar variables de entorno
    if not load_env_file(env_path):
        return False
    
    print()
    
    # Obtener configuración
    config = get_postgres_config()
    
    # Validar que la contraseña esté configurada
    if not config['password']:
        print_error("POSTGRES_PASSWORD no está configurada en el archivo .env")
        return False
    
    # Ejecutar pruebas
    tests_passed = 0
    tests_total = 4
    
    print("=" * 80)
    print(f"{BLUE}Ejecutando pruebas...{RESET}")
    print("=" * 80)
    print()
    
    # Test 1: Conexión básica
    if test_connection(config):
        tests_passed += 1
    print()
    
    # Test 2: Verificar tabla existe
    if test_table_exists(config):
        tests_passed += 1
    print()
    
    # Test 3: Verificar permisos de escritura
    if test_insert_permission(config):
        tests_passed += 1
    print()
    
    # Test 4: Generar comando de conexión
    generate_connection_command(config)
    tests_passed += 1
    
    # Resumen
    print("=" * 80)
    print(f"{BLUE}Resumen de Pruebas{RESET}")
    print("=" * 80)
    print(f"Pruebas exitosas: {tests_passed}/{tests_total}")
    print()
    
    if tests_passed == tests_total:
        print_success("¡Todas las pruebas pasaron! La conexión está lista para usar.")
        return True
    elif tests_passed >= 2:
        print_warning("Algunas pruebas fallaron, pero la conexión básica funciona.")
        return True
    else:
        print_error("Las pruebas fallaron. Revisa la configuración.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)