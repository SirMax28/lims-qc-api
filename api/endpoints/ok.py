from fastapi import APIRouter
from sqlalchemy import text
from core.config import settings
from core.database import db

router = APIRouter()


@router.get(
    "/ok",
    include_in_schema=True,
    summary="Verificación de salud del sistema",
    description="Proporciona el estado actual del servicio y sus dependencias"
)
async def health_check():
    """
    Comprueba el estado de la aplicación y la base de datos.
    Funciona con DB_ENGINE=mongodb o DB_ENGINE=postgresql.
    """
    service_status = {
        "status": "running",
        "version": settings.PROJECT_VERSION,
        "db_engine": settings.DB_ENGINE,
        "dependencies": {
            "database": "disconnected"
        }
    }

    engine = (settings.DB_ENGINE or "").lower()

    if engine in ("mongo", "mongodb"):
        try:
            # Si la instancia client existe, hacemos ping
            client = getattr(db.mongo, "client", None)
            if not client:
                raise RuntimeError("Mongo client no inicializado")
            await client.admin.command("ping")
            service_status["dependencies"]["database"] = "healthy"
        except Exception as e:
            service_status["dependencies"]["database"] = f"unhealthy: {str(e)}"

    elif engine in ("postgres", "postgresql"):
        try:
            pg_engine = getattr(db.postgres, "engine", None)
            if not pg_engine:
                raise RuntimeError("Postgres engine no inicializado")
            # Ejecutamos SELECT 1 como comprobación
            async with pg_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            service_status["dependencies"]["database"] = "healthy"
        except Exception as e:
            service_status["dependencies"]["database"] = f"unhealthy: {str(e)}"

    else:
        service_status["dependencies"]["database"] = f"unknown DB_ENGINE: {settings.DB_ENGINE}"

    return service_status
