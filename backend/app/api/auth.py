from fastapi import APIRouter, Depends, HTTPException, status
from app.models.schemas import UserLogin, Token, UserInfo, TokenData
from app.auth.users import user_db
from app.auth.jwt_handler import create_access_token, get_current_active_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """
    Endpoint de autenticación
    
    Args:
        credentials: Username y password
    
    Returns:
        Token JWT de acceso
    """
    user = user_db.authenticate_user(credentials.username, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user["username"]})
    
    return Token(access_token=access_token)


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(current_user: TokenData = Depends(get_current_active_user)):
    """
    Obtiene información del usuario actual
    
    Args:
        current_user: Usuario actual desde el token JWT
    
    Returns:
        Información del usuario
    """
    user_info = user_db.get_user_info(current_user.username)
    
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    return user_info


@router.post("/validate")
async def validate_token(current_user: TokenData = Depends(get_current_active_user)):
    """
    Valida si un token es válido
    
    Returns:
        Mensaje de validación exitosa
    """
    return {
        "valid": True,
        "username": current_user.username,
        "message": "Token válido"
    }