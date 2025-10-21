from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from models.user import UserLogin, Token
from services.user_service import UserService
from repositories.user_repository import UserRepository
from core.database import db
from exceptions import ErrorResponse

router = APIRouter()


def get_user_service() -> UserService:
    """
    Crea una instancia del servicio de usuarios.
    """
    # Obtenemos la colección 'users' de MongoDB
    collection = db.mongo.db["users"]
    user_repo = UserRepository(collection)
    return UserService(user_repo)


@router.post(
    "/auth/login",
    response_model=Token,
    summary="Login de usuario",
    description="Autentica un usuario y devuelve un token JWT",
    responses={
        200: {"description": "Login exitoso, token JWT devuelto"},
        401: {
            "model": ErrorResponse,
            "description": "Credenciales incorrectas o usuario desactivado",
        },
    },
)
async def login(
    login_data: UserLogin, service: UserService = Depends(get_user_service)
):
    """
    Autentica un usuario con email y contraseña.

    Devuelve un token JWT que debe incluirse en el header Authorization
    de las peticiones subsiguientes como: `Authorization: Bearer <token>`

    - **email**: Email del usuario
    - **password**: Contraseña del usuario
    """
    return await service.authenticate_user(login_data)


@router.post("/auth/token", response_model=Token, include_in_schema=False)
async def login_oauth(
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: UserService = Depends(get_user_service),
):
    """
    Endpoint compatible con el flujo OAuth2 para que funcione el botón "Authorize" en Swagger.
    El campo 'username' del formulario acepta email O username del usuario.
    """
    login_data = UserLogin(
        username_or_email=form_data.username, password=form_data.password
    )
    return await service.authenticate_user(login_data)
