from datetime import date
from typing import Literal
from pydantic import BaseModel, Field

# usar dropdowns en frontend para estos
Sexo = Literal["masculino", "femenino", "otro"]
ParentescoTipo = Literal["titular", "hijo", "conyuge"]

class PacienteCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    apellido: str = Field(min_length=1, max_length=150)
    sexo: Sexo
    fecha_nacimiento: date
    curp: str = Field(min_length=18, max_length=18)
    parentesco: ParentescoTipo

class PacienteUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    apellido: str | None = Field(default=None, min_length=1, max_length=150)
    sexo: Sexo | None = None
    fecha_nacimiento: date | None = None
    curp: str | None = Field(default=None, min_length=18, max_length=18)
    parentesco: ParentescoTipo | None = None

class PacienteEstadoUpdate(BaseModel):
    activo: bool
