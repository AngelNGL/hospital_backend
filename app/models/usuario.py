from sqlalchemy import Column, ForeignKey, String, Boolean, DateTime
from sqlalchemy.orm import relationship

from app.core.mysql_uuid import MySQLUUID
from app.database import Base


class Clinica(Base):
    __tablename__ = "Clinica"
    id_clinica_tenant = Column(MySQLUUID, primary_key=True)
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, nullable=False)
    usuarios = relationship("Usuario", back_populates="clinica")

class Rol(Base):
    __tablename__ = "Roles"
    id_rol = Column(String(12), primary_key=True)
    rol = Column(String(20), nullable=False, unique=True)

    usuarios = relationship("Usuario", back_populates="rol")

class Usuario(Base):
    __tablename__ = "Usuario"
    id_usuario = Column(MySQLUUID, primary_key=True)
    id_clinica_tenant = Column(
        MySQLUUID,
        ForeignKey("Clinica.id_clinica_tenant"),
        nullable=False,
    )
    correo = Column(String(100), nullable=False, unique=True)
    telefono = Column(String(20), nullable=False, unique=True)
    password = Column(String(255), nullable=False)

    id_rol = Column(String(12), ForeignKey("Roles.id_rol"), nullable=False)
    rol = relationship("Rol", back_populates="usuarios")
    clinica = relationship("Clinica", back_populates="usuarios")
