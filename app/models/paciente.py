from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
import uuid

from app.core.mysql_uuid import MySQLUUID
from app.database import Base


class Paciente(Base):
    __tablename__ = "paciente"
    id_paciente = Column(MySQLUUID, primary_key=True, default=lambda: str(uuid.uuid4()),)
    id_clinica_tenant = Column(
        MySQLUUID,
        ForeignKey("clinica.id_clinica_tenant"),
        nullable=False,
    )
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(150), nullable=False)
    sexo = Column(String(20), nullable=False)
    fecha_nacimiento = Column(Date, nullable=False)
    curp = Column(String(18), nullable=False, unique=True)
    activo = Column(Boolean, default=True)
    fecha_baja = Column(DateTime, nullable=True)

    id_usuario = Column(MySQLUUID, ForeignKey("usuario.id_usuario"), nullable=False)
    id_parentesco = Column(String(12), ForeignKey("parentesco.id_parentesco"), nullable=False)

    parentesco = relationship("Parentesco")
    usuario = relationship("Usuario")
