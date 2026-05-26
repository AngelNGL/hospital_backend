from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime, time, timedelta

from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.core.permissions import require_any_role
from app.database import get_db
from app.models.paciente import Paciente
from app.models.usuario import Usuario
from app.models.catalogos import Parentesco
from app.schemas.paciente import PacienteCreate, PacienteUpdate, PacienteEstadoUpdate


router = APIRouter(
    prefix="/pacientes",
    tags=["Pacientes"],
)

@router.get("")
@limiter.limit("30/minute")
def listar_pacientes_clinica(
        request: Request,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(require_any_role(["admin", "recepcionista"])),
):
    pacientes = (
        db.query(Paciente)
        .filter(Paciente.id_clinica_tenant == usuario_actual.id_clinica_tenant)
        .order_by(Paciente.nombre, Paciente.apellido)
        .all()
    )
    return [
        {
            "id_paciente": paciente.id_paciente,
            "id_usuario": paciente.id_usuario,
            "nombre": paciente.nombre,
            "apellido": paciente.apellido,
            "nombre_completo": f"{paciente.nombre} {paciente.apellido}",
            "sexo": paciente.sexo,
            "fecha_nacimiento": paciente.fecha_nacimiento,
            "curp": paciente.curp,
            "activo": paciente.activo,
            "fecha_baja": paciente.fecha_baja,
            "id_parentesco": paciente.id_parentesco,
            "parentesco": paciente.parentesco.parentesco if paciente.parentesco else None,
        }
        for paciente in pacientes
    ]

@router.get("/me")
@limiter.limit("30/minute")
def listar_mis_pacientes(
        request: Request,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(get_current_user),
):
    pacientes = (
        db.query(Paciente)
        .filter(
            Paciente.id_usuario == usuario_actual.id_usuario,
            Paciente.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .order_by(Paciente.nombre, Paciente.apellido)
        .all()
    )
    return [
        {
            "id_paciente": paciente.id_paciente,
            "nombre": paciente.nombre,
            "apellido": paciente.apellido,
            "nombre_completo": f"{paciente.nombre} {paciente.apellido}",
            "sexo": paciente.sexo,
            "fecha_nacimiento": paciente.fecha_nacimiento,
            "curp": paciente.curp,
            "activo": paciente.activo,
            "id_parentesco": paciente.id_parentesco,
            "parentesco": paciente.parentesco.parentesco if paciente.parentesco else None,
        }
        for paciente in pacientes
    ]

@router.get("/{id_paciente}")
@limiter.limit("30/minute")
def obtener_paciente_por_id(
        request: Request,
        id_paciente: str,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(require_any_role(["admin", "recepcionista"])),
):
    paciente = (
        db.query(Paciente)
        .filter(
            Paciente.id_paciente == id_paciente,
            Paciente.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .first()
    )
    if paciente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado",
        )
    return {
        "id_paciente": paciente.id_paciente,
        "id_usuario": paciente.id_usuario,
        "nombre": paciente.nombre,
        "apellido": paciente.apellido,
        "nombre_completo": f"{paciente.nombre} {paciente.apellido}",
        "sexo": paciente.sexo,
        "fecha_nacimiento": paciente.fecha_nacimiento,
        "curp": paciente.curp,
        "activo": paciente.activo,
        "fecha_baja": paciente.fecha_baja,
        "id_parentesco": paciente.id_parentesco,
        "parentesco": paciente.parentesco.parentesco if paciente.parentesco else None,
    }

@router.post("")
@limiter.limit("10/minute")
def crear_paciente(
        request: Request,
        datos: PacienteCreate,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(get_current_user),
):
    parentesco = (
        db.query(Parentesco)
        .filter(Parentesco.parentesco == datos.parentesco)
        .first()
    )
    if parentesco is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parentesco no válido",
        )

    paciente_existente = (
        db.query(Paciente)
        .filter(
            Paciente.curp == datos.curp,
            Paciente.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .first()
    )
    if paciente_existente is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un paciente registrado con ese CURP",
        )

    nuevo_paciente = Paciente(
        id_clinica_tenant=usuario_actual.id_clinica_tenant,
        nombre=datos.nombre,
        apellido=datos.apellido,
        sexo=datos.sexo,
        fecha_nacimiento=datos.fecha_nacimiento,
        curp=datos.curp,
        id_usuario=usuario_actual.id_usuario,
        id_parentesco=parentesco.id_parentesco,
        activo=True,
    )
    try:
        db.add(nuevo_paciente)
        db.commit()
        db.refresh(nuevo_paciente)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo crear al paciente. Revisa que los datos esten correctos.",
        )

    return {
        "id_paciente": nuevo_paciente.id_paciente,
        "nombre": nuevo_paciente.nombre,
        "apellido": nuevo_paciente.apellido,
        "nombre_completo": f"{nuevo_paciente.nombre} {nuevo_paciente.apellido}",
        "sexo": nuevo_paciente.sexo,
        "fecha_nacimiento": nuevo_paciente.fecha_nacimiento,
        "curp": nuevo_paciente.curp,
        "activo": nuevo_paciente.activo,
        "id_parentesco": nuevo_paciente.id_parentesco,
        "parentesco": parentesco.parentesco,
    }

@router.patch("/{id_paciente}")
@limiter.limit("10/minute")
def actualizar_paciente(
        request: Request,
        id_paciente: str,
        datos: PacienteUpdate,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(get_current_user),
):
    paciente = (
        db.query(Paciente)
        .filter(
            Paciente.id_paciente == id_paciente,
            Paciente.id_usuario == usuario_actual.id_usuario,
            Paciente.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .first()
    )
    if paciente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado",
        )
    if datos.parentesco is not None:
        parentesco = (
            db.query(Parentesco)
            .filter(Parentesco.parentesco == datos.parentesco)
            .first()
        )
        if parentesco is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parentesco no válido",
            )
        paciente.id_parentesco = parentesco.id_parentesco
    if datos.curp is not None and datos.curp != paciente.curp:
        paciente_existente = (
            db.query(Paciente)
            .filter(
                Paciente.curp == datos.curp,
                Paciente.id_clinica_tenant == usuario_actual.id_clinica_tenant,
            )
            .first()
        )
        if paciente_existente is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un paciente registrado con esa CURP",
            )
        paciente.curp = datos.curp
    if datos.nombre is not None:
        paciente.nombre = datos.nombre
    if datos.apellido is not None:
        paciente.apellido = datos.apellido
    if datos.sexo is not None:
        paciente.sexo = datos.sexo
    if datos.fecha_nacimiento is not None:
        paciente.fecha_nacimiento = datos.fecha_nacimiento
    try:
        db.commit()
        db.refresh(paciente)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo actualizar al paciente. Revisa que los datos estén correctos.",
        )
    return {
        "id_paciente": paciente.id_paciente,
        "nombre": paciente.nombre,
        "apellido": paciente.apellido,
        "nombre_completo": f"{paciente.nombre} {paciente.apellido}",
        "sexo": paciente.sexo,
        "fecha_nacimiento": paciente.fecha_nacimiento,
        "curp": paciente.curp,
        "activo": paciente.activo,
        "id_parentesco": paciente.id_parentesco,
        "parentesco": paciente.parentesco.parentesco if paciente.parentesco else None,
    }

@router.patch("/{id_paciente}/estado")
@limiter.limit("10/minute")
def actualizar_estado_paciente(
        request: Request,
        id_paciente: str,
        datos: PacienteEstadoUpdate,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(get_current_user),
):
    paciente = (
        db.query(Paciente)
        .filter(
            Paciente.id_paciente == id_paciente,
            Paciente.id_usuario == usuario_actual.id_usuario,
            Paciente.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .first()
    )
    if paciente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado",
        )
    paciente.activo = datos.activo
    if datos.activo is False:
        paciente.fecha_baja = datetime.now()
    else:
        paciente.fecha_baja = None
    try:
        db.commit()
        db.refresh(paciente)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo actualizar el estado del paciente.",
        )
    return {
        "id_paciente": paciente.id_paciente,
        "nombre": paciente.nombre,
        "apellido": paciente.apellido,
        "nombre_completo": f"{paciente.nombre} {paciente.apellido}",
        "activo": paciente.activo,
        "fecha_baja": paciente.fecha_baja,
    }