"""Vistas de la agenda de citas (RF-05 a RF-09, HU-02)."""

from datetime import datetime, time, timedelta, timezone

from django.db.models import DateTimeField, DurationField, ExpressionWrapper, F
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalogo.models import Barbero, Servicio
from apps.citas.agenda import (
    HorarioInvalido,
    descripcion_horario,
    es_dia_laborable,
    horarios_del_dia,
    verificar_horario,
)
from apps.citas.models import Cita
from apps.citas.serializers import (
    CitaActualizarSerializer,
    CitaCrearSerializer,
    CitaEstadoSerializer,
    CitaSerializer,
)
from apps.usuarios.models import Cliente


# --- Ayudas ----------------------------------------------------------------


def _cliente_del_usuario(usuario) -> Cliente:
    """Ficha de cliente de la cuenta autenticada."""
    cliente = Cliente.objects.filter(usuario=usuario).first()
    if cliente is None:
        raise NotFound(
            "La cuenta no tiene una ficha de cliente asociada. "
            "Contacte con la barbería."
        )
    return cliente


def _asegurar_futuro(fecha_hora: datetime) -> datetime:
    """RN-08: no se agenda en el pasado."""
    momento = (
        fecha_hora
        if fecha_hora.tzinfo is not None
        else fecha_hora.replace(tzinfo=timezone.utc)
    )

    if momento <= datetime.now(timezone.utc):
        raise ValidationError("La cita debe agendarse en una fecha y hora futuras.")
    return momento


def _asegurar_horario_valido(inicio: datetime, duracion_min: int) -> None:
    """RN-21 a RN-23: la cita debe caber en el horario de atención.

    Traduce el motivo concreto a un 422, de modo que quien reserva sepa por qué
    ese horario no sirve en lugar de recibir un rechazo genérico (RN-19).
    """
    try:
        verificar_horario(inicio, duracion_min)
    except HorarioInvalido as error:
        raise ValidationError(str(error)) from error


def _verificar_referencias(id_barbero: int, id_servicio: int) -> Servicio:
    """RN-13: barbero y servicio deben existir. Devuelve el servicio."""
    if not Barbero.objects.filter(pk=id_barbero).exists():
        raise NotFound(f"No existe un barbero con id {id_barbero}.")

    servicio = Servicio.objects.filter(pk=id_servicio).first()
    if servicio is None:
        raise NotFound(f"No existe un servicio con id {id_servicio}.")
    return servicio


def _citas_solapadas(
    id_barbero: int,
    inicio: datetime,
    duracion_min: int,
    id_cita_excluida: int | None = None,
):
    """Citas del barbero cuyo intervalo choca con el solicitado.

    El intervalo de una cita va desde su fecha/hora hasta esa hora más la
    duración de su servicio. Dos intervalos se solapan cuando cada uno empieza
    antes de que termine el otro; comparar sólo la hora de inicio dejaría pasar
    una cita que arranca en mitad de otra.

    Sólo compiten las citas agendadas: una cancelada o atendida libera su
    horario (RN-11).
    """
    fin = inicio + timedelta(minutes=duracion_min)

    # El fin de cada cita existente se calcula en la base: su hora de inicio
    # más la duración de su servicio, como intervalo de PostgreSQL.
    # `output_field` es obligatorio: Django no puede deducir el tipo de
    # multiplicar un intervalo por un entero.
    duracion_como_intervalo = ExpressionWrapper(
        timedelta(minutes=1) * F("servicio__duracion_min"),
        output_field=DurationField(),
    )

    consulta = (
        Cita.objects.filter(
            barbero_id=id_barbero,
            estado=Cita.AGENDADA,
            fecha_hora__lt=fin,
        )
        .annotate(
            fin_existente=ExpressionWrapper(
                F("fecha_hora") + duracion_como_intervalo,
                output_field=DateTimeField(),
            )
        )
        .filter(fin_existente__gt=inicio)
    )

    if id_cita_excluida is not None:
        consulta = consulta.exclude(pk=id_cita_excluida)

    return consulta


def _verificar_disponibilidad(
    id_barbero: int,
    inicio: datetime,
    duracion_min: int,
    id_cita_excluida: int | None = None,
) -> None:
    """RN-07: el barbero no puede tener dos citas con intervalos solapados."""
    if _citas_solapadas(id_barbero, inicio, duracion_min, id_cita_excluida).exists():
        fin = inicio + timedelta(minutes=duracion_min)
        raise ConflictoDeAgenda(
            f"El barbero {id_barbero} ya tiene una cita que se solapa con el "
            f"intervalo solicitado ({inicio.isoformat()} — {fin.isoformat()}). "
            "Seleccione otro horario."
        )


class ConflictoDeAgenda(Exception):
    """Choque de horarios. Se traduce a 409 en las vistas."""


def _exigir_propiedad(cita: Cita, usuario) -> None:
    """RN-03: un cliente sólo opera sobre sus propias citas.

    El administrador queda exento: gestiona la agenda completa del negocio.
    """
    if usuario.es_admin:
        return

    cliente = _cliente_del_usuario(usuario)
    if cita.cliente_id != cliente.id_cliente:
        raise PermissionDenied(
            "No puede operar sobre una cita que pertenece a otro cliente."
        )


def _buscar_cita(id_cita: int) -> Cita:
    cita = Cita.objects.filter(pk=id_cita).first()
    if cita is None:
        raise NotFound(f"No existe una cita con id {id_cita}.")
    return cita


# --- Agendar y listar (HU-02) ---------------------------------------------


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
            cliente = _cliente_del_usuario(request.user)
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

        cliente = _cliente_del_usuario(request.user)
        inicio = _asegurar_futuro(validados["fecha_hora"])
        servicio = _verificar_referencias(
            validados["id_barbero"], validados["id_servicio"]
        )

        _asegurar_horario_valido(inicio, servicio.duracion_min)
        try:
            _verificar_disponibilidad(
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


@extend_schema(
    parameters=[
        OpenApiParameter("id_barbero", int, required=True),
        OpenApiParameter("id_servicio", int, required=True),
        OpenApiParameter("fecha", str, required=True, description="AAAA-MM-DD"),
    ]
)
@api_view(["GET"])
@permission_classes([AllowAny])
def consultar_disponibilidad(request):
    """Devuelve los horarios en que ese barbero puede atender ese servicio.

    Cruza el horario de atención (RN-21 a RN-23) con las citas ya agendadas
    (RN-07), de modo que quien reserva elija entre opciones válidas en lugar de
    descubrir los conflictos al enviar el formulario.

    Es de acceso público: consultar disponibilidad no compromete la agenda ni
    revela datos de otros clientes, sólo qué franjas están libres.
    """
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

    servicio = _verificar_referencias(id_barbero, id_servicio)
    duracion = servicio.duracion_min

    base = {
        "fecha": dia,
        "id_barbero": id_barbero,
        "id_servicio": id_servicio,
        "duracion_min": duracion,
        "horario_atencion": descripcion_horario(),
    }

    # Día no laborable: se responde con la lista vacía y el motivo, no con un
    # error. No hay nada malo en la petición.
    if not es_dia_laborable(dia):
        return Response({**base, "atiende": False, "horarios": []})

    candidatos = horarios_del_dia(dia, duracion)
    ahora = datetime.now(timezone.utc)

    # Una sola consulta para todo el día, en lugar de una por horario.
    desde = datetime.combine(dia, time.min, tzinfo=timezone.utc)
    hasta = desde + timedelta(days=2)
    ocupados = [
        (cita.fecha_hora, cita.fecha_hora + timedelta(minutes=cita.servicio.duracion_min))
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
        if any(
            comienzo < fin and termina > inicio for comienzo, termina in ocupados
        ):
            continue
        libres.append(
            {
                "inicio": inicio,
                "etiqueta": f"{_local(inicio):%H:%M} a {_local(fin):%H:%M}",
            }
        )

    return Response({**base, "atiende": True, "horarios": libres})


def _local(momento: datetime) -> datetime:
    """Pasa un instante UTC al huso de la barbería, para las etiquetas."""
    from apps.citas.agenda import a_local

    return a_local(momento)


# --- Operar sobre una cita -------------------------------------------------


class DetalleCita(APIView):
    """Consulta, reprograma o cancela una cita."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: CitaSerializer})
    def get(self, request, id_cita: int):
        """RF-06: consulta una cita por su identificador."""
        cita = _buscar_cita(id_cita)
        _exigir_propiedad(cita, request.user)
        return Response(CitaSerializer(cita).data)

    @extend_schema(request=CitaActualizarSerializer, responses={200: CitaSerializer})
    def put(self, request, id_cita: int):
        """RF-08: reprograma una cita.

        Sólo se reprograma una cita agendada (RN-11): una cancelada o atendida
        ya cerró su ciclo.
        """
        cita = _buscar_cita(id_cita)
        _exigir_propiedad(cita, request.user)

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

        inicio = _asegurar_futuro(datos.validated_data["fecha_hora"])
        # El barbero y el servicio no cambian al reprogramar: se conservan los
        # de la cita y sólo se valida que el nuevo horario sirva.
        duracion = cita.servicio.duracion_min
        _asegurar_horario_valido(inicio, duracion)

        try:
            # Se excluye a sí misma: una cita no se solapa consigo.
            _verificar_disponibilidad(
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
        cita = _buscar_cita(id_cita)
        _exigir_propiedad(cita, request.user)

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
    cita = _buscar_cita(id_cita)
    _exigir_propiedad(cita, request.user)

    datos = CitaEstadoSerializer(data=request.data)
    datos.is_valid(raise_exception=True)
    nuevo = datos.validated_data["estado"]

    if nuevo == Cita.ATENDIDA and not request.user.es_admin:
        raise PermissionDenied(
            "Sólo la barbería puede marcar una cita como atendida."
        )

    # Reactivar una cita exige que su horario siga siendo válido y esté libre.
    if nuevo == Cita.AGENDADA and cita.estado != Cita.AGENDADA:
        inicio = _asegurar_futuro(cita.fecha_hora)
        _asegurar_horario_valido(inicio, cita.servicio.duracion_min)
        try:
            _verificar_disponibilidad(
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
