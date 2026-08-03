"""Dependencias de autenticación y autorización para los routers.

Reúne las comprobaciones de acceso que las historias de usuario exigen, de modo
que cada router las declare en lugar de repetir la lógica:

- `usuario_actual`      exige un token válido (RN-02).
- `usuario_opcional`    admite token o su ausencia; permite distinguir al
                        visitante del usuario identificado sin cerrar el acceso
                        público (RN-01).
- `requiere_admin`      exige además el rol administrador (RN-04).
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_sesion
from app.seguridad import leer_token
from app.tablas import UsuarioTabla

# `auto_error=False` deja que las dependencias decidan el código de respuesta,
# en lugar de que el esquema de seguridad aborte antes con su propio error.
esquema_bearer = HTTPBearer(auto_error=False, description="Token de acceso")


def _no_autenticado(detalle: str) -> HTTPException:
    """401 con la cabecera que exige la especificación de HTTP para Bearer."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detalle,
        headers={"WWW-Authenticate": "Bearer"},
    )


def usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
    sesion: Session = Depends(get_sesion),
) -> UsuarioTabla:
    """Resuelve el usuario dueño del token (RN-02).

    Responde 401 si falta el token, si es inválido o si expiró (RN-06), y
    también si la cuenta fue desactivada después de emitirse.
    """
    if credenciales is None:
        raise _no_autenticado("Se requiere un token de acceso.")

    contenido = leer_token(credenciales.credentials)
    if contenido is None:
        raise _no_autenticado("El token es inválido o ha expirado.")

    id_usuario = contenido.get("sub")
    if id_usuario is None:
        raise _no_autenticado("El token no identifica a ningún usuario.")

    usuario = sesion.get(UsuarioTabla, int(id_usuario))
    if usuario is None or not usuario.activo:
        raise _no_autenticado("La cuenta no existe o está desactivada.")

    return usuario


def usuario_opcional(
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
    sesion: Session = Depends(get_sesion),
) -> UsuarioTabla | None:
    """Devuelve el usuario si viaja un token válido; `None` en caso contrario.

    Nunca rechaza la petición: el acceso público no debe romperse porque el
    visitante envíe un token caduco (RN-01).
    """
    if credenciales is None:
        return None

    contenido = leer_token(credenciales.credentials)
    if contenido is None:
        return None

    id_usuario = contenido.get("sub")
    if id_usuario is None:
        return None

    usuario = sesion.get(UsuarioTabla, int(id_usuario))
    return usuario if usuario is not None and usuario.activo else None


def requiere_admin(usuario: UsuarioTabla = Depends(usuario_actual)) -> UsuarioTabla:
    """Exige rol administrador (RN-04).

    Distingue los dos casos que el documento separa: sin credenciales, 401;
    con credenciales válidas pero sin permiso, 403 (RN-19).
    """
    if usuario.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta operación requiere permisos de administrador.",
        )
    return usuario
