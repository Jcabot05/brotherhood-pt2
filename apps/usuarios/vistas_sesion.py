"""Registro, acceso y cierre de sesión."""

from django.conf import settings
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.usuarios.models import Cliente, Usuario
from apps.usuarios.seguridad import (
    crear_token,
    hashear_contrasena,
    verificar_contrasena,
)
from apps.usuarios.serializers import (
    CredencialesSerializer,
    RegistroSerializer,
    UsuarioSerializer,
)


def _adjuntar_cookie(respuesta, token: str, expira_en: int):
    """Entrega el token como cookie httpOnly.

    `httponly` es el punto de todo esto: impide que el JavaScript de la página
    lea el token, de modo que una inyección de script no basta para robar la
    sesión.
    """
    respuesta.set_cookie(
        key=settings.COOKIE_SESION,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SEGURA,
        samesite=settings.COOKIE_SAMESITE,
        max_age=expira_en,  # se alinea con la vigencia del token (RN-06)
        path="/",
    )
    return respuesta


def _respuesta_de_acceso(usuario: Usuario, codigo: int):
    """Arma la respuesta de acceso a partir de una cuenta ya verificada.

    El token viaja en la cookie y también en el cuerpo: lo primero es para el
    navegador, lo segundo para los clientes de API que usan cabecera Bearer.
    """
    token, expira_en = crear_token(usuario.id_usuario, usuario.correo, usuario.rol)
    respuesta = Response(
        {
            "token_acceso": token,
            "tipo_token": "bearer",
            "expira_en": expira_en,
            "usuario": UsuarioSerializer(usuario).data,
        },
        status=codigo,
    )
    return _adjuntar_cookie(respuesta, token, expira_en)


@extend_schema(request=RegistroSerializer, responses={201: UsuarioSerializer})
@api_view(["POST"])
@permission_classes([AllowAny])
def registrar(request):
    """Crea una cuenta de acceso y su ficha de cliente.

    El rol siempre es `cliente`: la creación de administradores no se expone
    por la API, se hace directamente en la base de datos (RN-04).
    """
    datos = RegistroSerializer(data=request.data)
    datos.is_valid(raise_exception=True)
    validados = datos.validated_data
    correo = validados["correo"]

    if Usuario.objects.filter(correo=correo).exists():
        return Response(
            {"detail": "Ya existe una cuenta registrada con ese correo."},
            status=status.HTTP_409_CONFLICT,
        )

    # Cuenta y ficha se crean en la misma transacción: si la ficha falla, la
    # cuenta no queda registrada a medias.
    with transaction.atomic():
        usuario = Usuario.objects.create(
            correo=correo,
            contrasena_hash=hashear_contrasena(validados["contrasena"]),
            rol=Usuario.CLIENTE,
            activo=True,
        )
        Cliente.objects.create(
            nombre=validados["nombre"],
            telefono=validados["telefono"],
            correo=correo,
            usuario=usuario,
        )

    return _respuesta_de_acceso(usuario, status.HTTP_201_CREATED)


@extend_schema(request=CredencialesSerializer, responses={200: UsuarioSerializer})
@api_view(["POST"])
@permission_classes([AllowAny])
def iniciar_sesion(request):
    """Verifica las credenciales y abre la sesión.

    La respuesta es la misma tanto si el correo no existe como si la
    contraseña es incorrecta, para no revelar qué correos están registrados
    (RN-20).
    """
    datos = CredencialesSerializer(data=request.data)
    datos.is_valid(raise_exception=True)
    validados = datos.validated_data

    usuario = Usuario.objects.filter(correo=validados["correo"]).first()
    credenciales_validas = usuario is not None and verificar_contrasena(
        validados["contrasena"], usuario.contrasena_hash
    )

    if not credenciales_validas:
        return Response(
            {"detail": "Correo o contraseña incorrectos."},
            status=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not usuario.activo:
        return Response(
            {"detail": "La cuenta está desactivada."},
            status=status.HTTP_403_FORBIDDEN,
        )

    return _respuesta_de_acceso(usuario, status.HTTP_200_OK)


@extend_schema(request=None, responses={204: None})
@api_view(["POST"])
@permission_classes([AllowAny])
def cerrar_sesion(request):
    """Borra la cookie de sesión.

    No exige token: cerrar una sesión ya expirada debe ser idempotente, no un
    error. Los atributos deben coincidir con los de `set_cookie`, o el
    navegador no reconoce la cookie como la misma y no la borra.
    """
    respuesta = Response(status=status.HTTP_204_NO_CONTENT)
    respuesta.delete_cookie(
        key=settings.COOKIE_SESION,
        path="/",
        samesite=settings.COOKIE_SAMESITE,
    )
    return respuesta


@extend_schema(responses={200: UsuarioSerializer})
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def consultar_cuenta(request):
    """Devuelve los datos de la cuenta dueña de la sesión.

    Es el modo en que el frontend comprueba si la sesión sigue viva, ahora que
    no puede leer el token (RN-06).
    """
    return Response(UsuarioSerializer(request.user).data)
