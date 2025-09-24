import aiobcrypt

# Función asíncrona para hashear la contraseña
async def hash_password(password: str) -> str:
    try:
        # Generar salt y hashear de forma asíncrona
        salt = await aiobcrypt.gensalt()
        hashed_bytes = await aiobcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed_bytes.decode('utf-8')
    except Exception as e:
        raise RuntimeError(f"Error al hashear la contraseña: {e}") from e

# Función asíncrona para verificar la contraseña hasheada
async def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        # Convertir a bytes
        plain_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        
        # Verificar de forma asíncrona
        return await aiobcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception as e:
        raise RuntimeError(f"Error al verificar la contraseña: {e}") from e