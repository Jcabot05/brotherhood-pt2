"""Vistas de la agenda de citas (RF-05 a RF-09, HU-02)."""

from datetime import datetime, time, timezone

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.citas.models import Cita
from apps.citas.reglas import (
    ConflictoDeAgenda,
    asegurar_futuro,
    asegurar_horario_valido,
    buscar_cita,
    cliente_del_usuario,
    exigir_propiedad,
    verificar_disponibilidad,
    verificar_referencias,
)
from apps.citas.serializers import (
    CitaActualizarSerializer,
    CitaCrearSerializer,
    CitaEstadoSerializer,
    CitaSerializer,
)


class ListaCitas(APIView):
    """Agenda y consulta de citas."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("id_barbero", int, description="Filtrar por barbero"),
            OpenApiParameter("fecha", str, description="Filtrar por día (AAAA-MM-DD)"),
            OpenApiParameter("estado", str, description="Filtrar por estado"),
            OpenApiParameter("skip", int),
            OpenApiParameter("limit", int),
        ],
        responses={200: CitaSerializer(many=True)},
    )
    def get(self, request):
        """RF-06: lista las citas con filtros por barbero, fecha y estado.

        Un cliente ve únicamente sus propias citas (RN-03); el administrador ve
        la agenda completa.
        """
        consulta = Cita.objects.all()

        if not request.user.es_admin:
            cliente = cliente_del_usuario(request.user)
            consulta = consulta.filter(cliente_id=cliente.id_cliente)

        parametros = request.query_params

        if parametros.get("id_barbero"):
            consulta = consulta.filter(barbero_id=parametros["id_barbero"])
        if parametros.get("estado"):
            consulta = consulta.filter(estado=parametros["estado"])
        if parametros.get("fecha"):
            dia = datetime.strptime(parametros["fecha"], "%Y-%m-%d").date()
            consulta = consulta.filter(
                fecha_hora__gte=datetime.combine(dia, time.min, tzinfo=timezone.utc),
                fecha_hora__lte=datetime.combine(dia, time.max, tzinfo=timezone.utc),
            )

        skip = int(parametros.get("skip", 0))
        limite = int(parametros.get("limit", 50))
        consulta = consulta.order_by("fecha_hora")[skip : skip + limite]

        return Response(CitaSerializer(consulta, many=True).data)

    @extend_schema(request=CitaCrearSerializer, responses={201: CitaSerializer})
    def post(self, request):
        """RF-05: agenda una cita a nombre del cliente autenticado.

        La cita se asocia siempre al dueño de la sesión (RN-03), nace en estado
        agendada (RN-10) y sólo se crea si el horario está libre (RN-07) y es
        futuro (RN-08).
        """
        datos = CitaCrearSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        validados = datos.validated_data

        cliente = cliente_del_usuario(request.user)
        inicio = asegurar_futuro(validados["fecha_hora"])
        servicio = verificar_referencias(
            validados["id_barbero"], validados["id_servicio"]
        )

        asegurar_horario_valido(inicio, servicio.duracion_min)
        try:
            verificar_disponibilidad(
                validados["id_barbero"], inicio, servicio.duracion_min
            )
        except ConflictoDeAgenda as error:
            return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)

        cita = Cita.objects.create(
            cliente_id=cliente.id_cliente,
            barbero_id=validados["id_barbero"],
            servicio_id=validados["id_servicio"],
            fecha_hora=inicio,
            estado=Cita.AGENDADA,
        )
        return Response(CitaSerializer(cita).data, status=status.HTTP_201_CREATED)


class DetalleCita(APIView):
    """Consulta, reprograma o cancela una cita."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: CitaSerializer})
    def get(self, request, id_cita: int):
        """RF-06: consulta una cita por su identificador."""
        cita = buscar_cita(id_cita)
        exigir_propiedad(cita, request.user)
        return Response(CitaSerializer(cita).data)

    @extend_schema(request=CitaActualizarSerializer, responses={200: CitaSerializer})
    def put(self, request, id_cita: int):
        """RF-08: reprograma una cita.

        Sólo se reprograma una cita agendada (RN-11): una cancelada o atendida
        ya cerró su ciclo.
        """
        cita = buscar_cita(id_cita)
        exigir_propiedad(cita, request.user)

        if cita.estado != Cita.AGENDADA:
            return Response(
                {
                    "detail": (
                        f"La cita {id_cita} está {cita.estado} y no puede "
                        "reprogramarse."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        datos = CitaActualizarSerializer(data=request.data)
        datos.is_valid(raise_exception=True)

        inicio = asegurar_futuro(datos.validated_data["fecha_hora"])
        # El barbero y el servicio no cambian al reprogramar: se conservan los
        # de la cita y sólo se valida que el nuevo horario sirva.
        duracion = cita.servicio.duracion_min
        asegurar_horario_valido(inicio, duracion)

        try:
            # Se excluye a sí misma: una cita no se solapa consigo.
            verificar_disponibilidad(
                cita.barbero_id,
                inicio,
                duracion,
                id_cita_excluida=id_cita,
            )
        except ConflictoDeAgenda as error:
            return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)

        cita.fecha_hora = inicio
        cita.save(update_fields=["fecha_hora"])

        return Response(CitaSerializer(cita).data)

    @extend_schema(responses={200: CitaSerializer})
    def delete(self, request, id_cita: int):
        """RF-08: cancela una cita.

        Es un borrado lógico: la cita queda en estado cancelada para preservar
        el historial (RN-12), nunca se elimina de la base.
        """
        cita = buscar_cita(id_cita)
        exigir_propiedad(cita, request.user)

        # Cancelar lo ya cancelado no es un error: la operación es idempotente.
        if cita.estado == Cita.CANCELADA:
            return Response(CitaSerializer(cita).data)

        if cita.fecha_hora <= datetime.now(timezone.utc):
            return Response(
                {"detail": "No se puede cancelar una cita que ya ocurrió."},
                status=status.HTTP_409_CONFLICT,
            )

        cita.estado = Cita.CANCELADA
        cita.save(update_fields=["estado"])
        return Response(CitaSerializer(cita).data)


@extend_schema(request=CitaEstadoSerializer, responses={200: CitaSerializer})
@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def cambiar_estado(request, id_cita: int):
    """RF-09: cambia el estado de una cita.

    Marcar como atendida es potestad del negocio, no del cliente (RN-04).
    """
    cita = buscar_cita(id_cita)
    exigir_propiedad(cita, request.user)

    datos = CitaEstadoSerializer(data=request.data)
    datos.is_valid(raise_exception=True)
    nuevo = datos.validated_data["estado"]

    if nuevo == Cita.ATENDIDA and not request.user.es_admin:
        raise PermissionDenied("Sólo la barbería puede marcar una cita como atendida.")

    # Reactivar una cita exige que su horario siga siendo válido y esté libre.
    if nuevo == Cita.AGENDADA and cita.estado != Cita.AGENDADA:
        inicio = asegurar_futuro(cita.fecha_hora)
        asegurar_horario_valido(inicio, cita.servicio.duracion_min)
        try:
            verificar_disponibilidad(
                cita.barbero_id,
                inicio,
                cita.servicio.duracion_min,
                id_cita_excluida=cita.id_cita,
            )
        except ConflictoDeAgenda as error:
            return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)

    cita.estado = nuevo
    cita.save(update_fields=["estado"])
    return Response(CitaSerializer(cita).data)
