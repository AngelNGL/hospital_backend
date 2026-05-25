from sqlalchemy import Column, String

from app.database import Base


class Especialidad(Base):
    __tablename__ = "Especialidades"
    id_especialidad = Column(String(12), primary_key=True)
    especialidad = Column(String(100), nullable=False, unique=True)

class Parentesco(Base):
    __tablename__ = "Parentesco"
    id_parentesco = Column(String(12), primary_key=True)
    parentesco = Column(String(50), nullable=False, unique=True)


class EstadoCita(Base):
    __tablename__ = "Estado_Cita"
    id_estado = Column(String(12), primary_key=True)
    estado = Column(String(20), nullable=False, unique=True)
