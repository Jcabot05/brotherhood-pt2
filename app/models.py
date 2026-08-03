from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class EstadoCita(str, Enum):
    """Estados permitidos de una cita (RF-09)."""

    agendada = "agendada"
    cancelada = "cancelada"
    atendida = "atendida"


# --------------------------------------------------------------------
# Cliente (RF-01)
# --------------------------------------------------------------------


class ClienteBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    telefono: str = Field(min_length=7, max_length=20)
    correo: EmailStr


class ClienteCrear(ClienteBase):
    pass


class ClienteActualizar(ClienteBase):
    pass


class Cliente(ClienteBase):
    id_cliente: int
    creado_en: datetime


# --------------------------------------------------------------------
# Barbero (RF-02)
# --------------------------------------------------------------------


class BarberoBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    especialidad: str | None = Field(default=None, max_length=120)


class BarberoCrear(BarberoBase):
    pass


class BarberoActualizar(BarberoBase):
    pass


class Barbero(BarberoBase):
    id_barbero: int
    creado_en: datetime


# --------------------------------------------------------------------
# Servicio (RF-03, RF-04)
# --------------------------------------------------------------------


class ServicioBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    precio: float = Field(ge=0)
    duracion_min: int = Field(gt=0)


class ServicioCrear(ServicioBase):
    pass


class ServicioActualizar(ServicioBase):
    pass


class Servicio(ServicioBase):
    id_servicio: int
    creado_en: datetime


# --------------------------------------------------------------------
# Cita (RF-05 a RF-09)
# --------------------------------------------------------------------


class CitaCrear(BaseModel):
    id_cliente: int
    id_barbero: int
    id_servicio: int
    fecha_hora: datetime
    estado: EstadoCita = EstadoCita.agendada


class CitaReprogramar(BaseModel):
    """Cambia la fecha y hora de una cita existente (RF-08)."""

    fecha_hora: datetime


class CitaCambiarEstado(BaseModel):
    """Cambia el estado de una cita existente (RF-09)."""

    estado: EstadoCita


class Cita(BaseModel):
    id_cita: int
    id_cliente: int
    id_barbero: int
    id_servicio: int
    fecha_hora: datetime
    estado: EstadoCita
    creado_en: datetime
