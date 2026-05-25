from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.core.config import settings
from app.database import get_db
from app.models.usuario import Usuario


bearer_scheme = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict) -> str:
    # crea un token jwt
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({
        "exp": expire
    })
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
        db: Session = Depends(get_db),
) -> Usuario:
    # lee el token jwt, obtiene el id_usuario, busca el usuario en la db
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar el token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        id_usuario: str | None = payload.get("sub")
        if id_usuario is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    usuario = (
        db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    )
    if usuario is None:
        raise credentials_exception
    return usuario

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def is_password_hashed(password: str) -> bool:
    return (
            password.startswith("$2b$")
            or password.startswith("$2a$")
            or password.startswith("$2y$")
    )

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
