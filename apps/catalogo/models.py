"""Modelos del catálogo: barberos y servicios."""

from django.db import models


class Barbero(models.Model):
    """Barbero que atiende citas (RF-02)."""

    id_barbero = models.BigAutoField(primary_key=True)
    nombre = models.TextField()
    especialidad = models.TextField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'daw"."barbero'

    def __str__(self):
        return self.nombre


class Servicio(models.Model):
    """Servicio ofrecido por la barbería (RF-03, RF-04)."""

    id_servicio = models.BigAutoField(primary_key=True)
    nombre = models.TextField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    duracion_min = models.IntegerField()
    # Retiro lógico del catálogo (RN-16): un servicio con citas asociadas no se
    # elimina físicamente, para preservar el historial.
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'daw"."servicio'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(precio__gte=0),
                name="servicio_precio_no_negativo",
            ),
            models.CheckConstraint(
                condition=models.Q(duracion_min__gt=0),
                name="servicio_duracion_positiva",
            ),
        ]

    def __str__(self):
        return self.nombre
