from typing import Optional, Dict
from app.auth.jwt_handler import get_password_hash
from app.models.schemas import UserInfo


class UserDatabase:
    """
    Base de datos de usuarios en memoria
    En producción, esto debería ser reemplazado por una base de datos real
    """
    
    # Usuarios con contraseñas hasheadas
    _users: Dict[str, dict] = {
        "admin": {
            "username": "admin",
            "hashed_password": get_password_hash("admin123!"),
            "name": "",
            "role": "Administrador",
            "cliente": "Todos los clientes"
        },
        "EAFIT": {
            "username": "EAFIT",
            "hashed_password": get_password_hash("EAFIT1!"),
            "name": "EAFIT",
            "role": "Operador",
            "cliente": "UNIVERSIDAD EAFIT"
        },
        "UNICAUCA": {
            "username": "UNICAUCA",
            "hashed_password": get_password_hash("UCA1!"),
            "name": "UNICAUCA",
            "role": "Operador",
            "cliente": "UNIVERSIDAD DEL CAUCA"
        }
    }
    
    @classmethod
    def get_user(cls, username: str) -> Optional[dict]:
        """Obtiene un usuario por username"""
        return cls._users.get(username)
    
    @classmethod
    def get_user_info(cls, username: str) -> Optional[UserInfo]:
        """Obtiene información pública del usuario"""
        user = cls._users.get(username)
        if user:
            return UserInfo(
                username=user["username"],
                name=user["name"],
                role=user["role"],
                cliente=user["cliente"]
            )
        return None
    
    @classmethod
    def authenticate_user(cls, username: str, password: str) -> Optional[dict]:
        """
        Autentica un usuario
        
        Args:
            username: Nombre de usuario
            password: Contraseña en texto plano
        
        Returns:
            Usuario si las credenciales son correctas, None en caso contrario
        """
        from app.auth.jwt_handler import verify_password
        
        user = cls.get_user(username)
        if not user:
            return None
        
        if not verify_password(password, user["hashed_password"]):
            return None
        
        return user
    
    @classmethod
    def user_has_access_to_client(cls, username: str, cliente: str) -> bool:
        """
        Verifica si un usuario tiene acceso a datos de un cliente específico
        
        Args:
            username: Nombre de usuario
            cliente: Nombre del cliente
        
        Returns:
            True si tiene acceso, False en caso contrario
        """
        user = cls.get_user(username)
        if not user:
            return False
        
        # Admin tiene acceso a todo
        if user["role"] == "Administrador":
            return True
        
        # Operadores solo tienen acceso a su cliente
        return user["cliente"].lower() in cliente.lower()


# Instancia singleton
user_db = UserDatabase()