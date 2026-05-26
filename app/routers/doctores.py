from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError
from datetime import date, datetime, time, timedelta

from app.core.cache import disponibilidad_cache, clear_doctores_cache_for_tenant, clear_disponibilidad_cache_for_doctor
from app.core.rate_limit import limiter
from app.core.security import get_current_user, hash_password
from app.core.permissions import require_any_role, require_role
from app.database import get_db
from app.models.catalogos import EstadoCita, Especialidad
from app.models.cita import Cita
from app.models.doctor import Doctor, PrecioConsulta
from app.models.usuario import Usuario, Rol
from app.models.horario import BloqueoHorario, HorarioDoctor
from app.schemas.doctor import DoctorCreate, DoctorUpdate, DoctorEstadoUpdate
from app.schemas.horario import HorarioCreate, HorarioUpdate
from app.schemas.bloqueo import BloqueoCreate, BloqueoUpdate


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

def obtener_mensaje_mysql(error):
    if hasattr(error, "orig") and error.orig:
        return str(error.orig)
    return str(error)

@router.get("")
@limiter.limit("30/minute")
def listar_doctores_clinica(
        request: Request,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(require_any_role(["admin", "recepcionista"])),
):
    doctores = (
        db.query(Doctor)
        .filter(Doctor.id_clinica_tenant == usuario_actual.id_clinica_tenant)
        .order_by(Doctor.apellido, Doctor.nombre)
        .all()
    )
    return [
        {
            "id_doctor": doctor.id_doctor,
            "id_usuario": doctor.id_usuario,
            "nombre": doctor.nombre,
            "apellido": doctor.apellido,
            "nombre_completo": f"{doctor.nombre} {doctor.apellido}",
            "curp": doctor.curp,
            "activo": doctor.activo,
            "fecha_baja": doctor.fecha_baja,
            "id_especialidad": doctor.id_especialidad,
            "especialidad": doctor.especialidad.especialidad if doctor.especialidad else None,
            "precio_consulta": float(doctor.precio_consulta.monto)
            if doctor.precio_consulta
            else None,
            "correo": doctor.usuario.correo if doctor.usuario else None,
            "telefono": doctor.usuario.telefono if doctor.usuario else None,
        }
        for doctor in doctores
    ]

@router.post("")
@limiter.limit("10/minute")
def crear_doctor(
        request: Request,
        datos: DoctorCreate,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(require_role("admin")),
):
    rol_doctor = (
        db.query(Rol)
        .filter(Rol.rol == "doctor")
        .first()
    )
    if rol_doctor is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No existe el rol doctor en la base de datos",
        )

    especialidad = (
        db.query(Especialidad)
        .filter(Especialidad.id_especialidad == datos.id_especialidad)
        .first()
    )
    if especialidad is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Especialidad no válida",
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

    doctor_existente = (
        db.query(Doctor)
        .filter(
            Doctor.curp == datos.curp,
            Doctor.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .first()
    )
    if doctor_existente is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un doctor registrado con esa CURP en esta clínica",
        )

    nuevo_usuario = Usuario(
        id_clinica_tenant=usuario_actual.id_clinica_tenant,
        correo=datos.correo,
        telefono=datos.telefono,
        password=hash_password(datos.password),
        id_rol=rol_doctor.id_rol,
    )
    try:
        db.add(nuevo_usuario)
        db.flush()

        nuevo_doctor = Doctor(
            id_clinica_tenant=usuario_actual.id_clinica_tenant,
            nombre=datos.nombre,
            apellido=datos.apellido,
            curp=datos.curp,
            activo=True,
            id_usuario=nuevo_usuario.id_usuario,
            id_especialidad=datos.id_especialidad,
        )
        db.add(nuevo_doctor)
        db.flush()

        nuevo_precio = PrecioConsulta(
            id_clinica_tenant=usuario_actual.id_clinica_tenant,
            id_doctor=nuevo_doctor.id_doctor,
            monto=datos.monto_consulta,
        )
        db.add(nuevo_precio)
        db.commit()
        db.refresh(nuevo_doctor)

        clear_doctores_cache_for_tenant(usuario_actual.id_clinica_tenant)
    except (IntegrityError, OperationalError) as error:
        db.rollback()
        mensaje = obtener_mensaje_mysql(error)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo crear el doctor: {mensaje}",
        )
    return {
        "id_doctor": nuevo_doctor.id_doctor,
        "id_usuario": nuevo_doctor.id_usuario,
        "nombre": nuevo_doctor.nombre,
        "apellido": nuevo_doctor.apellido,
        "nombre_completo": f"{nuevo_doctor.nombre} {nuevo_doctor.apellido}",
        "curp": nuevo_doctor.curp,
        "activo": nuevo_doctor.activo,
        "id_especialidad": nuevo_doctor.id_especialidad,
        "especialidad": especialidad.especialidad,
        "precio_consulta": float(nuevo_precio.monto),
        "correo": nuevo_usuario.correo,
        "telefono": nuevo_usuario.telefono,
    }

@router.patch("/{id_doctor}")
@limiter.limit("10/minute")
def actualizar_doctor(
        request: Request,
        id_doctor: str,
        datos: DoctorUpdate,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(require_role("admin")),
):
    doctor = (
        db.query(Doctor)
        .filter(
            Doctor.id_doctor == id_doctor,
            Doctor.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .first()
    )
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor no encontrado",
        )

    if datos.id_especialidad is not None:
        especialidad = (
            db.query(Especialidad)
            .filter(Especialidad.id_especialidad == datos.id_especialidad)
            .first()
        )
        if especialidad is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Especialidad no válida",
            )
        doctor.id_especialidad = datos.id_especialidad

    if datos.curp is not None and datos.curp != doctor.curp:
        doctor_existente = (
            db.query(Doctor)
            .filter(
                Doctor.curp == datos.curp,
                Doctor.id_clinica_tenant == usuario_actual.id_clinica_tenant,
            )
            .first()
        )
        if doctor_existente is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un doctor registrado con esa CURP en esta clínica",
            )
        doctor.curp = datos.curp

    if datos.nombre is not None:
        doctor.nombre = datos.nombre

    if datos.apellido is not None:
        doctor.apellido = datos.apellido

    if datos.monto_consulta is not None:
        if doctor.precio_consulta is None:
            nuevo_precio = PrecioConsulta(
                id_clinica_tenant=usuario_actual.id_clinica_tenant,
                id_doctor=doctor.id_doctor,
                monto=datos.monto_consulta,
            )
            db.add(nuevo_precio)
        else:
            doctor.precio_consulta.monto = datos.monto_consulta
    try:
        db.commit()
        db.refresh(doctor)
        clear_doctores_cache_for_tenant(usuario_actual.id_clinica_tenant)
    except (IntegrityError, OperationalError) as error:
        db.rollback()
        mensaje = obtener_mensaje_mysql(error)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo actualizar el doctor: {mensaje}",
        )
    return {
        "id_doctor": doctor.id_doctor,
        "id_usuario": doctor.id_usuario,
        "nombre": doctor.nombre,
        "apellido": doctor.apellido,
        "nombre_completo": f"{doctor.nombre} {doctor.apellido}",
        "curp": doctor.curp,
        "activo": doctor.activo,
        "fecha_baja": doctor.fecha_baja,
        "id_especialidad": doctor.id_especialidad,
        "especialidad": doctor.especialidad.especialidad if doctor.especialidad else None,
        "precio_consulta": float(doctor.precio_consulta.monto) if doctor.precio_consulta else None,
        "correo": doctor.usuario.correo if doctor.usuario else None,
        "telefono": doctor.usuario.telefono if doctor.usuario else None,
    }

@router.patch("/{id_doctor}/estado")
@limiter.limit("10/minute")
def actualizar_estado_doctor(
        request: Request,
        id_doctor: str,
        datos: DoctorEstadoUpdate,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(require_role("admin")),
):
    doctor = (
        db.query(Doctor)
        .filter(
            Doctor.id_doctor == id_doctor,
            Doctor.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .first()
    )
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor no encontrado",
        )
    doctor.activo = datos.activo
    if datos.activo is False:
        doctor.fecha_baja = datetime.now()
    else:
        doctor.fecha_baja = None
    try:
        db.commit()
        db.refresh(doctor)
        clear_doctores_cache_for_tenant(usuario_actual.id_clinica_tenant)
    except (IntegrityError, OperationalError) as error:
        db.rollback()
        mensaje = obtener_mensaje_mysql(error)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo actualizar el estado del doctor: {mensaje}",
        )
    return {
        "id_doctor": doctor.id_doctor,
        "nombre": doctor.nombre,
        "apellido": doctor.apellido,
        "nombre_completo": f"{doctor.nombre} {doctor.apellido}",
        "activo": doctor.activo,
        "fecha_baja": doctor.fecha_baja,
    }

@router.get("/{id_doctor}/horarios")
@limiter.limit("30/minute")
def listar_horarios_doctor(
        request: Request,
        id_doctor: str,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(require_any_role(["admin", "recepcionista", "doctor"])),
):
    doctor = (
        db.query(Doctor)
        .filter(
            Doctor.id_doctor == id_doctor,
            Doctor.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .first()
    )
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor no encontrado",
        )

    rol_actual = usuario_actual.rol.rol if usuario_actual.rol else None
    if rol_actual == "doctor" and doctor.id_usuario != usuario_actual.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puedes consultar tus propios horarios",
        )

    horarios = (
        db.query(HorarioDoctor)
        .filter(
            HorarioDoctor.id_doctor == id_doctor,
            HorarioDoctor.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .order_by(HorarioDoctor.dia, HorarioDoctor.hora_inicio)
        .all()
    )
    return [
        {
            "id_horario": horario.id_horario,
            "id_doctor": horario.id_doctor,
            "dia": horario.dia,
            "hora_inicio": horario.hora_inicio,
            "hora_fin": horario.hora_fin,
        }
        for horario in horarios
    ]

@router.post("/{id_doctor}/horarios")
@limiter.limit("10/minute")
def crear_horario_doctor(
        request: Request,
        id_doctor: str,
        datos: HorarioCreate,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(require_role("admin")),
):
    doctor = (
        db.query(Doctor)
        .filter(
            Doctor.id_doctor == id_doctor,
            Doctor.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .first()
    )
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor no encontrado",
        )

    if datos.hora_fin <= datos.hora_inicio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La hora de fin debe ser mayor a la hora de inicio",
        )
    nuevo_horario = HorarioDoctor(
        id_clinica_tenant=usuario_actual.id_clinica_tenant,
        id_doctor=id_doctor,
        dia=datos.dia,
        hora_inicio=datos.hora_inicio,
        hora_fin=datos.hora_fin,
    )
    try:
        db.add(nuevo_horario)
        db.commit()
        db.refresh(nuevo_horario)
        clear_disponibilidad_cache_for_doctor(
            id_clinica_tenant=usuario_actual.id_clinica_tenant,
            id_doctor=id_doctor,
        )
    except (IntegrityError, OperationalError) as error:
        db.rollback()
        mensaje = obtener_mensaje_mysql(error)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo crear el horario: {mensaje}",
        )
    return {
        "id_horario": nuevo_horario.id_horario,
        "id_doctor": nuevo_horario.id_doctor,
        "dia": nuevo_horario.dia,
        "hora_inicio": nuevo_horario.hora_inicio,
        "hora_fin": nuevo_horario.hora_fin,
        "mensaje": "Horario creado correctamente",
    }

@router.patch("/horarios/{id_horario}")
@limiter.limit("10/minute")
def actualizar_horario_doctor(
        request: Request,
        id_horario: str,
        datos: HorarioUpdate,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(require_role("admin")),
):
    horario = (
        db.query(HorarioDoctor)
        .filter(
            HorarioDoctor.id_horario == id_horario,
            HorarioDoctor.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .first()
    )
    if horario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Horario no encontrado",
        )

    nuevo_dia = datos.dia if datos.dia is not None else horario.dia
    nueva_hora_inicio = datos.hora_inicio if datos.hora_inicio is not None else horario.hora_inicio
    nueva_hora_fin = datos.hora_fin if datos.hora_fin is not None else horario.hora_fin
    if nueva_hora_fin <= nueva_hora_inicio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La hora de fin debe ser mayor a la hora de inicio",
        )

    horario.dia = nuevo_dia
    horario.hora_inicio = nueva_hora_inicio
    horario.hora_fin = nueva_hora_fin
    try:
        db.commit()
        db.refresh(horario)
        clear_disponibilidad_cache_for_doctor(
            id_clinica_tenant=usuario_actual.id_clinica_tenant,
            id_doctor=horario.id_doctor,
        )
    except (IntegrityError, OperationalError) as error:
        db.rollback()
        mensaje = obtener_mensaje_mysql(error)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo actualizar el horario: {mensaje}",
        )
    return {
        "id_horario": horario.id_horario,
        "id_doctor": horario.id_doctor,
        "dia": horario.dia,
        "hora_inicio": horario.hora_inicio,
        "hora_fin": horario.hora_fin,
        "mensaje": "Horario actualizado correctamente",
    }

@router.delete("/horarios/{id_horario}")
@limiter.limit("10/minute")
def eliminar_horario_doctor(
        request: Request,
        id_horario: str,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(require_role("admin")),
):
    horario = (
        db.query(HorarioDoctor)
        .filter(
            HorarioDoctor.id_horario == id_horario,
            HorarioDoctor.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .first()
    )
    if horario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Horario no encontrado",
        )
    id_doctor = horario.id_doctor
    try:
        db.delete(horario)
        db.commit()
        clear_disponibilidad_cache_for_doctor(
            id_clinica_tenant=usuario_actual.id_clinica_tenant,
            id_doctor=id_doctor,
        )
    except (IntegrityError, OperationalError) as error:
        db.rollback()
        mensaje = obtener_mensaje_mysql(error)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo eliminar el horario: {mensaje}",
        )
    return {
        "id_horario": id_horario,
        "mensaje": "Horario eliminado correctamente",
    }

@router.get("/{id_doctor}/bloqueos")
@limiter.limit("30/minute")
def listar_bloqueos_doctor(
        request: Request,
        id_doctor: str,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(require_any_role(["admin", "recepcionista", "doctor"])),
):
    doctor = (
        db.query(Doctor)
        .filter(
            Doctor.id_doctor == id_doctor,
            Doctor.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .first()
    )
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor no encontrado",
        )

    rol_actual = usuario_actual.rol.rol if usuario_actual.rol else None
    if rol_actual == "doctor" and doctor.id_usuario != usuario_actual.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puedes consultar tus propios bloqueos",
        )

    bloqueos = (
        db.query(BloqueoHorario)
        .filter(
            BloqueoHorario.id_doctor == id_doctor,
            BloqueoHorario.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .order_by(BloqueoHorario.fecha_inicio)
        .all()
    )
    return [
        {
            "id_bloqueo": bloqueo.id_bloqueo,
            "id_doctor": bloqueo.id_doctor,
            "fecha_inicio": bloqueo.fecha_inicio,
            "fecha_fin": bloqueo.fecha_fin,
        }
        for bloqueo in bloqueos
    ]

@router.post("/{id_doctor}/bloqueos")
@limiter.limit("10/minute")
def crear_bloqueo_doctor(
        request: Request,
        id_doctor: str,
        datos: BloqueoCreate,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(require_role("admin")),
):
    doctor = (
        db.query(Doctor)
        .filter(
            Doctor.id_doctor == id_doctor,
            Doctor.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .first()
    )
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor no encontrado",
        )

    if datos.fecha_fin <= datos.fecha_inicio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de fin debe ser mayor a la fecha de inicio",
        )

    nuevo_bloqueo = BloqueoHorario(
        id_clinica_tenant=usuario_actual.id_clinica_tenant,
        id_doctor=id_doctor,
        fecha_inicio=datos.fecha_inicio,
        fecha_fin=datos.fecha_fin,
    )
    try:
        db.add(nuevo_bloqueo)
        db.commit()
        db.refresh(nuevo_bloqueo)
        clear_disponibilidad_cache_for_doctor(
            id_clinica_tenant=usuario_actual.id_clinica_tenant,
            id_doctor=id_doctor,
        )
    except (IntegrityError, OperationalError) as error:
        db.rollback()
        mensaje = obtener_mensaje_mysql(error)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo crear el bloqueo: {mensaje}",
        )
    return {
        "id_bloqueo": nuevo_bloqueo.id_bloqueo,
        "id_doctor": nuevo_bloqueo.id_doctor,
        "fecha_inicio": nuevo_bloqueo.fecha_inicio,
        "fecha_fin": nuevo_bloqueo.fecha_fin,
        "mensaje": "Bloqueo creado correctamente",
    }

@router.patch("/bloqueos/{id_bloqueo}")
@limiter.limit("10/minute")
def actualizar_bloqueo_doctor(
        request: Request,
        id_bloqueo: str,
        datos: BloqueoUpdate,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(require_role("admin")),
):
    bloqueo = (
        db.query(BloqueoHorario)
        .filter(
            BloqueoHorario.id_bloqueo == id_bloqueo,
            BloqueoHorario.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .first()
    )
    if bloqueo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bloqueo no encontrado",
        )

    nueva_fecha_inicio = (
        datos.fecha_inicio if datos.fecha_inicio is not None else bloqueo.fecha_inicio
    )
    nueva_fecha_fin = (
        datos.fecha_fin if datos.fecha_fin is not None else bloqueo.fecha_fin
    )
    if nueva_fecha_fin <= nueva_fecha_inicio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de fin debe ser mayor a la fecha de inicio",
        )
    bloqueo.fecha_inicio = nueva_fecha_inicio
    bloqueo.fecha_fin = nueva_fecha_fin
    try:
        db.commit()
        db.refresh(bloqueo)
        clear_disponibilidad_cache_for_doctor(
            id_clinica_tenant=usuario_actual.id_clinica_tenant,
            id_doctor=bloqueo.id_doctor,
        )
    except (IntegrityError, OperationalError) as error:
        db.rollback()
        mensaje = obtener_mensaje_mysql(error)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo actualizar el bloqueo: {mensaje}",
        )
    return {
        "id_bloqueo": bloqueo.id_bloqueo,
        "id_doctor": bloqueo.id_doctor,
        "fecha_inicio": bloqueo.fecha_inicio,
        "fecha_fin": bloqueo.fecha_fin,
        "mensaje": "Bloqueo actualizado correctamente",
    }

@router.delete("/bloqueos/{id_bloqueo}")
@limiter.limit("10/minute")
def eliminar_bloqueo_doctor(
        request: Request,
        id_bloqueo: str,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(require_role("admin")),
):
    bloqueo = (
        db.query(BloqueoHorario)
        .filter(
            BloqueoHorario.id_bloqueo == id_bloqueo,
            BloqueoHorario.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .first()
    )
    if bloqueo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bloqueo no encontrado",
        )
    id_doctor = bloqueo.id_doctor
    try:
        db.delete(bloqueo)
        db.commit()
        clear_disponibilidad_cache_for_doctor(
            id_clinica_tenant=usuario_actual.id_clinica_tenant,
            id_doctor=id_doctor,
        )
    except (IntegrityError, OperationalError) as error:
        db.rollback()
        mensaje = obtener_mensaje_mysql(error)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo eliminar el bloqueo: {mensaje}",
        )
    return {
        "id_bloqueo": id_bloqueo,
        "mensaje": "Bloqueo eliminado correctamente",
    }

@router.get("/{id_doctor}")
@limiter.limit("30/minute")
def obtener_doctor_por_id(
        request: Request,
        id_doctor: str,
        db: Session = Depends(get_db),
        usuario_actual: Usuario = Depends(require_any_role(["admin", "recepcionista"])),
):
    doctor = (
        db.query(Doctor)
        .filter(
            Doctor.id_doctor == id_doctor,
            Doctor.id_clinica_tenant == usuario_actual.id_clinica_tenant,
        )
        .first()
    )
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor no encontrado",
        )
    return {
        "id_doctor": doctor.id_doctor,
        "id_usuario": doctor.id_usuario,
        "nombre": doctor.nombre,
        "apellido": doctor.apellido,
        "nombre_completo": f"{doctor.nombre} {doctor.apellido}",
        "curp": doctor.curp,
        "activo": doctor.activo,
        "fecha_baja": doctor.fecha_baja,
        "id_especialidad": doctor.id_especialidad,
        "especialidad": doctor.especialidad.especialidad if doctor.especialidad else None,
        "precio_consulta": float(doctor.precio_consulta.monto) if doctor.precio_consulta else None,
        "correo": doctor.usuario.correo if doctor.usuario else None,
        "telefono": doctor.usuario.telefono if doctor.usuario else None,
    }

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
