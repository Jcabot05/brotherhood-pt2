"""Serializers de cuentas y fichas de cliente."""

from rest_framework import serializers

from apps.usuarios.models import Cliente, Usuario
from apps.usuarios.seguridad import LIMITE_BYTES_CONTRASENA


class UsuarioSerializer(serializers.ModelSerializer):
    """Datos públicos de una cuenta. Nunca expone el hash (RN-05)."""

    id_cliente = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = ["id_usuario", "correo", "rol", "activo", "creado_en", "id_cliente"]

    def get_id_cliente(self, usuario) -> int | None:
        """Ficha de cliente asociada a la cuenta, si la tiene."""
        cliente = getattr(usuario, "cliente", None)
        return cliente.id_cliente if cliente else None


class RegistroSerializer(serializers.Serializer):
    """Alta de una cuenta de cliente junto con su ficha."""

    nombre = serializers.CharField(max_length=120)
    telefono = serializers.CharField(min_length=7, max_length=30)
    correo = serializers.EmailField()
    contrasena = serializers.CharField(min_length=8, write_only=True)

    def validate_correo(self, valor: str) -> str:
        return valor.strip().lower()

    def validate_contrasena(self, valor: str) -> str:
        # bcrypt trunca a 72 bytes: rechazar es preferible a truncar en
        # silencio, que haría equivalentes dos contraseñas distintas.
        if len(valor.encode("utf-8")) > LIMITE_BYTES_CONTRASENA:
            raise serializers.ValidationError(
                f"La contraseña no puede superar los {LIMITE_BYTES_CONTRASENA} bytes."
            )
        return valor


class CredencialesSerializer(serializers.Serializer):
    """Credenciales de inicio de sesión."""

    correo = serializers.EmailField()
    contrasena = serializers.CharField(write_only=True)

    def validate_correo(self, valor: str) -> str:
        return valor.strip().lower()


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = ["id_cliente", "nombre", "telefono", "correo", "creado_en"]
        read_only_fields = ["id_cliente", "creado_en"]


class ClienteCrearSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = ["nombre", "telefono", "correo"]

    def validate_telefono(self, valor: str) -> str:
        if len(valor.strip()) < 7:
            raise serializers.ValidationError(
                "El teléfono debe tener al menos 7 caracteres."
            )
        return valor.strip()
