from typing import Optional, List
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
            # await self.collection.create_index("username", unique=True)
            print("✅ Índices de 'users' OK")
        except Exception as e:
            raise DatabaseException(f"No se pudieron crear índices de users: {e}")

    async def create_with_email_check(self, data: dict) -> dict:
        """
        Inserta un usuario; 'data' debe traer 'hashed_password' ya preparado por el service.
        Captura duplicados por índice único.
        """
        try:
            result = await self.collection.insert_one(data)
            # Se usa utilidades del base para devolver JSON-friendly
            return await self.find_by_id(str(result.inserted_id))
        except DuplicateKeyError:
            raise ConflictException(f"El email {data.get('email')} ya está registrado")
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

    async def email_exists(self, email: str) -> bool:
        """
        Verifica si existe un usuario con ese email.
        """
        count = await self.collection.count_documents({"email": email})
        return count > 0

