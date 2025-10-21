from typing import Optional, List
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorCollection
from repositories.base_repository_md import BaseRepositoryMD
from pymongo.errors import DuplicateKeyError
from exceptions import ConflictException, DatabaseException


class UserRepository(BaseRepositoryMD):
    """
    Repo de usuarios sobre Mongo. Devuelve dicts JSON-friendly.
    El service se encarga del hash y de mapear a modelos Pydantic.
    """

    def __init__(self, collection: AsyncIOMotorCollection):
        super().__init__(collection)

    async def ensure_indexes(self):
        """
        Crea índices necesarios para la colección de usuarios.
        Debe llamarse al iniciar la aplicación.
        """
        try:
            await self.collection.create_index("email", unique=True)
            await self.collection.create_index("username", unique=True)
            print("✅ Índices de 'users' OK (email y username únicos)")
        except Exception as e:
            raise DatabaseException(f"No se pudieron crear índices de users: {e}")

    async def create_with_unique_check(self, data: dict) -> dict:
        """
        Inserta un usuario; 'data' debe traer 'hashed_password' ya preparado por el service.
        Captura duplicados por índice único (email o username).
        """
        try:
            result = await self.collection.insert_one(data)
            # Se usa utilidades del base para devolver JSON-friendly
            return await self.find_by_id(str(result.inserted_id))
        except DuplicateKeyError as e:
            # Determinamos qué campo está duplicado
            error_msg = str(e)
            if "email" in error_msg:
                raise ConflictException(
                    f"El email {data.get('email')} ya está registrado"
                )
            elif "username" in error_msg:
                raise ConflictException(
                    f"El username {data.get('username')} ya está registrado"
                )
            else:
                raise ConflictException("Email o username ya está registrado")
        except Exception as e:
            raise DatabaseException(f"Error al crear usuario: {e}")

    async def get_by_email(self, email: str) -> Optional[dict]:
        """
        Devuelve un dict JSON-friendly o None.
        """
        try:
            doc = await self.collection.find_one({"email": email})
            if not doc:
                return None
            doc["_id"] = str(doc["_id"])
            return doc
        except Exception as e:
            raise DatabaseException(f"Error al buscar por email: {e}")

    async def get_by_id(self, user_id: str) -> Optional[dict]:
        """
        Alias de find_by_id del base (valida id y convierte _id→str).
        """
        return await self.find_by_id(user_id)

    async def list(self, skip: int = 0, limit: int = 100) -> List[dict]:
        """
        Paginación básica.
        """
        try:
            cursor = self.collection.find().skip(skip).limit(limit)
            items: List[dict] = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                items.append(doc)
            return items
        except Exception as e:
            raise DatabaseException(f"Error al listar usuarios: {e}")

    async def get_by_username(self, username: str) -> Optional[dict]:
        """
        Devuelve un dict JSON-friendly o None.
        Busca por username (case-insensitive).
        """
        try:
            doc = await self.collection.find_one({"username": username.lower()})
            if not doc:
                return None
            doc["_id"] = str(doc["_id"])
            return doc
        except Exception as e:
            raise DatabaseException(f"Error al buscar por username: {e}")

    async def get_by_username_or_email(self, username_or_email: str) -> Optional[dict]:
        """
        Busca un usuario por username O email.
        Útil para login.
        """
        try:
            # Intentamos buscar por ambos campos
            doc = await self.collection.find_one(
                {
                    "$or": [
                        {"email": username_or_email},
                        {"username": username_or_email.lower()},
                    ]
                }
            )
            if not doc:
                return None
            doc["_id"] = str(doc["_id"])
            return doc
        except Exception as e:
            raise DatabaseException(f"Error al buscar usuario: {e}")

    async def update_user(self, user_id: str, update_data: dict) -> dict:
        """
        Actualiza un usuario.
        Solo actualiza los campos presentes en update_data.
        """
        try:
            # Añadimos timestamp de actualización
            update_data["updated_at"] = datetime.utcnow()

            # Usamos el método update del base
            return await self.update(user_id, update_data)
        except DuplicateKeyError as e:
            error_msg = str(e)
            if "email" in error_msg:
                raise ConflictException(f"El email ya está registrado")
            elif "username" in error_msg:
                raise ConflictException(f"El username ya está registrado")
            else:
                raise ConflictException("Email o username ya está registrado")
        except Exception as e:
            raise DatabaseException(f"Error al actualizar usuario: {e}")

    async def delete_user(self, user_id: str) -> bool:
        """
        Elimina un usuario permanentemente.
        Retorna True si se eliminó correctamente.
        """
        try:
            return await self.delete(user_id)
        except Exception as e:
            raise DatabaseException(f"Error al eliminar usuario: {e}")

    async def email_exists(
        self, email: str, exclude_user_id: Optional[str] = None
    ) -> bool:
        """
        Verifica si existe un usuario con ese email.
        exclude_user_id: ID de usuario a excluir (útil para updates).
        """
        query = {"email": email}
        if exclude_user_id:
            from bson import ObjectId

            query["_id"] = {"$ne": ObjectId(exclude_user_id)}

        count = await self.collection.count_documents(query)
        return count > 0

    async def username_exists(
        self, username: str, exclude_user_id: Optional[str] = None
    ) -> bool:
        """
        Verifica si existe un usuario con ese username.
        exclude_user_id: ID de usuario a excluir (útil para updates).
        """
        query = {"username": username.lower()}
        if exclude_user_id:
            from bson import ObjectId

            query["_id"] = {"$ne": ObjectId(exclude_user_id)}

        count = await self.collection.count_documents(query)
        return count > 0
