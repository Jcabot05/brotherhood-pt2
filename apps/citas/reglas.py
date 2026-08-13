"""Reglas de negocio de la agenda."""

from datetime import datetime, timedelta, timezone

from django.db.models import DateTimeField, DurationField, ExpressionWrapper, F
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.catalogo.models import Barbero, Servicio
from apps.citas.agenda import HorarioInvalido, verificar_horario
from apps.citas.models import Cita
from apps.usuarios.models import Cliente


class ConflictoDeAgenda(Exception):
    """Choque de horarios. Las vistas lo traducen a 409."""


def cliente_del_usuario(usuario) -> Cliente:
    """Ficha de cliente de la cuenta autenticada."""
    cliente = Cliente.objects.filter(usuario=usuario).first()
    if cliente is None:
        raise NotFound(
            "La cuenta no tiene una ficha de cliente asociada. "
            "Contacte con la barbería."
        )
    return cliente


def asegurar_futuro(fecha_hora: datetime) -> datetime:
    """RN-08: no se agenda en el pasado."""
    momento = (
        fecha_hora
        if fecha_hora.tzinfo is not None
        else fecha_hora.replace(tzinfo=timezone.utc)
    )

    if momento <= datetime.now(timezone.utc):
        raise ValidationError("La cita debe agendarse en una fecha y hora futuras.")
    return momento


def asegurar_horario_valido(inicio: datetime, duracion_min: int) -> None:
    """RN-21 a RN-23: la cita debe caber en el horario de atención."""
    try:
        verificar_horario(inicio, duracion_min)
    except HorarioInvalido as error:
        raise ValidationError(str(error)) from error


def verificar_referencias(id_barbero: int, id_servicio: int) -> Servicio:
    """RN-13: barbero y servicio deben existir. Devuelve el servicio."""
    if not Barbero.objects.filter(pk=id_barbero).exists():
        raise NotFound(f"No existe un barbero con id {id_barbero}.")

    servicio = Servicio.objects.filter(pk=id_servicio).first()
    if servicio is None:
        raise NotFound(f"No existe un servicio con id {id_servicio}.")
    return servicio


def citas_solapadas(
    id_barbero: int,
    inicio: datetime,
    duracion_min: int,
    id_cita_excluida: int | None = None,
):
    """Citas agendadas del barbero cuyo intervalo choca con el solicitado."""
    fin = inicio + timedelta(minutes=duracion_min)

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


def verificar_disponibilidad(
    id_barbero: int,
    inicio: datetime,
    duracion_min: int,
    id_cita_excluida: int | None = None,
) -> None:
    """RN-07: el barbero no puede tener dos citas con intervalos solapados."""
    if citas_solapadas(id_barbero, inicio, duracion_min, id_cita_excluida).exists():
        fin = inicio + timedelta(minutes=duracion_min)
        raise ConflictoDeAgenda(
            f"El barbero {id_barbero} ya tiene una cita que se solapa con el "
            f"intervalo solicitado ({inicio.isoformat()} — {fin.isoformat()}). "
            "Seleccione otro horario."
        )


def exigir_propiedad(cita: Cita, usuario) -> None:
    """RN-03: un cliente sólo opera sobre sus propias citas."""
    if usuario.es_admin:
        return

    cliente = cliente_del_usuario(usuario)
    if cita.cliente_id != cliente.id_cliente:
        raise PermissionDenied(
            "No puede operar sobre una cita que pertenece a otro cliente."
        )


def buscar_cita(id_cita: int) -> Cita:
    """Cita por su identificador."""
    cita = Cita.objects.filter(pk=id_cita).first()
    if cita is None:
        raise NotFound(f"No existe una cita con id {id_cita}.")
    return cita
