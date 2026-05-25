from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_current_user, verify_password, hash_password, is_password_hashed
from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.auth import LoginRequest, TokenResponse
from app.core.rate_limit import limiter


router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, datos: LoginRequest, db: Session = Depends(get_db)):
    usuario = (
        db.query(Usuario).filter(Usuario.correo == datos.correo).first()
    )
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )
    password_correcta = False
    if is_password_hashed(usuario.password):
        password_correcta = verify_password(datos.password, usuario.password)
    else:
        password_correcta = usuario.password == datos.password
        if password_correcta:
            usuario.password = hash_password(datos.password)
            db.commit()
            db.refresh(usuario)
    if not password_correcta:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )
    rol_nombre = usuario.rol.rol if usuario.rol else None
    access_token = create_access_token(
        data={
            "sub": usuario.id_usuario,
            "rol": rol_nombre,
            "id_clinica_tenant": usuario.id_clinica_tenant,
        }
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "id_usuario": usuario.id_usuario,
        "id_clinica_tenant": usuario.id_clinica_tenant,
        "correo": usuario.correo,
        "rol": rol_nombre,
    }

@router.get("/me")
def get_me(usuario_actual: Usuario = Depends(get_current_user)):
    return {
        "id_usuario": usuario_actual.id_usuario,
        "id_clinica_tenant": usuario_actual.id_clinica_tenant,
        "correo": usuario_actual.correo,
        "telefono": usuario_actual.telefono,
        "rol": usuario_actual.rol.rol if usuario_actual.rol else None,
    }
