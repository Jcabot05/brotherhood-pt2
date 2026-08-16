"""Serializers del catálogo."""

from rest_framework import serializers

from apps.catalogo.models import Barbero, Servicio


class BarberoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Barbero
        fields = ["id_barbero", "nombre", "especialidad", "creado_en"]
        read_only_fields = ["id_barbero", "creado_en"]


class ServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servicio
        fields = [
            "id_servicio",
            "nombre",
            "precio",
            "duracion_min",
            "activo",
            "creado_en",
        ]
        read_only_fields = ["id_servicio", "activo", "creado_en"]

    def validate_precio(self, valor):
        if valor < 0:
            raise serializers.ValidationError("El precio no puede ser negativo.")
        return valor

    def validate_duracion_min(self, valor):
        if valor <= 0:
            raise serializers.ValidationError(
                "La duración debe ser mayor que cero minutos."
            )
        return valor
