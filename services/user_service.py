from typing import List
from datetime import datetime
from models.user import User, UserCreate, UserLogin, Token, UserResponse
from repositories.user_repository import UserRepository
from utils.hash_and_verify_password import hash_password, verify_password
from utils.auth_manager import create_access_token
from exceptions import ConflictException, NotFoundException, UnauthorizedException

class UserService:
    """
    Servicio que contiene la lógica de negocio para usuarios.
    """
    
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
    
    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """
        Crea un nuevo usuario después de validar y hashear la contraseña.
        
        Args:
            user_data: Datos del usuario a crear
            
        Returns:
            Usuario creado (sin contraseña)
            
        Raises:
            ConflictException: Si el email ya está registrado
        """
        # Preparamos el documento para MongoDB
        # hasheamos la contraseña
        user_dict = {
            "email": user_data.email,
            "full_name": user_data.full_name,
            "role": user_data.role.value,  # Convertimos el Enum a string
            "hashed_password": await hash_password(user_data.password),  # AWAIT aquí
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": None
        }
        
        # El repositorio solo guarda los datos y maneja duplicados
        user_doc = await self.user_repo.create_with_email_check(user_dict)
        
        # Construimos el modelo User desde el dict
        user = User(**user_doc)
        
        # Convertimos a UserResponse (sin contraseña)
        return UserResponse(
            _id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at
        )
    
    async def authenticate_user(self, login_data: UserLogin) -> Token:
        """
        Autentica un usuario y devuelve un token JWT.
        
        Args:
            login_data: Credenciales de login (email y contraseña)
            
        Returns:
            Token JWT válido
            
        Raises:
            UnauthorizedException: Si las credenciales son incorrectas
        """
        # Buscamos el usuario por email (devuelve dict o None)
        user_doc = await self.user_repo.get_by_email(login_data.email)
        
        # Verificamos que exista el usuario
        if not user_doc:
            raise UnauthorizedException("Email o contraseña incorrectos")
        
        # Construimos el modelo User desde el dict
        user = User(**user_doc)
        
        # Verificamos que esté activo
        if not user.is_active:
            raise UnauthorizedException("Usuario desactivado")
        
        # Verificamos la contraseña con await
        if not await verify_password(login_data.password, user.hashed_password):
            raise UnauthorizedException("Email o contraseña incorrectos")
        
        # Creamos el token JWT con el ID y rol del usuario
        access_token = create_access_token(
            data={"sub": user.id, "role": user.role.value}
        )
        
        return Token(access_token=access_token, token_type="bearer")
    
    async def get_user_by_id(self, user_id: str) -> UserResponse:
        """
        Obtiene un usuario por su ID.
        """
        user_doc = await self.user_repo.get_by_id(user_id)
        
        if not user_doc:
            raise NotFoundException(f"Usuario con ID {user_id} no encontrado")
        
        user = User(**user_doc)
        
        return UserResponse(
            _id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at
        )
    
    async def get_user_by_email(self, email: str) -> UserResponse:
        """
        Obtiene un usuario por su email.
        """
        user_doc = await self.user_repo.get_by_email(email)
        
        if not user_doc:
            raise NotFoundException(f"Usuario con email {email} no encontrado")
        
        user = User(**user_doc)
        
        return UserResponse(
            _id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at
        )
    
    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        """
        Obtiene lista de todos los usuarios con paginación.
        """
        # Usamos el método list() del repository
        users_docs = await self.user_repo.list(skip=skip, limit=limit)
        
        return [
            UserResponse(
                _id=doc["_id"],
                email=doc["email"],
                full_name=doc["full_name"],
                role=doc["role"],
                is_active=doc["is_active"],
                created_at=doc["created_at"]
            )
            for doc in users_docs
        ]