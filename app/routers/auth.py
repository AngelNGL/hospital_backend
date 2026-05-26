from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.security import (create_access_token, get_current_user, verify_password, hash_password, is_password_hashed)
from app.database import get_db
from app.models.usuario import Usuario, Clinica, Rol
from app.schemas.auth import LoginRequest, TokenResponse, RegisterRequest
from app.core.rate_limit import limiter
from app.models.catalogos import Parentesco
from app.models.paciente import Paciente


router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)

def obtener_mensaje_mysql(error):
    if hasattr(error, "orig") and error.orig:
        return str(error.orig)
    return str(error)

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

@router.post("/register", response_model=TokenResponse)
@limiter.limit("5/minute")
def register(
        request: Request,
        datos: RegisterRequest,
        db: Session = Depends(get_db),
):
    clinica = (
        db.query(Clinica)
        .filter(
            Clinica.id_clinica_tenant == datos.id_clinica_tenant,
            Clinica.activo == True,
        )
        .first()
    )
    if clinica is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Clínica no válida",
        )

    rol_cliente = (
        db.query(Rol)
        .filter(Rol.rol == "cliente")
        .first()
    )
    if rol_cliente is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No existe el rol cliente en la base de datos",
        )

    parentesco_titular = (
        db.query(Parentesco)
        .filter(Parentesco.parentesco == "titular")
        .first()
    )
    if parentesco_titular is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No existe el parentesco titular en la base de datos",
        )

    usuario_existente = (
        db.query(Usuario)
        .filter(Usuario.correo == datos.correo)
        .first()
    )
    if usuario_existente is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario registrado con ese correo",
        )

    telefono_existente = (
        db.query(Usuario)
        .filter(Usuario.telefono == datos.telefono)
        .first()
    )
    if telefono_existente is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario registrado con ese teléfono",
        )

    paciente_existente = (
        db.query(Paciente)
        .filter(
            Paciente.curp == datos.curp,
            Paciente.id_clinica_tenant == datos.id_clinica_tenant,
        )
        .first()
    )
    if paciente_existente is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un paciente registrado con esa CURP en esta clínica",
        )

    nuevo_usuario = Usuario(
        id_clinica_tenant=datos.id_clinica_tenant,
        correo=datos.correo,
        telefono=datos.telefono,
        password=hash_password(datos.password),
        id_rol=rol_cliente.id_rol,
    )
    try:
        db.add(nuevo_usuario)
        db.flush()

        nuevo_paciente = Paciente(
            id_clinica_tenant=datos.id_clinica_tenant,
            nombre=datos.nombre,
            apellido=datos.apellido,
            sexo=datos.sexo,
            fecha_nacimiento=datos.fecha_nacimiento,
            curp=datos.curp,
            id_usuario=nuevo_usuario.id_usuario,
            id_parentesco=parentesco_titular.id_parentesco,
            activo=True,
        )
        db.add(nuevo_paciente)
        db.commit()
        db.refresh(nuevo_usuario)
    except (IntegrityError, OperationalError) as error:
        db.rollback()
        mensaje = obtener_mensaje_mysql(error)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo registrar el usuario: {mensaje}",
        )

    rol_nombre = nuevo_usuario.rol.rol if nuevo_usuario.rol else "cliente"
    access_token = create_access_token(
        data={
            "sub": nuevo_usuario.id_usuario,
            "rol": rol_nombre,
            "id_clinica_tenant": nuevo_usuario.id_clinica_tenant,
        }
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "id_usuario": nuevo_usuario.id_usuario,
        "id_clinica_tenant": nuevo_usuario.id_clinica_tenant,
        "correo": nuevo_usuario.correo,
        "rol": rol_nombre,
    }
