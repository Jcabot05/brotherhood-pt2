"""Registro, inicio de sesión y consulta de la cuenta propia.

Implementa la capa de autenticación de la que depende HU-02: hasta que exista
emisión y validación de tokens, el endpoint de creación de citas no puede
exigirlos.

Reglas de negocio cubiertas: RN-05 (hash de contraseñas), RN-06 (vigencia
limitada del token), RN-14 (correo único y con formato válido) y RN-20 (los
mensajes de error no filtran detalles internos).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_sesion
from app.dependencias import usuario_actual
from app.models import (
    CredencialesAcceso,
    RegistroUsuario,
    TokenAcceso,
    UsuarioAutenticado,
)
from app.seguridad import crear_token, hashear_contrasena, verificar_contrasena
from app.tablas import ClienteTabla, UsuarioTabla

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def _id_cliente_de(sesion: Session, id_usuario: int) -> int | None:
    """Devuelve la ficha de cliente asociada a una cuenta, si la tiene."""
    consulta = select(ClienteTabla.id_cliente).where(
        ClienteTabla.id_usuario == id_usuario
    )
    return sesion.scalars(consulta).first()


def _respuesta_con_token(sesion: Session, usuario: UsuarioTabla) -> TokenAcceso:
    """Arma la respuesta de acceso a partir de una cuenta ya verificada."""
    token, expira_en = crear_token(usuario.id_usuario, usuario.correo, usuario.rol)
    return TokenAcceso(
        token_acceso=token,
        expira_en=expira_en,
        usuario=UsuarioAutenticado(
            id_usuario=usuario.id_usuario,
            correo=usuario.correo,
            rol=usuario.rol,
            activo=usuario.activo,
            creado_en=usuario.creado_en,
            id_cliente=_id_cliente_de(sesion, usuario.id_usuario),
        ),
    )


@router.post(
    "/registro",
    response_model=TokenAcceso,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una cuenta de cliente",
)
def registrar(datos: RegistroUsuario, sesion: Session = Depends(get_sesion)):
    """Crea una cuenta de acceso y su ficha de cliente.

    El rol siempre es `cliente`: la creación de administradores no se expone
    por la API, se hace directamente en la base de datos (RN-04).
    """
    correo = datos.correo.strip().lower()

    existente = sesion.scalars(
        select(UsuarioTabla).where(UsuarioTabla.correo == correo)
    ).first()
    if existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta registrada con ese correo.",
        )

    usuario = UsuarioTabla(
        correo=correo,
        contrasena_hash=hashear_contrasena(datos.contrasena),
        rol="cliente",
        activo=True,
    )
    sesion.add(usuario)
    sesion.flush()  # asigna el id sin cerrar la transacción

    cliente = ClienteTabla(
        nombre=datos.nombre,
        telefono=datos.telefono,
        correo=correo,
        id_usuario=usuario.id_usuario,
    )
    sesion.add(cliente)

    # Usuario y cliente se crean en la misma transacción: si la ficha falla,
    # la cuenta no queda registrada a medias.
    sesion.commit()
    sesion.refresh(usuario)

    return _respuesta_con_token(sesion, usuario)


@router.post("/login", response_model=TokenAcceso, summary="Iniciar sesión")
def iniciar_sesion(
    credenciales: CredencialesAcceso, sesion: Session = Depends(get_sesion)
):
    """Verifica las credenciales y emite un token de acceso.

    La respuesta es la misma tanto si el correo no existe como si la
    contraseña es incorrecta, para no revelar qué correos están registrados
    (RN-20).
    """
    correo = credenciales.correo.strip().lower()

    usuario = sesion.scalars(
        select(UsuarioTabla).where(UsuarioTabla.correo == correo)
    ).first()

    credenciales_validas = usuario is not None and verificar_contrasena(
        credenciales.contrasena, usuario.contrasena_hash
    )

    if not credenciales_validas:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta está desactivada.",
        )

    return _respuesta_con_token(sesion, usuario)


@router.get(
    "/yo",
    response_model=UsuarioAutenticado,
    summary="Consultar la cuenta autenticada",
)
def consultar_cuenta(
    usuario: UsuarioTabla = Depends(usuario_actual),
    sesion: Session = Depends(get_sesion),
):
    """Devuelve los datos de la cuenta dueña del token.

    Permite al frontend comprobar si el token sigue vigente (RN-06).
    """
    return UsuarioAutenticado(
        id_usuario=usuario.id_usuario,
        correo=usuario.correo,
        rol=usuario.rol,
        activo=usuario.activo,
        creado_en=usuario.creado_en,
        id_cliente=_id_cliente_de(sesion, usuario.id_usuario),
    )
