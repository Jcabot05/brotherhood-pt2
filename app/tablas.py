"""Definición de las tablas del esquema `daw` para SQLAlchemy.

Corresponde al diagrama entidad-relación de la fase de Diseño. El esquema
físico se crea con `db/schema.sql`; estas clases lo describen para el ORM.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
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


class ClienteTabla(Base):
    __tablename__ = "cliente"
    __table_args__ = {"schema": "daw"}

    id_cliente: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    telefono: Mapped[str] = mapped_column(Text, nullable=False)
    correo: Mapped[str] = mapped_column(Text, nullable=False)
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
