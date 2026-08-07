"""Modelo de la cita agendada."""

from django.db import models

from apps.catalogo.models import Barbero, Servicio
from apps.usuarios.models import Cliente


class Cita(models.Model):
    """Cita entre un cliente y un barbero para un servicio (RF-05).

    `fecha_hora` se almacena siempre en UTC (RN-17); la conversión al huso de
    la barbería ocurre en `apps/citas/agenda.py` y en el frontend.
    """

    AGENDADA = "agendada"
    CANCELADA = "cancelada"
    ATENDIDA = "atendida"
    ESTADOS = [
        (AGENDADA, "Agendada"),
        (CANCELADA, "Cancelada"),
        (ATENDIDA, "Atendida"),
    ]

    id_cita = models.BigAutoField(primary_key=True)
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        db_column="id_cliente",
        related_name="citas",
    )
    barbero = models.ForeignKey(
        Barbero,
        on_delete=models.CASCADE,
        db_column="id_barbero",
        related_name="citas",
    )
    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.CASCADE,
        db_column="id_servicio",
        related_name="citas",
    )
    fecha_hora = models.DateTimeField()
    estado = models.TextField(choices=ESTADOS, default=AGENDADA)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'daw"."cita'
        # Refleja la restricción que `db/schema.sql` ya impone en la base.
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    estado__in=["agendada", "cancelada", "atendida"]
                ),
                name="cita_estado_valido",
            ),
        ]

    def __str__(self):
        return f"Cita {self.id_cita} — {self.fecha_hora:%Y-%m-%d %H:%M} UTC"
