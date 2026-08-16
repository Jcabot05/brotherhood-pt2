"""Serializers de la agenda."""

from rest_framework import serializers

from apps.citas.models import Cita


class CitaSerializer(serializers.ModelSerializer):
    """Representación de una cita. Los ids van planos, como en la API previa."""

    id_cliente = serializers.IntegerField(source="cliente_id", read_only=True)
    id_barbero = serializers.IntegerField(source="barbero_id", read_only=True)
    id_servicio = serializers.IntegerField(source="servicio_id", read_only=True)

    class Meta:
        model = Cita
        fields = [
            "id_cita",
            "id_cliente",
            "id_barbero",
            "id_servicio",
            "fecha_hora",
            "estado",
            "creado_en",
        ]


class CitaCrearSerializer(serializers.Serializer):
    """Datos para agendar.

    No acepta `id_cliente` ni `estado` a propósito: la cita se ata siempre al
    dueño de la sesión (RN-03) y nace en estado agendada (RN-10). Aceptarlos
    permitiría reservar a nombre de otro.
    """

    id_barbero = serializers.IntegerField()
    id_servicio = serializers.IntegerField()
    fecha_hora = serializers.DateTimeField()


class CitaActualizarSerializer(serializers.Serializer):
    """Datos para reprogramar una cita (RF-08).

    Sólo cambia la fecha y hora: reprogramar es mover la cita, no convertirla
    en otra. Cambiar de barbero o de servicio equivale a agendar de nuevo.
    """

    fecha_hora = serializers.DateTimeField()


class CitaEstadoSerializer(serializers.Serializer):
    """Cambio de estado de una cita."""

    estado = serializers.ChoiceField(choices=Cita.ESTADOS)


class HorarioSerializer(serializers.Serializer):
    inicio = serializers.DateTimeField()
    etiqueta = serializers.CharField()


class DisponibilidadSerializer(serializers.Serializer):
    fecha = serializers.DateField()
    id_barbero = serializers.IntegerField()
    id_servicio = serializers.IntegerField()
    duracion_min = serializers.IntegerField()
    atiende = serializers.BooleanField()
    horario_atencion = serializers.CharField()
    horarios = HorarioSerializer(many=True)
