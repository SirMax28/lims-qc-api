from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from core.database import db 
from repositories.user_repository import UserRepository

# Importar routers de los endpoints
from api.endpoints.ok import router as ok_router
from api.endpoints.hello import router as hello_router
from api.endpoints.users import router as users_router
from api.endpoints.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicialización conexión según DB_ENGINE (Mongo o Postgres)
    try:
        await db.connect()
        print("✅ Conexión a la base de datos establecida correctamente")
        
        # Crear índices en la colección de usuarios
        collection = db.mongo.db["users"]
        user_repo = UserRepository(collection)
        await user_repo.ensure_indexes()
        
    except Exception as e:
        print(f"❌ Error fatal de conexión a la base de datos: {str(e)}")
        raise RuntimeError("No se pudo iniciar la aplicación - Error de base de datos") from e

    yield

    # Cierre
    await db.disconnect()
    print("🔌 Conexión a la base de datos cerrada")

app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(ok_router, prefix=settings.API_PREFIX, tags=["ok"])
app.include_router(hello_router, prefix=settings.API_PREFIX, tags=["hello"])
app.include_router(users_router, prefix=settings.API_PREFIX, tags=["users"])
app.include_router(auth_router, prefix=settings.API_PREFIX, tags=["auth"])


# Static files
#app.mount("/static", StaticFiles(directory="assets"), name="static")


