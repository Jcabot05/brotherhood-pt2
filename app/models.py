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
    # RN-16: un servicio retirado del catálogo conserva su registro y queda
    # marcado como inactivo. El alta y la edición no reciben este campo: se
    # gobierna con DELETE (retirar) y con el endpoint de reactivación.
    activo: bool
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


# --------------------------------------------------------------------
# Autenticación (Proyecto 04 — RN-02 a RN-06)
# --------------------------------------------------------------------


class RolUsuario(str, Enum):
    """Roles reconocidos por el sistema (RN-04)."""

    cliente = "cliente"
    admin = "admin"


class RegistroUsuario(BaseModel):
    """Alta de una cuenta de acceso junto con su ficha de cliente.

    El registro crea el usuario y el cliente asociado en una sola operación,
    de modo que quien se registra queda en condiciones de agendar (HU-02).
    """

    correo: EmailStr
    contrasena: str = Field(min_length=8, max_length=72)
    nombre: str = Field(min_length=1, max_length=120)
    telefono: str = Field(min_length=7, max_length=20)


class CredencialesAcceso(BaseModel):
    correo: EmailStr
    contrasena: str = Field(min_length=1, max_length=72)


class Usuario(BaseModel):
    """Datos públicos de una cuenta. Nunca incluye el hash de la contraseña."""

    id_usuario: int
    correo: EmailStr
    rol: RolUsuario
    activo: bool
    creado_en: datetime


class UsuarioAutenticado(Usuario):
    """Cuenta junto con la ficha de cliente que le corresponde, si existe."""

    id_cliente: int | None = None


class TokenAcceso(BaseModel):
    token_acceso: str
    tipo_token: str = "bearer"
    expira_en: int = Field(description="Vigencia del token en segundos.")
    usuario: UsuarioAutenticado
