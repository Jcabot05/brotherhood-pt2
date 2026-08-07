"""Traducción de errores al contrato de respuesta que el proyecto ya publicó.

Dos comportamientos de la versión FastAPI que deben conservarse:

1. Los errores de validación responden **422** con la forma
   `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}`.
   DRF, por defecto, responde 400 con `{"campo": ["mensaje"]}`. El criterio de
   aceptación de `docs/01_analisis.md` exige el 422 con el detalle del campo
   que falló, y el frontend lo interpreta campo por campo, así que se traduce
   aquí en vez de cambiar el contrato ya entregado.

2. Las violaciones de integridad de PostgreSQL se traducen a códigos HTTP con
   sentido de negocio en lugar de un 500 genérico.
"""

from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.serializers import as_serializer_error
from rest_framework.views import exception_handler as manejador_base
from rest_framework.exceptions import ValidationError

# Mapa de SQLSTATE de PostgreSQL al código HTTP que corresponde.
_CODIGOS_POSTGRES = {
    "23505": (
        status.HTTP_409_CONFLICT,
        "Ya existe un registro con esos datos.",
    ),
    "23503": (
        status.HTTP_404_NOT_FOUND,
        "Alguno de los registros referidos no existe.",
    ),
    "23514": (
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Los datos no cumplen una restricción de la base.",
    ),
}


def _aplanar(detalle, prefijo=("body",)):
    """Convierte el dict de errores de DRF a la lista de items de Pydantic.

    DRF anida por campo (`{"correo": ["..."]}`); el contrato publicado espera
    una lista plana de `{loc, msg, type}` donde `loc` es la ruta al campo.
    """
    items = []

    if isinstance(detalle, dict):
        for campo, valor in detalle.items():
            items.extend(_aplanar(valor, prefijo + (campo,)))
    elif isinstance(detalle, list):
        for elemento in detalle:
            if isinstance(elemento, (dict, list)):
                items.extend(_aplanar(elemento, prefijo))
            else:
                items.append(_item(elemento, prefijo))
    else:
        items.append(_item(detalle, prefijo))

    return items


def _item(mensaje, prefijo):
    """Arma un item de error preservando el `code` de DRF como `type`."""
    codigo = getattr(mensaje, "code", None) or "invalid"
    item = {
        "loc": list(prefijo),
        "msg": str(mensaje),
        # El frontend conmuta sobre `type` para redactar el motivo en español.
        "type": _TIPOS_EQUIVALENTES.get(codigo, codigo),
    }
    return item


# Equivalencias entre los `code` de DRF y los `type` de Pydantic, para que el
# frontend siga reconociendo los motivos que ya traducía.
_TIPOS_EQUIVALENTES = {
    "required": "missing",
    "null": "missing",
    "blank": "string_too_short",
    "min_length": "string_too_short",
    "max_length": "string_too_long",
    "invalid_choice": "enum",
    "datetime": "datetime_parsing",
    "date": "date_parsing",
    "invalid_email": "value_error",
    "min_value": "greater_than_equal",
    "max_value": "less_than_equal",
}


def manejador_de_excepciones(exc, context):
    """Punto de entrada configurado en `REST_FRAMEWORK.EXCEPTION_HANDLER`."""

    # Violaciones de integridad: PostgreSQL las señala con un SQLSTATE que
    # dice exactamente qué falló. Django envuelve el error del driver, así que
    # el código hay que leerlo de la excepción original encadenada.
    if isinstance(exc, IntegrityError):
        original = exc.__cause__
        sqlstate = getattr(original, "sqlstate", None)
        codigo_http, mensaje = _CODIGOS_POSTGRES.get(
            sqlstate,
            (status.HTTP_500_INTERNAL_SERVER_ERROR, "Error de integridad en la base."),
        )
        return Response({"detail": mensaje}, status=codigo_http)

    respuesta = manejador_base(exc, context)

    # Errores de validación: 400 → 422 con la forma publicada.
    if isinstance(exc, ValidationError) and respuesta is not None:
        detalle = as_serializer_error(exc)
        respuesta.data = {"detail": _aplanar(detalle)}
        respuesta.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    return respuesta
