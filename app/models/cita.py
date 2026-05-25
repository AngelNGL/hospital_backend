from sqlalchemy import Column, Date, ForeignKey, String, Text, Time
from sqlalchemy.orm import relationship
import uuid

from app.core.mysql_uuid import MySQLUUID
from app.database import Base


class Cita(Base):
    __tablename__ = "Cita"
    id_cita = Column(MySQLUUID, primary_key=True, default=lambda: str(uuid.uuid4()),)
    id_clinica_tenant = Column(
        MySQLUUID,
        ForeignKey("Clinica.id_clinica_tenant"),
        nullable=False,
    )
    fecha = Column(Date, nullable=False)
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)
    motivo = Column(Text, nullable=False)

    id_estado = Column(String(12), ForeignKey("Estado_Cita.id_estado"), nullable=False)
    id_paciente = Column(MySQLUUID, ForeignKey("Paciente.id_paciente"), nullable=False)
    id_doctor = Column(MySQLUUID, ForeignKey("Doctores.id_doctor"), nullable=True)

    estado = relationship("EstadoCita")
    paciente = relationship("Paciente")
    doctor = relationship("Doctor")
