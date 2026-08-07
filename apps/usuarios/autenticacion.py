"""Autenticación por cookie httpOnly, con cabecera Bearer como alternativa.

Por qué cookie y no `localStorage`/`sessionStorage`: un token que JavaScript
puede leer es un token que cualquier XSS puede robar. Marcada `httpOnly`, la
cookie deja de ser accesible desde el código de la página, así que una
inyección de script ya no basta para llevarse la sesión.

Se mantiene el soporte de `Authorization: Bearer` porque la API también se
consume desde clientes que no son navegadores (`tests/prueba_endpoints.py`) y
porque es lo que permite usar el botón "Authorize" de la documentación.
"""

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from apps.usuarios.models import Usuario
from apps.usuarios.seguridad import leer_token


def _token_de_la_peticion(request) -> str | None:
    """Extrae el token de la petición.

    La cabecera `Authorization` tiene prioridad sobre la cookie: enviarla es
    un acto deliberado de quien llama, mientras que la cookie la adjunta el
    navegador sola. Si mandara la cookie, un cliente que guardó una sesión
    previa no podría actuar como otra cuenta aunque lo pidiera expresamente.
    """
    cabecera = request.headers.get("Authorization", "")
    if cabecera.startswith("Bearer "):
        token = cabecera.removeprefix("Bearer ").strip()
        if token:
            return token

    return request.COOKIES.get(settings.COOKIE_SESION) or None


class AutenticacionCookieOBearer(BaseAuthentication):
    """Resuelve el usuario de la petición a partir de su token."""

    # Hace que DRF responda 401 (y no 403) cuando falta credencial.
    def authenticate_header(self, request) -> str:
        return "Bearer"

    def authenticate(self, request):
        token = _token_de_la_peticion(request)
        if not token:
            # Sin credencial: DRF lo resuelve como anónimo. Son las clases de
            # permiso las que deciden si la vista lo admite.
            return None

        contenido = leer_token(token)
        if contenido is None:
            raise AuthenticationFailed("El token es inválido o ha expirado.")

        id_usuario = contenido.get("sub")
        if not id_usuario:
            raise AuthenticationFailed("El token no identifica a ningún usuario.")

        # Se relee el usuario de la base en lugar de confiar en los claims: así
        # una cuenta desactivada deja de funcionar de inmediato, aunque su
        # token siga vigente, y un `rol` obsoleto en un token viejo no sirve
        # para escalar privilegios.
        usuario = Usuario.objects.filter(pk=id_usuario, activo=True).first()
        if usuario is None:
            raise AuthenticationFailed("La cuenta no existe o está desactivada.")

        return (usuario, token)
