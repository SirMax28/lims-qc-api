from fastapi import APIRouter, Depends, status, Query
from typing import List
from models.user import UserCreate, UserResponse
from services.user_service import UserService
from repositories.user_repository import UserRepository
from core.database import db
from utils.auth_manager import get_current_user_id, require_role
from exceptions import ErrorResponse

router = APIRouter()

def get_user_service() -> UserService:
    """
    Crea una instancia del servicio de usuarios.
    FastAPI llamará esta función automáticamente cuando se necesite.
    """
    # Obtenemos la colección 'users' de MongoDB
    collection = db.mongo.db["users"]
    user_repo = UserRepository(collection)
    return UserService(user_repo)

@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo usuario",
    description="Crea un nuevo usuario en el sistema con el rol especificado",
    responses={
        201: {"description": "Usuario creado exitosamente"},
        409: {"model": ErrorResponse, "description": "El email ya está registrado"},
    }
)
async def create_user(
    user_data: UserCreate,
    service: UserService = Depends(get_user_service)
):
    """
    Crea un nuevo usuario.
    
    - **email**: Email único del usuario
    - **full_name**: Nombre completo
    - **password**: Contraseña (mínimo 8 caracteres)
    - **role**: Rol del usuario (admin, quality, technician, auditor, viewer)
    """
    return await service.create_user(user_data)

@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="Listar usuarios",
    description="Obtiene la lista de todos los usuarios (requiere autenticación)",
    dependencies=[Depends(get_current_user_id)]
)
async def get_users(
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"),
    service: UserService = Depends(get_user_service),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Lista todos los usuarios del sistema con paginación.
    Requiere estar autenticado.
    """
    return await service.get_all_users(skip, limit)

@router.get(
    "/users/me",
    response_model=UserResponse,
    summary="Obtener usuario actual",
    description="Obtiene la información del usuario autenticado actualmente"
)
async def get_current_user(
    current_user_id: str = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service)
):
    """
    Devuelve la información del usuario que está actualmente autenticado.
    """
    return await service.get_user_by_id(current_user_id)

@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Obtener usuario por ID",
    description="Obtiene un usuario específico por su ID (requiere autenticación)"
)
async def get_user_by_id(
    user_id: str,
    service: UserService = Depends(get_user_service),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Obtiene un usuario por su ID.
    Requiere estar autenticado.
    """
    return await service.get_user_by_id(user_id)