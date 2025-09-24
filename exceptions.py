from fastapi import HTTPException, status
from pydantic import BaseModel

class AppException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

class NotFoundException(AppException):
    def __init__(self, detail: str = "Recurso no encontrado"):
        super().__init__(status.HTTP_404_NOT_FOUND, detail)

class ConflictException(AppException):
    def __init__(self, detail: str = "Conflicto de datos"):
        super().__init__(status.HTTP_409_CONFLICT, detail)

class UnauthorizedException(AppException):
    def __init__(self, detail: str = "No autorizado"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail)

class ValidationException(AppException):
    def __init__(self, detail: str = "Error de validación"):
        super().__init__(status.HTTP_422_UNPROCESSABLE_ENTITY, detail)

class DatabaseException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {detail}"
        )

class ErrorResponse(BaseModel):
    detail: str