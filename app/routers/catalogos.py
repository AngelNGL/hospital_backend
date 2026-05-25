from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.cache import (doctores_cache, especialidades_cache, parentescos_cache, estados_cita_cache)
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.database import get_db
from app.models.catalogos import Especialidad, EstadoCita, Parentesco
from app.models.usuario import Usuario
from app.models.doctor import Doctor


router = APIRouter(
    prefix="/catalogos",
    tags=["Catálogos"],
)

@router.get("/especialidades")
@limiter.limit("30/minute")
def listar_especialidades(
        request: Request,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(get_current_user),
):
    cache_key = "especialidades"
    if cache_key in especialidades_cache:
        return especialidades_cache[cache_key]

    especialidades = db.query(Especialidad).order_by(Especialidad.especialidad).all()
    resultado = [
        {
            "id_especialidad": especialidad.id_especialidad,
            "especialidad": especialidad.especialidad,
        }
        for especialidad in especialidades
    ]
    especialidades_cache[cache_key] = resultado
    return resultado

@router.get("/parentescos")
@limiter.limit("30/minute")
def listar_parentescos(
        request: Request,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(get_current_user),
):
    cache_key = "parentescos"
    if cache_key in parentescos_cache:
        return parentescos_cache[cache_key]

    parentescos = db.query(Parentesco).order_by(Parentesco.parentesco).all()
    resultado = [
        {
            "id_parentesco": parentesco.id_parentesco,
            "parentesco": parentesco.parentesco,
        }
        for parentesco in parentescos
    ]
    parentescos_cache[cache_key] = resultado
    return resultado

@router.get("/estados-cita")
@limiter.limit("30/minute")
def listar_estados_cita(
        request: Request,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(get_current_user),
):
    cache_key = "estados-cita"
    if cache_key in estados_cita_cache:
        return estados_cita_cache[cache_key]

    estados = db.query(EstadoCita).order_by(EstadoCita.estado).all()
    resultado = [
        {
            "id_estado": estado.id_estado,
            "estado": estado.estado,
        }
        for estado in estados
    ]
    estados_cita_cache[cache_key] = resultado
    return resultado

@router.get("/doctores")
@limiter.limit("30/minute")
def listar_doctores(
        request: Request,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(get_current_user),
):
    cache_key = f"doctores:{usuario_actual.id_clinica_tenant}"
    if cache_key in doctores_cache:
        return doctores_cache[cache_key]

    doctores = (
        db.query(Doctor)
        .filter(
            Doctor.activo == True,
            Doctor.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .order_by(Doctor.apellido, Doctor.nombre)
        .all()
    )
    resultado = [
        {
            "id_doctor": doctor.id_doctor,
            "nombre": doctor.nombre,
            "apellido": doctor.apellido,
            "nombre_completo": f"{doctor.nombre} {doctor.apellido}",
            "id_especialidad": doctor.id_especialidad,
            "especialidad": doctor.especialidad.especialidad if doctor.especialidad else None,
            "precio_consulta": float(doctor.precio_consulta.monto) if doctor.precio_consulta else None,
        }
        for doctor in doctores
    ]
    doctores_cache[cache_key] = resultado
    return resultado