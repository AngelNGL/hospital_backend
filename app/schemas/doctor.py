from pydantic import BaseModel, EmailStr, Field


class DoctorCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    apellido: str = Field(min_length=1, max_length=150)
    curp: str = Field(min_length=18, max_length=18)
    correo: EmailStr
    telefono: str = Field(min_length=7, max_length=20)
    password: str = Field(min_length=6, max_length=72)
    id_especialidad: str = Field(min_length=12, max_length=12)
    monto_consulta: float = Field(gt=0)

class DoctorUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    apellido: str | None = Field(default=None, min_length=1, max_length=150)
    curp: str | None = Field(default=None, min_length=18, max_length=18)
    id_especialidad: str | None = Field(default=None, min_length=12, max_length=12)
    monto_consulta: float | None = Field(default=None, gt=0)

class DoctorEstadoUpdate(BaseModel):
    activo: bool
