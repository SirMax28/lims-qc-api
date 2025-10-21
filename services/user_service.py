from typing import List
from datetime import datetime
from models.user import User, UserCreate, UserLogin, UserUpdate, Token, UserResponse
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
            ConflictException: Si el email o username ya están registrados
        """
        # Preparamos el documento para MongoDB
        # hasheamos la contraseña
        user_dict = {
            "email": user_data.email,
            "username": user_data.username,
            "full_name": user_data.full_name,
            "role": user_data.role.value,  # Convertimos el Enum a string
            "hashed_password": await hash_password(user_data.password),  # AWAIT aquí
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": None,
        }

        # El repositorio solo guarda los datos y maneja duplicados
        user_doc = await self.user_repo.create_with_unique_check(user_dict)

        # Construimos el modelo User desde el dict
        user = User(**user_doc)

        # Convertimos a UserResponse (sin contraseña)
        return UserResponse(
            _id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    async def authenticate_user(self, login_data: UserLogin) -> Token:
        """
        Autentica un usuario y devuelve un token JWT.
        Permite login con email O username.

        Args:
            login_data: Credenciales de login (username_or_email y contraseña)

        Returns:
            Token JWT válido

        Raises:
            UnauthorizedException: Si las credenciales son incorrectas
        """
        # Buscamos el usuario por email o username (devuelve dict o None)
        user_doc = await self.user_repo.get_by_username_or_email(
            login_data.username_or_email
        )

        # Verificamos que exista el usuario
        if not user_doc:
            raise UnauthorizedException("Usuario/Email o contraseña incorrectos")

        # Construimos el modelo User desde el dict
        user = User(**user_doc)

        # Verificamos que esté activo
        if not user.is_active:
            raise UnauthorizedException("Usuario desactivado")

        # Verificamos la contraseña con await
        if not await verify_password(login_data.password, user.hashed_password):
            raise UnauthorizedException("Usuario/Email o contraseña incorrectos")

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
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
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
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    async def get_all_users(
        self, skip: int = 0, limit: int = 100
    ) -> List[UserResponse]:
        """
        Obtiene lista de todos los usuarios con paginación.
        """
        # Usamos el método list() del repository
        users_docs = await self.user_repo.list(skip=skip, limit=limit)

        return [
            UserResponse(
                _id=doc["_id"],
                email=doc["email"],
                username=doc["username"],
                full_name=doc["full_name"],
                role=doc["role"],
                is_active=doc["is_active"],
                created_at=doc["created_at"],
                updated_at=doc.get("updated_at"),
            )
            for doc in users_docs
        ]

    async def update_user(self, user_id: str, update_data: UserUpdate) -> UserResponse:
        """
        Actualiza un usuario existente.

        Args:
            user_id: ID del usuario a actualizar
            update_data: Datos a actualizar (todos opcionales)

        Returns:
            Usuario actualizado

        Raises:
            NotFoundException: Si el usuario no existe
            ConflictException: Si el email o username ya están en uso
        """
        # Verificamos que el usuario exista
        existing_user = await self.user_repo.get_by_id(user_id)
        if not existing_user:
            raise NotFoundException(f"Usuario con ID {user_id} no encontrado")

        # Construimos el dict de actualización solo con campos presentes
        update_dict = {}

        if update_data.email is not None:
            # Verificamos que el email no esté en uso por otro usuario
            if await self.user_repo.email_exists(
                update_data.email, exclude_user_id=user_id
            ):
                raise ConflictException(
                    f"El email {update_data.email} ya está registrado"
                )
            update_dict["email"] = update_data.email

        if update_data.username is not None:
            # Verificamos que el username no esté en uso por otro usuario
            if await self.user_repo.username_exists(
                update_data.username, exclude_user_id=user_id
            ):
                raise ConflictException(
                    f"El username {update_data.username} ya está registrado"
                )
            update_dict["username"] = update_data.username

        if update_data.full_name is not None:
            update_dict["full_name"] = update_data.full_name

        if update_data.role is not None:
            update_dict["role"] = update_data.role.value

        if update_data.is_active is not None:
            update_dict["is_active"] = update_data.is_active

        if update_data.password is not None:
            # Hasheamos la nueva contraseña
            update_dict["hashed_password"] = await hash_password(update_data.password)

        # Si no hay nada que actualizar, devolvemos el usuario actual
        if not update_dict:
            return await self.get_user_by_id(user_id)

        # Actualizamos en el repositorio
        updated_doc = await self.user_repo.update_user(user_id, update_dict)

        # Convertimos a UserResponse
        user = User(**updated_doc)
        return UserResponse(
            _id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    async def delete_user(self, user_id: str) -> None:
        """
        Elimina un usuario (hard delete).

        Args:
            user_id: ID del usuario a eliminar

        Raises:
            NotFoundException: Si el usuario no existe
        """
        # Verificamos que el usuario exista
        existing_user = await self.user_repo.get_by_id(user_id)
        if not existing_user:
            raise NotFoundException(f"Usuario con ID {user_id} no encontrado")

        # Eliminamos
        await self.user_repo.delete_user(user_id)
