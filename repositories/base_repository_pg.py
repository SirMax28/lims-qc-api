from typing import Type, TypeVar, Generic, Optional, List, Any, Dict
from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from exceptions import NotFoundException, DatabaseException

T = TypeVar("T", bound=SQLModel)


def _serialize_model(instance: SQLModel) -> Dict[str, Any]:
    """
    Serializa una instancia de SQLModel/Pydantic.
    - Preferimos model_dump() (Pydantic v2).
    - Si no existe, usamos dict() (compatibilidad v1).
    - Si ninguna existe, usamos vars() como último recurso.
    """
    if instance is None:
        return {}
    if hasattr(instance, "model_dump"):
        # pydantic v2 / SQLModel más reciente
        try:
            return instance.model_dump()  # type: ignore[attr-defined]
        except Exception:
            # fallback robusto
            pass
    if hasattr(instance, "dict"):
        try:
            return instance.dict()
        except Exception:
            pass
    try:
        return dict(vars(instance))
    except Exception:
        return {}


class BaseRepositoryPG(Generic[T]):
    """
    Repositorio base para PostgreSQL usando SQLModel + AsyncSession.
    Mantiene API similar a la versión Mongo: find_all, find_by_id, create, update, delete, etc.
    """

    def __init__(self, model: Type[T], session: AsyncSession):
        self.model = model
        self.session = session

    async def _validate_id(self, id: str) -> int:
        """
        Valida/convierte id a int (Postgres usa integer primary key por defecto).
        Lanza NotFoundException si no es un entero válido.
        """
        try:
            return int(id)
        except (ValueError, TypeError):
            raise NotFoundException("ID inválido")

    async def find_by_username(self, username: str) -> List[dict]:
        """
        Busca por el campo 'username' (asume que el modelo tiene el atributo).
        Devuelve lista de dicts.
        """
        if not hasattr(self.model, "username"):
            raise DatabaseException("El modelo no tiene atributo 'username'")

        try:
            q = select(self.model).where(self.model.username == username)
            result = await self.session.execute(q)
            items = result.scalars().all()
            return [_serialize_model(item) for item in items]
        except SQLAlchemyError as e:
            raise DatabaseException(f"Error al buscar por username: {str(e)}")

    async def find_all(self) -> List[dict]:
        """
        Devuelve todos los registros de la tabla como lista de dicts.
        """
        try:
            q = select(self.model)
            result = await self.session.execute(q)
            items = result.scalars().all()
            return [_serialize_model(item) for item in items]
        except SQLAlchemyError as e:
            raise DatabaseException(f"Error al obtener documentos: {str(e)}")

    async def find_by_id(self, id: str) -> dict:
        """
        Busca por id (primary key). Devuelve dict del registro o lanza NotFoundException.
        """
        try:
            pk = await self._validate_id(id)
            q = select(self.model).where(self.model.id == pk)
            result = await self.session.execute(q)
            item = result.scalars().first()
            if not item:
                raise NotFoundException("Registro no encontrado")
            return _serialize_model(item)
        except NotFoundException:
            raise
        except SQLAlchemyError as e:
            raise DatabaseException(f"Error de base de datos: {str(e)}")

    async def create(self, data: dict) -> dict:
        """
        Crea un registro a partir de un dict y devuelve el objeto creado como dict.
        """
        try:
            instance: T = self.model(**data)
            self.session.add(instance)
            await self.session.commit()
            await self.session.refresh(instance)
            return _serialize_model(instance)
        except SQLAlchemyError as e:
            try:
                await self.session.rollback()
            except Exception:
                pass
            raise DatabaseException(f"Error al crear registro: {str(e)}")

    async def update(self, id: str, update_data: dict) -> dict:
        """
        Actualiza un registro por id con los campos en update_data y devuelve el registro actualizado.
        """
        try:
            pk = await self._validate_id(id)
            q = select(self.model).where(self.model.id == pk)
            result = await self.session.execute(q)
            instance: Optional[T] = result.scalars().first()
            if not instance:
                raise NotFoundException("Registro a actualizar no encontrado")

            for k, v in update_data.items():
                # solo setear atributos que existan
                if hasattr(instance, k):
                    setattr(instance, k, v)

            self.session.add(instance)
            await self.session.commit()
            await self.session.refresh(instance)
            return _serialize_model(instance)
        except NotFoundException:
            raise
        except SQLAlchemyError as e:
            try:
                await self.session.rollback()
            except Exception:
                pass
            raise DatabaseException(f"Error al actualizar: {str(e)}")

    async def delete(self, id: str) -> bool:
        """
        Elimina un registro por id. Devuelve True si fue eliminado, lanza NotFoundException si no existe.
        """
        try:
            pk = await self._validate_id(id)
            q = select(self.model).where(self.model.id == pk)
            result = await self.session.execute(q)
            instance: Optional[T] = result.scalars().first()
            if not instance:
                raise NotFoundException("Registro a eliminar no encontrado")

            # delete no es awaitable
            self.session.delete(instance)
            await self.session.commit()
            return True
        except NotFoundException:
            raise
        except SQLAlchemyError as e:
            try:
                await self.session.rollback()
            except Exception:
                pass
            raise DatabaseException(f"Error al eliminar: {str(e)}")
