from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.cache import clinicas_publicas_cache
from app.core.rate_limit import limiter
from app.database import get_db
from app.models.usuario import Clinica, DatosClinica


router = APIRouter(
    prefix="/clinicas",
    tags=["Clínicas"],
)

@router.get("/publicas")
@limiter.limit("30/minute")
def listar_clinicas_publicas(
        request: Request,
        db: Session = Depends(get_db),
):
    cache_key = "clinicas_publicas"
    if cache_key in clinicas_publicas_cache:
        return clinicas_publicas_cache[cache_key]

    clinicas = (
        db.query(DatosClinica)
        .join(Clinica, DatosClinica.id_clinica_tenant == Clinica.id_clinica_tenant)
        .filter(Clinica.activo == True)
        .order_by(DatosClinica.nombre)
        .all()
    )
    resultado = [
        {
            "id_clinica_tenant": clinica.id_clinica_tenant,
            "nombre": clinica.nombre,
            "direccion": clinica.direccion,
            "telefono": clinica.telefono,
            "horario_atencion": clinica.horario_atencion,
            "correo": clinica.correo,
        }
        for clinica in clinicas
    ]
    clinicas_publicas_cache[cache_key] = resultado
    return resultado
