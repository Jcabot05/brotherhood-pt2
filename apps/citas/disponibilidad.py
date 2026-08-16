"""Consulta de horarios libres."""

from datetime import datetime, time, timedelta, timezone

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.citas.agenda import (
    a_local,
    descripcion_horario,
    es_dia_laborable,
    horarios_del_dia,
)
from apps.citas.models import Cita
from apps.citas.reglas import verificar_referencias


@extend_schema(
    parameters=[
        OpenApiParameter("id_barbero", int, required=True),
        OpenApiParameter("id_servicio", int, required=True),
        OpenApiParameter("fecha", str, required=True, description="AAAA-MM-DD"),
    ],
    # La respuesta se arma a mano, sin serializer, así que su forma se declara
    # aquí para que la documentación no la anuncie como vacía.
    responses={
        200: {
            "type": "object",
            "properties": {
                "fecha": {"type": "string", "format": "date"},
                "id_barbero": {"type": "integer"},
                "id_servicio": {"type": "integer"},
                "duracion_min": {"type": "integer"},
                "horario_atencion": {"type": "string"},
                "atiende": {"type": "boolean"},
                "horarios": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "inicio": {"type": "string", "format": "date-time"},
                            "etiqueta": {"type": "string"},
                        },
                    },
                },
            },
        }
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
def consultar_disponibilidad(request):
    """RN-07 y RN-21 a RN-23: horarios en que el barbero puede atender."""
    parametros = request.query_params
    for requerido in ("id_barbero", "id_servicio", "fecha"):
        if not parametros.get(requerido):
            raise ValidationError({requerido: "Este parámetro es obligatorio."})

    id_barbero = int(parametros["id_barbero"])
    id_servicio = int(parametros["id_servicio"])
    try:
        dia = datetime.strptime(parametros["fecha"], "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError({"fecha": "El formato debe ser AAAA-MM-DD."})

    servicio = verificar_referencias(id_barbero, id_servicio)
    duracion = servicio.duracion_min

    base = {
        "fecha": dia,
        "id_barbero": id_barbero,
        "id_servicio": id_servicio,
        "duracion_min": duracion,
        "horario_atencion": descripcion_horario(),
    }

    if not es_dia_laborable(dia):
        return Response({**base, "atiende": False, "horarios": []})

    candidatos = horarios_del_dia(dia, duracion)
    ahora = datetime.now(timezone.utc)

    desde = datetime.combine(dia, time.min, tzinfo=timezone.utc)
    hasta = desde + timedelta(days=2)
    ocupados = [
        (
            cita.fecha_hora,
            cita.fecha_hora + timedelta(minutes=cita.servicio.duracion_min),
        )
        for cita in Cita.objects.filter(
            barbero_id=id_barbero,
            estado=Cita.AGENDADA,
            fecha_hora__gte=desde,
            fecha_hora__lt=hasta,
        ).select_related("servicio")
    ]

    libres = []
    for inicio in candidatos:
        if inicio <= ahora:
            continue
        fin = inicio + timedelta(minutes=duracion)
        if any(comienzo < fin and termina > inicio for comienzo, termina in ocupados):
            continue
        libres.append(
            {
                "inicio": inicio,
                "etiqueta": f"{a_local(inicio):%H:%M} a {a_local(fin):%H:%M}",
            }
        )

    return Response({**base, "atiende": True, "horarios": libres})
