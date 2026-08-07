"""Clases de permiso que implementan las reglas de acceso RN-01..RN-04."""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class EsAdmin(BasePermission):
    """Restringe la vista a cuentas con rol de administrador (RN-04)."""

    message = "Esta operación requiere una cuenta de administrador."

    def has_permission(self, request, view) -> bool:
        usuario = request.user
        return usuario is not None and usuario.es_admin


class SoloLecturaPublica(BasePermission):
    """Lectura abierta a cualquiera; escritura sólo para administradores.

    Es el patrón del catálogo: el visitante consulta servicios y barberos sin
    cuenta (RN-01, HU-01), pero modificarlos exige rol de administrador.
    """

    message = "Esta operación requiere una cuenta de administrador."

    def has_permission(self, request, view) -> bool:
        if request.method in SAFE_METHODS:
            return True
        usuario = request.user
        return usuario is not None and usuario.es_admin
