"""Gestión de citas.

Implementa HU-02: agendar una cita crea un compromiso con un barbero en un
horario concreto y consume disponibilidad real del negocio, por lo que exige
identificar quién reserva.

Reglas de negocio aplicadas:

- RN-02: toda operación de escritura exige un token válido.
- RN-03: un cliente solo opera sobre sus propias citas; hacerlo sobre la cita
  de otro devuelve 403. El administrador queda exento, porque gestiona la
  agenda del negocio.
- RN-07: un barbero no puede tener dos citas cuyos intervalos se solapen. El
  intervalo ocupado va desde la fecha/hora de la cita hasta esa hora más la
  duración del servicio.
- RN-08: una cita solo puede agendarse en una fecha/hora futura.
- RN-10: una cita nueva nace siempre en estado agendada.
- RN-21: la cita debe caer dentro del horario de atención de la barbería.
- RN-22: los inicios de cita ocurren en intervalos regulares.
- RN-23: el servicio debe caber completo antes de la hora de cierre.
- RN-11: una cita cancelada o atendida no puede reprogramarse.
- RN-12: una cita solo puede cancelarse mientras su horario siga siendo futuro.
- RN-13: la cita exige la existencia previa de barbero y servicio.
- RN-17: las fechas se manejan y almacenan en UTC.
"""

from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.agenda import (
    HorarioInvalido,
    a_local,
    descripcion_horario,
    es_dia_laborable,
    horarios_del_dia,
    verificar_horario,
)
from app.database import get_sesion
from app.dependencias import usuario_actual
from app.models import (
    Cita,
    CitaCambiarEstado,
    CitaCrear,
    CitaReprogramar,
    DisponibilidadDia,
    EstadoCita,
    HorarioDisponible,
)
from app.tablas import BarberoTabla, CitaTabla, ClienteTabla, ServicioTabla, UsuarioTabla

router = APIRouter(prefix="/citas", tags=["Citas"])


# --------------------------------------------------------------------
# Apoyo
# --------------------------------------------------------------------


def _buscar_cita(sesion: Session, id_cita: int) -> CitaTabla:
    cita = sesion.get(CitaTabla, id_cita)
    if cita is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe una cita con id {id_cita}.",
        )
    return cita


def _cliente_del_usuario(sesion: Session, usuario: UsuarioTabla) -> ClienteTabla:
    """Devuelve la ficha de cliente asociada a la cuenta autenticada.

    El registro crea siempre usuario y ficha en la misma operación, de modo que
    la ausencia de ficha indica una cuenta incompleta y no un error del cliente.
    """
    consulta = select(ClienteTabla).where(ClienteTabla.id_usuario == usuario.id_usuario)
    cliente = sesion.scalars(consulta).first()

    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "La cuenta no tiene una ficha de cliente asociada y no puede "
                "agendar citas."
            ),
        )
    return cliente


def _asegurar_futuro(fecha_hora: datetime) -> datetime:
    """RN-08 y RN-17: la fecha debe ser futura y se maneja en UTC.

    Una fecha sin zona horaria se interpreta como UTC, de modo que la
    comparación nunca mezcla instantes con y sin zona.
    """
    momento = (
        fecha_hora
        if fecha_hora.tzinfo is not None
        else fecha_hora.replace(tzinfo=timezone.utc)
    )

    if momento <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La cita debe agendarse en una fecha y hora futuras.",
        )
    return momento


def _asegurar_horario_valido(inicio: datetime, duracion_min: int) -> None:
    """RN-21 a RN-23: la cita debe caber en el horario de atención.

    Traduce el motivo concreto a un 422, de modo que quien reserva sepa por qué
    ese horario no sirve en lugar de recibir un rechazo genérico (RN-19).
    """
    try:
        verificar_horario(inicio, duracion_min)
    except HorarioInvalido as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error


def _verificar_referencias(sesion: Session, id_barbero: int, id_servicio: int) -> ServicioTabla:
    """RN-13: barbero y servicio deben existir. Devuelve el servicio."""
    if sesion.get(BarberoTabla, id_barbero) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un barbero con id {id_barbero}.",
        )

    servicio = sesion.get(ServicioTabla, id_servicio)
    if servicio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un servicio con id {id_servicio}.",
        )
    return servicio


def _intervalos_ocupados(
    sesion: Session, id_barbero: int, desde: datetime, hasta: datetime
) -> list[tuple[datetime, datetime]]:
    """Devuelve los intervalos que el barbero ya tiene comprometidos.

    Una sola consulta por día en lugar de una por horario candidato: la
    disponibilidad se calcula después en memoria.
    """
    consulta = (
        select(CitaTabla.fecha_hora, ServicioTabla.duracion_min)
        .join(ServicioTabla, ServicioTabla.id_servicio == CitaTabla.id_servicio)
        .where(
            CitaTabla.id_barbero == id_barbero,
            CitaTabla.estado == EstadoCita.agendada.value,
            CitaTabla.fecha_hora >= desde,
            CitaTabla.fecha_hora < hasta,
        )
    )

    return [
        (comienzo, comienzo + timedelta(minutes=duracion))
        for comienzo, duracion in sesion.execute(consulta).all()
    ]


def _verificar_disponibilidad(
    sesion: Session,
    id_barbero: int,
    inicio: datetime,
    duracion_min: int,
    id_cita_excluida: int | None = None,
) -> None:
    """RN-07: el barbero no puede tener dos citas con intervalos solapados.

    El intervalo de una cita va desde su fecha/hora hasta esa hora más la
    duración de su servicio. Dos intervalos se solapan cuando cada uno empieza
    antes de que termine el otro; comparar solo la hora de inicio dejaría pasar
    una cita que arranca en mitad de otra.

    Solo compiten las citas agendadas: una cancelada o atendida libera su
    horario (RN-11).
    """
    fin = inicio + timedelta(minutes=duracion_min)

    # Fin del intervalo de cada cita existente: su hora de inicio más la
    # duración de su servicio, expresada como intervalo de PostgreSQL.
    fin_existente = CitaTabla.fecha_hora + (
        ServicioTabla.duracion_min * text("interval '1 minute'")
    )

    consulta = (
        select(CitaTabla.id_cita)
        .join(ServicioTabla, ServicioTabla.id_servicio == CitaTabla.id_servicio)
        .where(
            CitaTabla.id_barbero == id_barbero,
            CitaTabla.estado == EstadoCita.agendada.value,
            # Dos intervalos se solapan cuando cada uno empieza antes de que
            # termine el otro: inicio_existente < fin_nueva y fin_existente > inicio_nueva.
            CitaTabla.fecha_hora < fin,
            fin_existente > inicio,
        )
    )
    if id_cita_excluida is not None:
        consulta = consulta.where(CitaTabla.id_cita != id_cita_excluida)

    if sesion.scalars(consulta).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"El barbero {id_barbero} ya tiene una cita que se solapa con el "
                f"intervalo solicitado ({inicio.isoformat()} — {fin.isoformat()}). "
                "Seleccione otro horario."
            ),
        )


def _exigir_propiedad(cita: CitaTabla, cliente_id: int, usuario: UsuarioTabla) -> None:
    """RN-03: un cliente solo opera sobre sus propias citas.

    El administrador queda exento: gestiona la agenda completa del negocio.
    """
    if usuario.rol == "admin":
        return

    if cita.id_cliente != cliente_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puede operar sobre una cita que pertenece a otro cliente.",
        )


# --------------------------------------------------------------------
# Agendar (HU-02)
# --------------------------------------------------------------------


@router.post(
    "/",
    response_model=Cita,
    status_code=status.HTTP_201_CREATED,
    summary="Agendar una cita",
)
def agendar_cita(
    datos: CitaCrear,
    sesion: Session = Depends(get_sesion),
    usuario: UsuarioTabla = Depends(usuario_actual),
):
    """RF-05: agenda una cita a nombre del cliente autenticado.

    La cita se asocia siempre al dueño del token (RN-03), nace en estado
    agendada (RN-10) y solo se crea si el horario está libre (RN-07) y es
    futuro (RN-08).
    """
    cliente = _cliente_del_usuario(sesion, usuario)
    inicio = _asegurar_futuro(datos.fecha_hora)
    servicio = _verificar_referencias(sesion, datos.id_barbero, datos.id_servicio)

    _asegurar_horario_valido(inicio, servicio.duracion_min)
    _verificar_disponibilidad(
        sesion, datos.id_barbero, inicio, servicio.duracion_min
    )

    cita = CitaTabla(
        id_cliente=cliente.id_cliente,
        id_barbero=datos.id_barbero,
        id_servicio=datos.id_servicio,
        fecha_hora=inicio,
        estado=EstadoCita.agendada.value,
    )
    sesion.add(cita)
    sesion.commit()
    sesion.refresh(cita)
    return cita


# --------------------------------------------------------------------
# Consulta
# --------------------------------------------------------------------


@router.get("/", response_model=list[Cita], summary="Listar y filtrar citas")
def listar_citas(
    id_barbero: int | None = Query(default=None, description="Filtrar por barbero"),
    fecha: date | None = Query(default=None, description="Filtrar por día (AAAA-MM-DD)"),
    estado: EstadoCita | None = Query(default=None, description="Filtrar por estado"),
    skip: int = 0,
    limit: int = 50,
    sesion: Session = Depends(get_sesion),
    usuario: UsuarioTabla = Depends(usuario_actual),
):
    """RF-06: lista las citas con filtros por barbero, fecha y estado.

    Un cliente ve únicamente sus propias citas (RN-03); el administrador ve la
    agenda completa.
    """
    consulta = select(CitaTabla)

    if usuario.rol != "admin":
        cliente = _cliente_del_usuario(sesion, usuario)
        consulta = consulta.where(CitaTabla.id_cliente == cliente.id_cliente)

    if id_barbero is not None:
        consulta = consulta.where(CitaTabla.id_barbero == id_barbero)
    if estado is not None:
        consulta = consulta.where(CitaTabla.estado == estado.value)
    if fecha is not None:
        inicio = datetime.combine(fecha, time.min, tzinfo=timezone.utc)
        fin = datetime.combine(fecha, time.max, tzinfo=timezone.utc)
        consulta = consulta.where(CitaTabla.fecha_hora.between(inicio, fin))

    consulta = consulta.order_by(CitaTabla.fecha_hora).offset(skip).limit(limit)
    return sesion.scalars(consulta).all()


@router.get(
    "/disponibilidad",
    response_model=DisponibilidadDia,
    summary="Consultar los horarios libres de un barbero",
)
def consultar_disponibilidad(
    id_barbero: int = Query(description="Barbero cuya agenda se consulta"),
    id_servicio: int = Query(description="Servicio que se quiere reservar"),
    fecha: date = Query(description="Día a consultar (AAAA-MM-DD)"),
    sesion: Session = Depends(get_sesion),
):
    """Devuelve los horarios en que ese barbero puede atender ese servicio.

    Cruza el horario de atención (RN-21 a RN-23) con las citas ya agendadas
    (RN-07), de modo que quien reserva elija entre opciones válidas en lugar de
    descubrir los conflictos al enviar el formulario.

    Es de acceso público: consultar disponibilidad no compromete la agenda ni
    revela datos de otros clientes, solo qué franjas están libres.
    """
    servicio = _verificar_referencias(sesion, id_barbero, id_servicio)
    duracion = servicio.duracion_min

    candidatos = horarios_del_dia(fecha, duracion)

    if not candidatos:
        return DisponibilidadDia(
            fecha=fecha,
            id_barbero=id_barbero,
            id_servicio=id_servicio,
            duracion_min=duracion,
            atiende=es_dia_laborable(fecha),
            horario_atencion=descripcion_horario(),
            horarios=[],
        )

    # Los horarios pasados de hoy ya no son reservables (RN-08).
    ahora = datetime.now(timezone.utc)
    ocupados = _intervalos_ocupados(
        sesion,
        id_barbero,
        candidatos[0],
        candidatos[-1] + timedelta(minutes=duracion),
    )

    libres: list[HorarioDisponible] = []

    for inicio in candidatos:
        if inicio <= ahora:
            continue

        fin = inicio + timedelta(minutes=duracion)
        # Se solapa si empieza antes de que termine el otro y viceversa.
        if any(inicio < fin_ocupado and fin > inicio_ocupado
               for inicio_ocupado, fin_ocupado in ocupados):
            continue

        inicio_local = a_local(inicio)
        fin_local = a_local(fin)
        libres.append(
            HorarioDisponible(
                inicio=inicio,
                fin=fin,
                etiqueta=(
                    f"{inicio_local.strftime('%H:%M')} a {fin_local.strftime('%H:%M')}"
                ),
            )
        )

    return DisponibilidadDia(
        fecha=fecha,
        id_barbero=id_barbero,
        id_servicio=id_servicio,
        duracion_min=duracion,
        atiende=True,
        horario_atencion=descripcion_horario(),
        horarios=libres,
    )


@router.get("/{id_cita}", response_model=Cita, summary="Consultar una cita")
def obtener_cita(
    id_cita: int,
    sesion: Session = Depends(get_sesion),
    usuario: UsuarioTabla = Depends(usuario_actual),
):
    """RF-06: consulta una cita propia por su identificador (RN-03)."""
    cita = _buscar_cita(sesion, id_cita)
    cliente = _cliente_del_usuario(sesion, usuario) if usuario.rol != "admin" else None
    _exigir_propiedad(cita, cliente.id_cliente if cliente else 0, usuario)
    return cita


# --------------------------------------------------------------------
# Modificación
# --------------------------------------------------------------------


@router.put("/{id_cita}", response_model=Cita, summary="Reprogramar una cita")
def reprogramar_cita(
    id_cita: int,
    datos: CitaReprogramar,
    sesion: Session = Depends(get_sesion),
    usuario: UsuarioTabla = Depends(usuario_actual),
):
    """RF-08: cambia la fecha y hora de una cita propia, revalidando el horario.

    Una cita cancelada o atendida no se reprograma: su horario ya quedó
    liberado para otras reservas (RN-11).
    """
    cita = _buscar_cita(sesion, id_cita)
    cliente = _cliente_del_usuario(sesion, usuario) if usuario.rol != "admin" else None
    _exigir_propiedad(cita, cliente.id_cliente if cliente else 0, usuario)

    if cita.estado != EstadoCita.agendada.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Solo se pueden reprogramar citas en estado 'agendada'. "
                f"La cita {id_cita} está en estado '{cita.estado}'."
            ),
        )

    inicio = _asegurar_futuro(datos.fecha_hora)
    servicio = sesion.get(ServicioTabla, cita.id_servicio)
    duracion = servicio.duracion_min if servicio is not None else 0

    _asegurar_horario_valido(inicio, duracion)
    _verificar_disponibilidad(
        sesion, cita.id_barbero, inicio, duracion, id_cita_excluida=id_cita
    )

    cita.fecha_hora = inicio
    sesion.commit()
    sesion.refresh(cita)
    return cita


@router.patch(
    "/{id_cita}/estado", response_model=Cita, summary="Actualizar el estado de una cita"
)
def actualizar_estado_cita(
    id_cita: int,
    datos: CitaCambiarEstado,
    sesion: Session = Depends(get_sesion),
    usuario: UsuarioTabla = Depends(usuario_actual),
):
    """RF-09: cambia el estado de la cita entre agendada, cancelada y atendida.

    Marcar una cita como atendida corresponde a la operación del negocio, de
    modo que queda reservado al administrador.
    """
    cita = _buscar_cita(sesion, id_cita)
    cliente = _cliente_del_usuario(sesion, usuario) if usuario.rol != "admin" else None
    _exigir_propiedad(cita, cliente.id_cliente if cliente else 0, usuario)

    if datos.estado is EstadoCita.atendida and usuario.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un administrador puede marcar una cita como atendida.",
        )

    # Al reactivar una cita hay que revalidar que el horario siga libre.
    if (
        datos.estado is EstadoCita.agendada
        and cita.estado != EstadoCita.agendada.value
    ):
        _asegurar_futuro(cita.fecha_hora)
        servicio = sesion.get(ServicioTabla, cita.id_servicio)
        duracion = servicio.duracion_min if servicio is not None else 0
        _verificar_disponibilidad(
            sesion, cita.id_barbero, cita.fecha_hora, duracion, id_cita_excluida=id_cita
        )

    cita.estado = datos.estado.value
    sesion.commit()
    sesion.refresh(cita)
    return cita


@router.delete("/{id_cita}", response_model=Cita, summary="Cancelar una cita")
def cancelar_cita(
    id_cita: int,
    sesion: Session = Depends(get_sesion),
    usuario: UsuarioTabla = Depends(usuario_actual),
):
    """RF-08: cancela una cita propia cambiando su estado a 'cancelada'.

    Una cita solo puede cancelarse mientras su horario siga siendo futuro
    (RN-12): pasada la hora, el registro refleja lo que ocurrió.
    """
    cita = _buscar_cita(sesion, id_cita)
    cliente = _cliente_del_usuario(sesion, usuario) if usuario.rol != "admin" else None
    _exigir_propiedad(cita, cliente.id_cliente if cliente else 0, usuario)

    if cita.estado == EstadoCita.cancelada.value:
        return cita

    momento = (
        cita.fecha_hora
        if cita.fecha_hora.tzinfo is not None
        else cita.fecha_hora.replace(tzinfo=timezone.utc)
    )
    if momento <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede cancelar una cita cuyo horario ya pasó.",
        )

    cita.estado = EstadoCita.cancelada.value
    sesion.commit()
    sesion.refresh(cita)
    return cita
