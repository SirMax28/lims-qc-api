from pydantic import BaseModel, EmailStr, Field, ConfigDict
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
    email: EmailStr  
    full_name: str = Field(..., min_length=2, max_length=100)
    role: UserRole = UserRole.VIEWER  # Por defecto es viewer


# Modelo para CREAR un usuario con password
class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)

# Modelo para LOGIN con password y email
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Modelo que se guarda en MongoDB
class User(UserBase):
    id: Optional[str] = Field(None, alias="_id")  # MongoDB usa objeto _id
    hashed_password: str  # Contraseña hasheada
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    #v2 usa model_config
    model_config = ConfigDict(
        populate_by_name=True,  # Permite usar _id o id
        json_schema_extra={
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "email": "usuario@ejemplo.com",
                "full_name": "Juan Pérez",
                "role": "technician",
                "is_active": True,
                "created_at": "2025-09-30T10:00:00"
            }
        }
    )

# Modelo de RESPUESTA, sin password
class UserResponse(UserBase):
    id: str = Field(..., alias="_id")
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(
        populate_by_name=True
    )

# Modelo para el TOKEN JWT que devolvemos al hacer login
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Datos que guardamos DENTRO del token JWT
class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None