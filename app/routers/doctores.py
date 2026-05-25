from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session
from datetime import date, datetime, time, timedelta

from app.core.cache import disponibilidad_cache
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.database import get_db
from app.models.catalogos import EstadoCita
from app.models.cita import Cita
from app.models.doctor import Doctor
from app.models.usuario import Usuario
from app.models.horario import BloqueoHorario, HorarioDoctor


router = APIRouter(
    prefix="/doctores",
    tags=["Doctores"],
)

def convertir_dia_mysql(fecha: date) -> int:
    # 1=domingo, 2=lunes, 3=martes, 4=miercoles, 5=jueves, 6=viernes, 7=sabado
    return ((fecha.weekday() + 1) % 7) + 1

def sumar_minutos(hora: time, minutos: int) -> time:
    base = datetime.combine(date.today(), hora)
    nueva_hora = base + timedelta(minutes=minutos)
    return nueva_hora.time()

def se_cruzan(inicio_a, fin_a, inicio_b, fin_b) -> bool:
    return not (fin_a <= inicio_b or inicio_a >= fin_b)

@router.get("/{id_doctor}/disponibilidad")
@limiter.limit("30/minute")
def obtener_disponibilidad_doctor(
        request: Request,
        id_doctor: str,
        fecha: date = Query(...),
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(get_current_user),
):
    doctor = (
        db.query(Doctor)
        .filter(
            Doctor.id_doctor == id_doctor,
            Doctor.id_clinica_tenant == usuario_actual.id_clinica_tenant,
            Doctor.activo == True,
        )
        .first()
    )
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor no encontrado",
        )

    cache_key = (
        f"disponibilidad:"
        f"{usuario_actual.id_clinica_tenant}:"
        f"{id_doctor}:"
        f"{fecha.isoformat()}"
    )
    if cache_key in disponibilidad_cache:
        return disponibilidad_cache[cache_key]

    dia_mysql = convertir_dia_mysql(fecha)
    horarios = (
        db.query(HorarioDoctor)
        .filter(
            HorarioDoctor.id_doctor == id_doctor,
            HorarioDoctor.id_clinica_tenant == usuario_actual.id_clinica_tenant,
            HorarioDoctor.dia == dia_mysql,
        )
        .all()
    )
    if not horarios:
        resultado = {
            "id_doctor": id_doctor,
            "fecha": fecha,
            "duracion_minutos": 30,
            "horarios_disponibles": [],
        }
        disponibilidad_cache[cache_key] = resultado
        return resultado

    estado_cancelada = (
        db.query(EstadoCita)
        .filter(EstadoCita.estado == "cancelada")
        .first()
    )
    id_cancelada = estado_cancelada.id_estado if estado_cancelada else None
    citas = (
        db.query(Cita)
        .filter(
            Cita.id_doctor == id_doctor,
            Cita.id_clinica_tenant == usuario_actual.id_clinica_tenant,
            Cita.fecha == fecha,
        )
        .all()
    )
    bloqueos = (
        db.query(BloqueoHorario)
        .filter(
            BloqueoHorario.id_doctor == id_doctor,
            BloqueoHorario.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .all()
    )
    horarios_disponibles = []

    for horario in horarios:
        hora_actual = horario.hora_inicio
        while sumar_minutos(hora_actual, 30) <= horario.hora_fin:
            hora_fin_bloque = sumar_minutos(hora_actual, 30)
            bloque_inicio_dt = datetime.combine(fecha, hora_actual)
            bloque_fin_dt = datetime.combine(fecha, hora_fin_bloque)

            ocupado_por_cita = False
            for cita in citas:
                if id_cancelada is not None and cita.id_estado == id_cancelada:
                    continue
                if se_cruzan(
                    hora_actual, hora_fin_bloque,
                    cita.hora_inicio, cita.hora_fin,
                ):
                    ocupado_por_cita = True
                    break

            ocupado_por_bloqueo = False
            for bloqueo in bloqueos:
                if se_cruzan(
                    bloque_inicio_dt, bloque_fin_dt,
                    bloqueo.fecha_inicio, bloqueo.fecha_fin,
                ):
                    ocupado_por_bloqueo = True
                    break

            if not ocupado_por_cita and not ocupado_por_bloqueo:
                horarios_disponibles.append({
                    "hora_inicio": hora_actual.strftime("%H:%M"),
                    "hora_fin": hora_fin_bloque.strftime("%H:%M"),
                })
            hora_actual = hora_fin_bloque
    resultado = {
        "id_doctor": id_doctor,
        "doctor": f"{doctor.nombre} {doctor.apellido}",
        "fecha": fecha,
        "duracion_minutos": 30,
        "horarios_disponibles": horarios_disponibles,
    }
    disponibilidad_cache[cache_key] = resultado
    return resultado
