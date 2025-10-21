from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum


# Roles como lista fija de valores
class UserRole(str, Enum):
    ADMIN = "admin"
    QUALITY = "quality"
    TECHNICIAN = "technician"
    AUDITOR = "auditor"
    VIEWER = "viewer"


# Modelo base con campos comunes para todos
class UserBase(BaseModel):
    email: EmailStr  # EmailStr valida que sea un email válido
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    full_name: str = Field(..., min_length=2, max_length=100)
    role: UserRole = UserRole.VIEWER  # Por defecto es viewer


# Modelo para CREAR un usuario con password y confirm_password
class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        """
        Valida que password y confirm_password coincidan.
        Pydantic v2 usa field_validator en lugar de validator.
        """
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Las contraseñas no coinciden")
        return v

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v):
        """
        Valida que el username solo contenga caracteres alfanuméricos, guiones y guiones bajos.
        """
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "El username solo puede contener letras, números, guiones y guiones bajos"
            )
        return v.lower()  # Convertimos a minúsculas para consistencia


# Modelo para LOGIN - puede usar email o username
class UserLogin(BaseModel):
    username_or_email: str = Field(..., description="Email o username del usuario")
    password: str


# Modelo para ACTUALIZAR usuario (campos opcionales)
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(
        None, min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$"
    )
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)  # Nueva contraseña (opcional)

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v):
        if v is not None:
            if not v.replace("_", "").replace("-", "").isalnum():
                raise ValueError(
                    "El username solo puede contener letras, números, guiones y guiones bajos"
                )
            return v.lower()
        return v


# Modelo que se guarda en MongoDB
class User(UserBase):
    id: Optional[str] = Field(None, alias="_id")  # MongoDB usa objeto _id
    hashed_password: str  # Contraseña hasheada
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    # v2 usa model_config
    model_config = ConfigDict(
        populate_by_name=True,  # Permite usar _id o id
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "email": "usuario@ejemplo.com",
                "username": "juanperez",
                "full_name": "Juan Pérez",
                "role": "technician",
                "is_active": True,
                "created_at": "2025-09-30T10:00:00",
            }
        },
    )


# Modelo de RESPUESTA, sin password (datos públicos)
class UserResponse(UserBase):
    id: str = Field(..., alias="_id")
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(populate_by_name=True)


# Modelo para el TOKEN JWT que devolvemos al hacer login
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Datos que guardamos DENTRO del token JWT
class TokenData(BaseModel):
    user_id: Optional[str] = None  # Cambiado de email a user_id
    role: Optional[str] = None
