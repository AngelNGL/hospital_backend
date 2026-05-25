from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import relationship
import uuid

from app.core.mysql_uuid import MySQLUUID
from app.database import Base


class Doctor(Base):
    __tablename__ = "Doctores"
    id_doctor = Column(MySQLUUID, primary_key=True, default=lambda: str(uuid.uuid4()),)
    id_clinica_tenant = Column(
        MySQLUUID,
        ForeignKey("Clinica.id_clinica_tenant"),
        nullable=False,
    )
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(150), nullable=False)
    curp = Column(String(18), nullable=False, unique=True)
    activo = Column(Boolean, default=True)
    fecha_baja = Column(DateTime, nullable=True)

    id_usuario = Column(MySQLUUID, ForeignKey("Usuario.id_usuario"), nullable=False)
    id_especialidad = Column(String(12), ForeignKey("Especialidades.id_especialidad"), nullable=False)

    especialidad = relationship("Especialidad")
    usuario = relationship("Usuario")
    precio_consulta = relationship("PrecioConsulta", back_populates="doctor", uselist=False)

class PrecioConsulta(Base):
    __tablename__ = "Precios_Consulta"
    id_precio = Column(MySQLUUID, primary_key=True, default=lambda: str(uuid.uuid4()),)
    id_clinica_tenant = Column(
        MySQLUUID,
        ForeignKey("Clinica.id_clinica_tenant"),
        nullable=False,
    )
    id_doctor = Column(MySQLUUID, ForeignKey("Doctores.id_doctor"), nullable=False, unique=True)
    monto = Column(Numeric(10, 2), nullable=False)

    doctor = relationship("Doctor", back_populates="precio_consulta")
