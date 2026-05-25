from datetime import date, time
from pydantic import BaseModel, Field


class CitaCreate(BaseModel):
    id_paciente: str
    id_doctor: str
    fecha: date
    hora_inicio: time
    hora_fin: time | None = None
    motivo: str = Field(min_length=1, max_length=500)

class CitaReprogramar(BaseModel):
    fecha: date
    hora_inicio: time
    hora_fin: time | None = None