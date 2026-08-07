"""Horario de atención y generación de horarios reservables.

La barbería atiende en un horario fijo y las citas empiezan en intervalos
regulares, de modo que la agenda sea predecible y no queden huecos
inaprovechables entre reservas.

Reglas de negocio cubiertas:

- RN-21: una cita solo puede agendarse dentro del horario de atención.
- RN-22: los inicios de cita ocurren en intervalos regulares.
- RN-23: el servicio debe caber completo antes de la hora de cierre.

El horario se lee de variables de entorno para que un cambio en la operación
del negocio no exija tocar el código. La comparación se hace siempre en la
zona horaria local de la barbería: la base de datos almacena en UTC (RN-17),
así que un instante correcto se rechazaría si se comparara sin convertir.
"""

import os
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

# Zona horaria en la que opera la barbería.
ZONA_LOCAL = ZoneInfo(os.getenv("ZONA_HORARIA", "America/Guayaquil"))

# Horario de atención. Domingo (6 en la numeración de Python) queda fuera.
HORA_APERTURA = int(os.getenv("HORA_APERTURA", "9"))
HORA_CIERRE = int(os.getenv("HORA_CIERRE", "19"))
INTERVALO_MIN = int(os.getenv("INTERVALO_MINUTOS", "30"))

# Días laborables: 0 es lunes y 6 es domingo.
DIAS_LABORABLES = frozenset(
    int(d) for d in os.getenv("DIAS_LABORABLES", "0,1,2,3,4,5").split(",")
)

NOMBRES_DIA = (
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
)


class HorarioInvalido(ValueError):
    """El horario solicitado no cumple las reglas de la agenda.

    Lleva el motivo ya redactado, de modo que el router lo traduzca a una
    respuesta HTTP sin volver a interpretarlo.
    """


def a_local(momento: datetime) -> datetime:
    """Convierte un instante a la hora local de la barbería."""
    return momento.astimezone(ZONA_LOCAL)


def descripcion_horario() -> str:
    """Describe el horario de atención en una frase, para los mensajes."""
    dias = sorted(DIAS_LABORABLES)
    if not dias:
        return "sin días de atención configurados"

    if dias == list(range(dias[0], dias[-1] + 1)):
        rango = f"de {NOMBRES_DIA[dias[0]]} a {NOMBRES_DIA[dias[-1]]}"
    else:
        rango = ", ".join(NOMBRES_DIA[d] for d in dias)

    return f"{rango}, de {HORA_APERTURA}:00 a {HORA_CIERRE}:00"


def verificar_horario(inicio: datetime, duracion_min: int) -> None:
    """Comprueba que la cita quepa dentro del horario de atención.

    Lanza `HorarioInvalido` con el motivo concreto. Se valida en este orden
    —día, minuto, apertura, cierre— para que el mensaje señale la causa más
    evidente primero.
    """
    local = a_local(inicio)

    # RN-21: el negocio no atiende todos los días.
    if local.weekday() not in DIAS_LABORABLES:
        dia = NOMBRES_DIA[local.weekday()]
        plural = dia if dia.endswith("s") else f"{dia}s"
        raise HorarioInvalido(
            f"La barbería no atiende los {plural}. "
            f"Horario de atención: {descripcion_horario()}."
        )

    # RN-22: los inicios ocurren en intervalos regulares.
    if local.minute % INTERVALO_MIN != 0 or local.second or local.microsecond:
        raise HorarioInvalido(
            f"Las citas empiezan cada {INTERVALO_MIN} minutos. "
            f"Seleccione un horario válido, por ejemplo "
            f"{local.hour:02d}:00 o {local.hour:02d}:{INTERVALO_MIN:02d}."
        )

    # RN-21: dentro de la franja de atención.
    if local.hour < HORA_APERTURA:
        raise HorarioInvalido(
            f"La barbería abre a las {HORA_APERTURA}:00. "
            f"Horario de atención: {descripcion_horario()}."
        )

    # RN-23: el servicio debe terminar antes del cierre.
    cierre = local.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(
        hours=HORA_CIERRE
    )
    fin = local + timedelta(minutes=duracion_min)

    if local >= cierre:
        raise HorarioInvalido(
            f"La barbería cierra a las {HORA_CIERRE}:00. "
            f"Horario de atención: {descripcion_horario()}."
        )

    if fin > cierre:
        raise HorarioInvalido(
            f"El servicio dura {duracion_min} minutos y no alcanza a terminar "
            f"antes del cierre ({HORA_CIERRE}:00). Seleccione un horario más temprano."
        )


def es_dia_laborable(dia: date) -> bool:
    """Indica si la barbería atiende ese día."""
    return dia.weekday() in DIAS_LABORABLES


def horarios_del_dia(dia: date, duracion_min: int) -> list[datetime]:
    """Genera los horarios en que podría empezar un servicio ese día.

    Devuelve instantes con zona horaria, en orden. Excluye los que no dejan
    tiempo suficiente antes del cierre (RN-23). No consulta la base de datos:
    la ocupación real se descuenta en el router.
    """
    if not es_dia_laborable(dia):
        return []

    apertura = datetime.combine(dia, time(hour=HORA_APERTURA), tzinfo=ZONA_LOCAL)
    cierre = datetime.combine(dia, time(hour=0), tzinfo=ZONA_LOCAL) + timedelta(
        hours=HORA_CIERRE
    )

    horarios: list[datetime] = []
    momento = apertura

    while momento < cierre:
        if momento + timedelta(minutes=duracion_min) <= cierre:
            horarios.append(momento)
        momento += timedelta(minutes=INTERVALO_MIN)

    return horarios
