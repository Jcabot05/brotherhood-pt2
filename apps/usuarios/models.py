"""Modelos de acceso al sistema: cuentas de usuario y fichas de cliente.

Corresponde al diagrama entidad-relación de la fase de Diseño. El esquema
físico lo crean los scripts de `db/`; estas clases sólo lo describen.

Todos los modelos van con `managed = False`: la base es una Supabase de un
cliente real y el esquema se administra con SQL revisado a mano, no con
`makemigrations`.
"""

from django.db import models


class Usuario(models.Model):
    """Cuenta de acceso al sistema (Proyecto 04).

    La contraseña se guarda únicamente como hash bcrypt (RN-05): el sistema
    nunca almacena ni puede recuperar el texto plano.
    """

    CLIENTE = "cliente"
    ADMIN = "admin"
    ROLES = [(CLIENTE, "Cliente"), (ADMIN, "Administrador")]

    id_usuario = models.BigAutoField(primary_key=True)
    correo = models.TextField(unique=True)
    contrasena_hash = models.TextField()
    rol = models.TextField(choices=ROLES, default=CLIENTE)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'daw"."usuario'
        # Refleja las restricciones que `db/migracion_01_usuarios.sql` ya
        # impone en la base. Como el modelo es `managed = False`, Django no
        # las crea: quedan como documentación del contrato real.
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rol__in=["cliente", "admin"]),
                name="usuario_rol_valido",
            ),
        ]

    def __str__(self):
        return self.correo

    @property
    def es_admin(self) -> bool:
        return self.rol == self.ADMIN

    # DRF consulta estos atributos en `request.user`. Como no se usa
    # `django.contrib.auth`, se declaran a mano.
    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False


class Cliente(models.Model):
    """Ficha del cliente de la barbería (RF-01)."""

    id_cliente = models.BigAutoField(primary_key=True)
    nombre = models.TextField()
    telefono = models.TextField()
    correo = models.TextField()
    # Nullable: los clientes registrados en el Proyecto 03 no tienen cuenta de
    # acceso asociada y siguen siendo válidos.
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="id_usuario",
        related_name="cliente",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'daw"."cliente'

    def __str__(self):
        return self.nombre
