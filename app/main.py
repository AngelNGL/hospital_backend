from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.database import get_db
from app.routers import auth, catalogos, pacientes, citas, doctores
from app.core.rate_limit import limiter

# Imports para ayudar a SQLAlchemy
from app.models.usuario import Usuario, Rol
from app.models.catalogos import Especialidad, Parentesco, EstadoCita
from app.models.doctor import Doctor, PrecioConsulta
from app.models.paciente import Paciente
from app.models.cita import Cita
from app.models.horario import HorarioDoctor, BloqueoHorario


app = FastAPI(
    title="Sistema de Citas Médicas",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", # comun en React/Next, agregar otro si se usa otro en front
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(catalogos.router)
app.include_router(pacientes.router)
app.include_router(citas.router)
app.include_router(doctores.router)

@app.get("/")
def root():
    return {
        "message": "cambio de prueba"
    }

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "database": "connected"
    }
