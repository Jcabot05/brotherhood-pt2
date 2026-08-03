"""Definición de las tablas del esquema `daw` para SQLAlchemy.

Corresponde al diagrama entidad-relación de la fase de Diseño. El esquema
físico se crea con `db/schema.sql`; estas clases lo describen para el ORM.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UsuarioTabla(Base):
    """Cuenta de acceso al sistema (Proyecto 04).

    La contraseña se guarda únicamente como hash bcrypt (RN-05): el sistema
    nunca almacena ni puede recuperar el texto plano.
    """

    __tablename__ = "usuario"
    __table_args__ = (
        CheckConstraint("rol in ('cliente', 'admin')", name="usuario_rol_valido"),
        {"schema": "daw"},
    )

    id_usuario: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    correo: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    contrasena_hash: Mapped[str] = mapped_column(Text, nullable=False)
    rol: Mapped[str] = mapped_column(Text, nullable=False, default="cliente")
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ClienteTabla(Base):
    __tablename__ = "cliente"
    __table_args__ = {"schema": "daw"}

    id_cliente: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    telefono: Mapped[str] = mapped_column(Text, nullable=False)
    correo: Mapped[str] = mapped_column(Text, nullable=False)
    # Nullable: los clientes registrados en el Proyecto 03 no tienen cuenta de
    # acceso asociada y siguen siendo válidos.
    id_usuario: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("daw.usuario.id_usuario", ondelete="SET NULL"),
        unique=True,
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class BarberoTabla(Base):
    __tablename__ = "barbero"
    __table_args__ = {"schema": "daw"}

    id_barbero: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    especialidad: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ServicioTabla(Base):
    __tablename__ = "servicio"
    __table_args__ = (
        CheckConstraint("precio >= 0", name="servicio_precio_no_negativo"),
        CheckConstraint("duracion_min > 0", name="servicio_duracion_positiva"),
        {"schema": "daw"},
    )

    id_servicio: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    precio: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    duracion_min: Mapped[int] = mapped_column(Integer, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CitaTabla(Base):
    __tablename__ = "cita"
    __table_args__ = (
        CheckConstraint(
            "estado in ('agendada', 'cancelada', 'atendida')",
            name="cita_estado_valido",
        ),
        {"schema": "daw"},
    )

    id_cita: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_cliente: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("daw.cliente.id_cliente", ondelete="CASCADE"), nullable=False
    )
    id_barbero: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("daw.barbero.id_barbero", ondelete="CASCADE"), nullable=False
    )
    id_servicio: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("daw.servicio.id_servicio", ondelete="CASCADE"), nullable=False
    )
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estado: Mapped[str] = mapped_column(Text, nullable=False, default="agendada")
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
