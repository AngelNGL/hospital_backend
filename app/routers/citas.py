from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError
from datetime import date, datetime, timedelta

from app.core.cache import clear_disponibilidad_cache_for_doctor
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.core.permissions import require_any_role
from app.database import get_db
from app.models.cita import Cita
from app.models.doctor import Doctor
from app.models.paciente import Paciente
from app.models.usuario import Usuario
from app.models.catalogos import EstadoCita
from app.schemas.cita import CitaCreate, CitaReprogramar


router = APIRouter(
    prefix="/citas",
    tags=["Citas"],
)

def sumar_30_minutos(hora):
    base = datetime.combine(date.today(), hora)
    nueva_hora = base + timedelta(minutes=30)
    return nueva_hora.time()

def obtener_mensaje_mysql(error):
    if hasattr(error, "orig") and error.orig:
        return str(error.orig)
    return str(error)

@router.get("")
@limiter.limit("30/minute")
def listar_citas_clinica(
        request: Request,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(require_any_role(["admin", "recepcionista"])),
):
    citas = (
        db.query(Cita)
        .filter(Cita.id_clinica_tenant == usuario_actual.id_clinica_tenant)
        .order_by(Cita.fecha.desc(), Cita.hora_inicio.desc())
        .all()
    )
    return [
        {
            "id_cita": cita.id_cita,
            "fecha": cita.fecha,
            "hora_inicio": cita.hora_inicio,
            "hora_fin": cita.hora_fin,
            "motivo": cita.motivo,
            "estado": cita.estado.estado if cita.estado else None,
            "paciente": {
                "id_paciente": cita.paciente.id_paciente,
                "nombre": cita.paciente.nombre,
                "apellido": cita.paciente.apellido,
                "nombre_completo": f"{cita.paciente.nombre} {cita.paciente.apellido}",
            } if cita.paciente else None,
            "doctor": {
                "id_doctor": cita.doctor.id_doctor,
                "nombre": cita.doctor.nombre,
                "apellido": cita.doctor.apellido,
                "nombre_completo": f"{cita.doctor.nombre} {cita.doctor.apellido}",
                "especialidad": cita.doctor.especialidad.especialidad
                if cita.doctor.especialidad
                else None,
            } if cita.doctor else None,
        }
        for cita in citas
    ]

@router.get("/me")
@limiter.limit("30/minute")
def listar_mis_citas(
        request: Request,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(get_current_user),
):
    rol_actual = usuario_actual.rol.rol if usuario_actual.rol else None
    query = db.query(Cita).filter(
        Cita.id_clinica_tenant == usuario_actual.id_clinica_tenant
    )

    if rol_actual == "cliente":
        query = (
            query
            .join(Paciente, Cita.id_paciente == Paciente.id_paciente)
            .filter(Paciente.id_usuario == usuario_actual.id_usuario)
        )

    elif rol_actual == "doctor":
        doctor = (
            db.query(Doctor)
            .filter(Doctor.id_usuario == usuario_actual.id_usuario)
            .first()
        )
        if doctor is None:
            return []
        query = query.filter(Cita.id_doctor == doctor.id_doctor)

    elif rol_actual in ["admin", "recepcionista"]:
        pass

    else:
        return []

    citas = (
        query
        .order_by(Cita.fecha.desc(), Cita.hora_inicio.desc())
        .all()
    )
    return [
        {
            "id_cita": cita.id_cita,
            "fecha": cita.fecha,
            "hora_inicio": cita.hora_inicio,
            "hora_fin": cita.hora_fin,
            "motivo": cita.motivo,
            "estado": cita.estado.estado if cita.estado else None,
            "paciente": {
                "id_paciente": cita.paciente.id_paciente,
                "nombre": cita.paciente.nombre,
                "apellido": cita.paciente.apellido,
                "nombre_completo": f"{cita.paciente.nombre} {cita.paciente.apellido}",
            } if cita.paciente else None,
            "doctor": {
                "id_doctor": cita.doctor.id_doctor,
                "nombre": cita.doctor.nombre,
                "apellido": cita.doctor.apellido,
                "nombre_completo": f"{cita.doctor.nombre} {cita.doctor.apellido}",
                "especialidad": cita.doctor.especialidad.especialidad
                if cita.doctor.especialidad
                else None,
            } if cita.doctor else None,
        }
        for cita in citas
    ]

@router.get("/{id_cita}")
@limiter.limit("30/minute")
def obtener_cita_por_id(
        request: Request,
        id_cita: str,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(require_any_role(["admin", "recepcionista"])),
):
    cita = (
        db.query(Cita)
        .filter(
            Cita.id_cita == id_cita,
            Cita.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .first()
    )
    if cita is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada",
        )
    return {
        "id_cita": cita.id_cita,
        "fecha": cita.fecha,
        "hora_inicio": cita.hora_inicio,
        "hora_fin": cita.hora_fin,
        "motivo": cita.motivo,
        "estado": cita.estado.estado if cita.estado else None,
        "paciente": {
            "id_paciente": cita.paciente.id_paciente,
            "nombre": cita.paciente.nombre,
            "apellido": cita.paciente.apellido,
            "nombre_completo": f"{cita.paciente.nombre} {cita.paciente.apellido}",
            "curp": cita.paciente.curp,
            "sexo": cita.paciente.sexo,
            "fecha_nacimiento": cita.paciente.fecha_nacimiento,
        } if cita.paciente else None,
        "doctor": {
            "id_doctor": cita.doctor.id_doctor,
            "nombre": cita.doctor.nombre,
            "apellido": cita.doctor.apellido,
            "nombre_completo": f"{cita.doctor.nombre} {cita.doctor.apellido}",
            "especialidad": cita.doctor.especialidad.especialidad
            if cita.doctor.especialidad
            else None,
        } if cita.doctor else None,
    }

@router.post("")
@limiter.limit("10/minute")
def crear_cita(
        request: Request,
        datos: CitaCreate,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(get_current_user),
):
    rol_actual = usuario_actual.rol.rol if usuario_actual.rol else None

    paciente = (
        db.query(Paciente)
        .filter(
            Paciente.id_paciente == datos.id_paciente,
            Paciente.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .first()
    )
    if paciente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado",
        )
    if not paciente.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede agendar cita para un paciente inactivo",
        )

    doctor = (
        db.query(Doctor)
        .filter(
            Doctor.id_doctor == datos.id_doctor,
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

    if rol_actual == "cliente":
        if paciente.id_usuario != usuario_actual.id_usuario:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes crear citas para pacientes que no pertenecen a tu cuenta",
            )
        # para el cliente siempre seran citas de 30 minutos
        hora_fin = sumar_30_minutos(datos.hora_inicio)

    elif rol_actual == "doctor":
        doctor_actual = (
            db.query(Doctor)
            .filter(
                Doctor.id_usuario == usuario_actual.id_usuario,
                Doctor.id_clinica_tenant == usuario_actual.id_clinica_tenant,
            )
            .first()
        )
        if doctor_actual is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El usuario no tiene un doctor asociado",
            )
        if doctor_actual.id_doctor != datos.id_doctor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Un doctor solo puede crear citas para sí mismo",
            )
        hora_fin = datos.hora_fin if datos.hora_fin else sumar_30_minutos(datos.hora_inicio)

    elif rol_actual in ["admin", "recepcionista"]:
        hora_fin = datos.hora_fin if datos.hora_fin else sumar_30_minutos(datos.hora_inicio)

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para crear citas",
        )

    if hora_fin <= datos.hora_inicio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La hora de fin debe ser después a la hora de inicio",
        )

    estado_pendiente = (
        db.query(EstadoCita)
        .filter(EstadoCita.estado == "pendiente")
        .first()
    )
    if estado_pendiente is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No existe el estado pendiente en la base de datos",
        )

    nueva_cita = Cita(
        id_clinica_tenant=usuario_actual.id_clinica_tenant,
        fecha=datos.fecha,
        hora_inicio=datos.hora_inicio,
        hora_fin=hora_fin,
        motivo=datos.motivo,
        id_estado=estado_pendiente.id_estado,
        id_paciente=datos.id_paciente,
        id_doctor=datos.id_doctor,
    )
    try:
        db.add(nueva_cita)
        db.commit()
        db.refresh(nueva_cita)
        clear_disponibilidad_cache_for_doctor(
            id_clinica_tenant=usuario_actual.id_clinica_tenant,
            id_doctor=datos.id_doctor,
            fecha=str(datos.fecha),
        )
    except (IntegrityError, OperationalError) as error:
        db.rollback()
        mensaje = obtener_mensaje_mysql(error)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo crear la cita: {mensaje}",
        )
    return {
        "id_cita": nueva_cita.id_cita,
        "fecha": nueva_cita.fecha,
        "hora_inicio": nueva_cita.hora_inicio,
        "hora_fin": nueva_cita.hora_fin,
        "motivo": nueva_cita.motivo,
        "estado": estado_pendiente.estado,
        "paciente": {
            "id_paciente": paciente.id_paciente,
            "nombre": paciente.nombre,
            "apellido": paciente.apellido,
            "nombre_completo": f"{paciente.nombre} {paciente.apellido}",
        },
        "doctor": {
            "id_doctor": doctor.id_doctor,
            "nombre": doctor.nombre,
            "apellido": doctor.apellido,
            "nombre_completo": f"{doctor.nombre} {doctor.apellido}",
            "especialidad": doctor.especialidad.especialidad if doctor.especialidad else None,
        },
    }

@router.patch("/{id_cita}/cancelar")
@limiter.limit("10/minute")
def cancelar_cita(
        request: Request,
        id_cita: str,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(get_current_user),
):
    rol_actual = usuario_actual.rol.rol if usuario_actual.rol else None

    cita = (
        db.query(Cita)
        .filter(
            Cita.id_cita == id_cita,
            Cita.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .first()
    )
    if cita is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada",
        )

    estado_cancelada = (
        db.query(EstadoCita)
        .filter(EstadoCita.estado == "cancelada")
        .first()
    )
    if estado_cancelada is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No existe el estado cancelada en la base de datos",
        )
    if cita.id_estado == estado_cancelada.id_estado:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La cita ya está cancelada",
        )

    if rol_actual == "cliente":
        if cita.paciente is None or cita.paciente.id_usuario != usuario_actual.id_usuario:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes cancelar citas que no pertenecen a tu usuario",
            )
        fecha_hora_cita = datetime.combine(cita.fecha, cita.hora_inicio)
        ahora = datetime.now()
        if fecha_hora_cita - ahora < timedelta(hours=24):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo puedes cancelar una cita con al menos 24 horas de anticipación",
            )

    elif rol_actual == "doctor":
        doctor_actual = (
            db.query(Doctor)
            .filter(
                Doctor.id_usuario == usuario_actual.id_usuario,
                Doctor.id_clinica_tenant == usuario_actual.id_clinica_tenant,
            )
            .first()
        )
        if doctor_actual is None or cita.id_doctor != doctor_actual.id_doctor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puedes cancelar tus propias citas",
            )

    elif rol_actual in ["admin", "recepcionista"]:
        pass

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para cancelar citas",
        )

    cita.id_estado = estado_cancelada.id_estado
    try:
        db.commit()
        db.refresh(cita)
        clear_disponibilidad_cache_for_doctor(
            id_clinica_tenant=usuario_actual.id_clinica_tenant,
            id_doctor=cita.id_doctor,
            fecha=str(cita.fecha),
        )
    except (IntegrityError, OperationalError) as error:
        db.rollback()
        mensaje = obtener_mensaje_mysql(error)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo cancelar la cita: {mensaje}",
        )
    return {
        "id_cita": cita.id_cita,
        "fecha": cita.fecha,
        "hora_inicio": cita.hora_inicio,
        "hora_fin": cita.hora_fin,
        "estado": estado_cancelada.estado,
        "mensaje": "Cita cancelada correctamente",
    }

@router.patch("/{id_cita}/reprogramar")
@limiter.limit("10/minute")
def reprogramar_cita(
        request: Request,
        id_cita: str,
        datos: CitaReprogramar,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(get_current_user),
):
    rol_actual = usuario_actual.rol.rol if usuario_actual.rol else None

    cita = (
        db.query(Cita)
        .filter(
            Cita.id_cita == id_cita,
            Cita.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .first()
    )
    if cita is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada",
        )

    estado_cancelada = (
        db.query(EstadoCita)
        .filter(EstadoCita.estado == "cancelada")
        .first()
    )
    if estado_cancelada and cita.id_estado == estado_cancelada.id_estado:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede reprogramar una cita cancelada",
        )

    if rol_actual == "cliente":
        if cita.paciente is None or cita.paciente.id_usuario != usuario_actual.id_usuario:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes reprogramar citas que no pertenecen a tu usuario",
            )
        fecha_hora_cita_actual = datetime.combine(cita.fecha, cita.hora_inicio)
        ahora = datetime.now()
        if fecha_hora_cita_actual - ahora < timedelta(hours=24):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo puedes reprogramar una cita con al menos 24 horas de anticipación",
            )
        nueva_hora_fin = sumar_30_minutos(datos.hora_inicio)

    elif rol_actual == "doctor":
        doctor_actual = (
            db.query(Doctor)
            .filter(
                Doctor.id_usuario == usuario_actual.id_usuario,
                Doctor.id_clinica_tenant == usuario_actual.id_clinica_tenant,
            )
            .first()
        )
        if doctor_actual is None or cita.id_doctor != doctor_actual.id_doctor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puedes reprogramar tus propias citas",
            )
        nueva_hora_fin = datos.hora_fin if datos.hora_fin else sumar_30_minutos(datos.hora_inicio)

    elif rol_actual in ["admin", "recepcionista"]:
        nueva_hora_fin = datos.hora_fin if datos.hora_fin else sumar_30_minutos(datos.hora_inicio)

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para reprogramar citas",
        )

    if nueva_hora_fin <= datos.hora_inicio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La hora de fin debe ser mayor a la hora de inicio",
        )
    fecha_anterior = cita.fecha
    id_doctor_anterior = cita.id_doctor
    cita.fecha = datos.fecha
    cita.hora_inicio = datos.hora_inicio
    cita.hora_fin = nueva_hora_fin
    try:
        db.commit()
        db.refresh(cita)
        clear_disponibilidad_cache_for_doctor(
            id_clinica_tenant=usuario_actual.id_clinica_tenant,
            id_doctor=id_doctor_anterior,
            fecha=str(fecha_anterior),
        )
        clear_disponibilidad_cache_for_doctor(
            id_clinica_tenant=usuario_actual.id_clinica_tenant,
            id_doctor=cita.id_doctor,
            fecha=str(cita.fecha),
        )
    except (IntegrityError, OperationalError) as error:
        db.rollback()
        mensaje = obtener_mensaje_mysql(error)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo reprogramar la cita: {mensaje}",
        )
    return {
        "id_cita": cita.id_cita,
        "fecha": cita.fecha,
        "hora_inicio": cita.hora_inicio,
        "hora_fin": cita.hora_fin,
        "estado": cita.estado.estado if cita.estado else None,
        "mensaje": "Cita reprogramada correctamente",
    }

@router.patch("/{id_cita}/completar")
@limiter.limit("10/minute")
def completar_cita(
    request: Request,
    id_cita: str,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(
        require_any_role(["admin", "recepcionista", "doctor"])
    ),
):
    cita = (
        db.query(Cita)
        .filter(
            Cita.id_cita == id_cita,
            Cita.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .first()
    )
    if cita is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada",
        )

    rol_actual = usuario_actual.rol.rol if usuario_actual.rol else None
    if rol_actual == "doctor":
        doctor_actual = (
            db.query(Doctor)
            .filter(
                Doctor.id_usuario == usuario_actual.id_usuario,
                Doctor.id_clinica_tenant == usuario_actual.id_clinica_tenant,
            )
            .first()
        )
        if doctor_actual is None or cita.id_doctor != doctor_actual.id_doctor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puedes completar tus propias citas",
            )

    estado_completada = (
        db.query(EstadoCita)
        .filter(EstadoCita.estado == "completada")
        .first()
    )
    if estado_completada is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No existe el estado completada en la base de datos",
        )

    if cita.estado and cita.estado.estado == "cancelada":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede completar una cita cancelada",
        )
    cita.id_estado = estado_completada.id_estado
    try:
        db.commit()
        db.refresh(cita)
    except (IntegrityError, OperationalError) as error:
        db.rollback()
        mensaje = obtener_mensaje_mysql(error)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo completar la cita: {mensaje}",
        )
    return {
        "id_cita": cita.id_cita,
        "fecha": cita.fecha,
        "hora_inicio": cita.hora_inicio,
        "hora_fin": cita.hora_fin,
        "estado": cita.estado.estado if cita.estado else None,
        "mensaje": "Cita marcada como completada correctamente",
    }
