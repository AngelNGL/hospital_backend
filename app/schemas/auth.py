from pydantic import BaseModel, EmailStr


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
