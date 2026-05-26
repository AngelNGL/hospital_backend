from pydantic import BaseModel, EmailStr, Field
from datetime import date
from typing import Literal


class LoginRequest(BaseModel):
    correo: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    id_usuario: str
    id_clinica_tenant: str
    correo: EmailStr
    rol: str

Sexo = Literal["masculino", "femenino", "otro"]
class RegisterRequest(BaseModel):
    id_clinica_tenant: str
    correo: EmailStr
    telefono: str = Field(min_length=7, max_length=20)
    password: str = Field(min_length=6, max_length=72)
    nombre: str = Field(min_length=1, max_length=100)
    apellido: str = Field(min_length=1, max_length=150)
    sexo: Sexo
    fecha_nacimiento: date
    curp: str = Field(min_length=18, max_length=18)