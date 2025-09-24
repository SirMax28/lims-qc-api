from motor.motor_asyncio import AsyncIOMotorCollection
from bson import ObjectId, errors
from exceptions import NotFoundException, DatabaseException


class BaseRepositoryMD:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    async def _validate_id(self, id: str):
        if id.isdigit():
            return int(id)
        try:
            return ObjectId(id)
        except errors.InvalidId:
            raise NotFoundException("ID inválido")

    async def find_by_username(self, username: str) -> list[dict]:
        try:
            cursor = self.collection.find({"username": username})
            results = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                results.append(doc)
            return results
        except Exception as e:
            raise DatabaseException(f"Error al buscar por username: {str(e)}")

    async def find_all(self):
        try:
            cursor = self.collection.find()
            documents = []
            async for document in cursor:
                document["_id"] = str(document["_id"])
                documents.append(document)
            return documents
        except Exception as e:
            raise DatabaseException(f"Error al obtener documentos: {str(e)}")

    async def find_by_id(self, id: str):
        try:
            obj_id = await self._validate_id(id)
            document = await self.collection.find_one({"_id": obj_id})
            if not document:
                raise NotFoundException("Documento no encontrado")
            document["_id"] = str(document["_id"])
            return document
        except NotFoundException:
            raise  # Propaga la excepción directamente
        except Exception as e:
            raise DatabaseException(f"Error de base de datos: {str(e)}")

    async def create(self, data: dict):
        try:
            result = await self.collection.insert_one(data)
            return await self.find_by_id(str(result.inserted_id))
        except Exception as e:
            raise DatabaseException(f"Error al crear documento: {str(e)}")

    async def update(self, id: str, update_data: dict):
        try:
            obj_id = await self._validate_id(id)
            result = await self.collection.update_one(
                {"_id": obj_id}, {"$set": update_data}
            )
            if result.matched_count == 0:
                raise NotFoundException("Documento a actualizar no encontrado")
            return await self.find_by_id(id)
        except NotFoundException:
            raise
        except Exception as e:
            raise DatabaseException(f"Error al actualizar: {str(e)}")

    async def delete(self, id: str):
        try:
            obj_id = await self._validate_id(id)
            result = await self.collection.delete_one({"_id": obj_id})
            if result.deleted_count == 0:
                raise NotFoundException("Documento a eliminar no encontrado")
            return True
        except NotFoundException:
            raise
        except Exception as e:
            raise DatabaseException(f"Error al eliminar: {str(e)}")