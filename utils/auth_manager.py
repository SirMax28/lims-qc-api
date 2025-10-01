from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from core.config import settings
from models.user import TokenData

# OAuth2PasswordBearer: maneja el token en el header "Authorization: Bearer <token>"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un token JWT.
    
    Args:
        data: Diccionario con los datos a incluir en el token (ej: {"sub": user_id})
        expires_delta: Tiempo de expiración personalizado
        
    Returns:
        Token JWT como string
    """
    to_encode = data.copy()
    
    # Calculamos cuando expira el token
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Agregamos la fecha de expiración al token
    to_encode.update({"exp": expire})
    
    # Creamos el token usando nuestra clave secreta
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> TokenData:
    """
    Verifica y decodifica un token JWT.
    
    Args:
        token: El token JWT a verificar
        
    Returns:
        TokenData con la información del usuario
        
    Raises:
        HTTPException si el token es inválido
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decodificamos el token
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")  # "sub" contiene el ID del usuario
        role: str = payload.get("role")
        
        if user_id is None:
            raise credentials_exception
            
        return TokenData(user_id=user_id, role=role)
    except JWTError:
        raise credentials_exception

async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    """
    Dependencia de FastAPI que extrae el ID del usuario actual desde el token.
    Se usa en endpoints protegidos: 
        async def my_endpoint(current_user_id: str = Depends(get_current_user_id))
    """
    token_data = verify_token(token)
    return token_data.user_id

def require_role(allowed_roles: list[str]):
    """
    Decorador para restringir acceso por roles.

    Uso:
        @app.get("/admin-only", dependencies=[Depends(require_role(["admin"]))])
            ...
    """
    async def role_checker(token: str = Depends(oauth2_scheme)):
        token_data = verify_token(token)
        if token_data.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere uno de estos roles: {', '.join(allowed_roles)}"
            )
        return token_data
    return role_checker