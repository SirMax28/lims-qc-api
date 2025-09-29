from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/hello",
    summary="Saludo inicial",
    description="Devuelve un mensaje de saludo para comprobar el funcionamiento de la API",
)
async def hello_world():
    return {"message": "Hello World"}
