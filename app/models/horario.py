from sqlalchemy import Column, DateTime, ForeignKey, Integer, Time
from sqlalchemy.orm import relationship
import uuid

from app.core.mysql_uuid import MySQLUUID
from app.database import Base


class HorarioDoctor(Base):
    __tablename__ = "Horarios_Doctor"
    id_horario = Column(MySQLUUID, primary_key=True, default=lambda: str(uuid.uuid4()),)
    id_clinica_tenant = Column(
        MySQLUUID,
        ForeignKey("Clinica.id_clinica_tenant"),
        nullable=False,
    )
    dia = Column(Integer, nullable=False)
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)

    id_doctor = Column(MySQLUUID, ForeignKey("Doctores.id_doctor"), nullable=False)

    doctor = relationship("Doctor")

class BloqueoHorario(Base):
    __tablename__ = "Bloqueo_horario"
    id_bloqueo = Column(MySQLUUID, primary_key=True, default=lambda: str(uuid.uuid4()),)
    id_clinica_tenant = Column(
        MySQLUUID,
        ForeignKey("Clinica.id_clinica_tenant"),
        nullable=False,
    )

    id_doctor = Column(MySQLUUID, ForeignKey("Doctores.id_doctor"), nullable=False)
    fecha_inicio = Column(DateTime, nullable=False)
    fecha_fin = Column(DateTime, nullable=False)

    doctor = relationship("Doctor")
