from typing import Optional, AsyncGenerator
from urllib.parse import urlparse
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import settings
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.exc import NoSuchModuleError
from sqlalchemy import text  


def _normalize_postgres_uri(uri: str) -> str:
    if not uri:
        return uri

    uri = uri.strip()

    if "+asyncpg" in uri:
        return uri

    if uri.startswith("postgres://"):
        return "postgresql+asyncpg://" + uri[len("postgres://") :]

    if uri.startswith("postgresql://"):
        return "postgresql+asyncpg://" + uri[len("postgresql://") :]

    if uri.startswith("postgresql+"):
        parts = uri.split("://", 1)
        if len(parts) == 2:
            rest = parts[1]
            return "postgresql+asyncpg://" + rest

    return uri


class MongoDB:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.is_connected = False

    async def connect(self):
        if self.is_connected:
            return
        if not settings.MONGODB_URI_DEV_LAB_TEST:
            raise RuntimeError("MONGODB_URI_DEV_LAB_TEST no configurado")
        self.client = AsyncIOMotorClient(settings.MONGODB_URI_DEV_LAB_TEST)
        self.db = self.client[settings.MONGODB_NAME]
        await self.client.admin.command("ping")
        self.is_connected = True
        print("Conexión a MongoDB establecida.")

    async def disconnect(self):
        if self.client:
            self.client.close()
            self.is_connected = False
            print("Conexión a MongoDB cerrada.")


class PostgresDB:
    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.async_session: Optional[async_sessionmaker[AsyncSession]] = None
        self.is_connected = False

    async def connect(self):
        if self.is_connected:
            return
        if not settings.POSTGRES_URI:
            raise RuntimeError("POSTGRES_URI no configurado")

        normalized = _normalize_postgres_uri(settings.POSTGRES_URI)

        try:
            self.engine = create_async_engine(normalized, future=True)
        except NoSuchModuleError as e:
            msg = (
                f"No se pudo crear engine con la URI: {settings.POSTGRES_URI!r}. "
                "Asegúrate de usar 'postgresql+asyncpg://user:pass@host:port/db' "
                "y de instalar `asyncpg` (pip install asyncpg)."
            )
            raise RuntimeError(msg) from e
        except Exception as e:
            raise RuntimeError(f"Error al crear engine async de SQLAlchemy: {e}") from e

        self.async_session = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

        # --- Aquí está la corrección: usar sqlalchemy.text(...) para ejecutar SQL raw ---
        try:
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as e:
            try:
                await self.engine.dispose()
            except Exception:
                pass
            raise RuntimeError(f"Error probando conexión a Postgres: {e}") from e

        self.is_connected = True
        print("Conexión a Postgres establecida.")

    async def init_models(self):
        if not self.engine:
            raise RuntimeError("Engine no inicializado")
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        print("Tablas de SQLModel creadas (si no existían).")

    async def disconnect(self):
        if self.engine:
            await self.engine.dispose()
            self.is_connected = False
            print("Conexión a Postgres cerrada.")


class Database:
    def __init__(self):
        self.mongo = MongoDB()
        self.postgres = PostgresDB()

    async def connect(self):
        engine = (settings.DB_ENGINE or "").lower()
        if engine in ("mongo", "mongodb"):
            await self.mongo.connect()
        elif engine in ("postgres", "postgresql"):
            await self.postgres.connect()
            await self.postgres.init_models()
        else:
            raise RuntimeError(f"DB_ENGINE desconocido: {settings.DB_ENGINE}")

    async def disconnect(self):
        engine = (settings.DB_ENGINE or "").lower()
        if engine in ("mongo", "mongodb"):
            await self.mongo.disconnect()
        elif engine in ("postgres", "postgresql"):
            await self.postgres.disconnect()


db = Database()

# dependencia de la sesión de SQL
async def get_sql_session() -> AsyncGenerator[Optional[AsyncSession], None]:
    if (settings.DB_ENGINE or "").lower() not in ("postgres", "postgresql"):
        yield None
    else:
        assert db.postgres.async_session is not None, "async_session no inicializada"
        async with db.postgres.async_session() as session:
            yield session


# Compatibilidad de nombres antiguos
try:
    mongodb = db.mongo
except Exception:
    mongodb = None

try:
    postgres = db.postgres
except Exception:
    postgres = None

__all__ = ["db", "mongodb", "postgres", "get_sql_session"]
