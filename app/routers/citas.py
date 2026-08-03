from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_sesion
from app.models import Cita, CitaCambiarEstado, CitaCrear, CitaReprogramar, EstadoCita
from app.tablas import BarberoTabla, CitaTabla, ClienteTabla, ServicioTabla

router = APIRouter(prefix="/citas", tags=["Citas"])


def _buscar_cita(sesion: Session, id_cita: int) -> CitaTabla:
    cita = sesion.get(CitaTabla, id_cita)
    if cita is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe una cita con id {id_cita}.",
        )
    return cita


def _verificar_referencias(sesion: Session, datos: CitaCrear) -> None:
    """RF-05: los tres recursos referenciados por la cita deben existir."""
    if sesion.get(ClienteTabla, datos.id_cliente) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un cliente con id {datos.id_cliente}.",
        )
    if sesion.get(BarberoTabla, datos.id_barbero) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un barbero con id {datos.id_barbero}.",
        )
    if sesion.get(ServicioTabla, datos.id_servicio) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un servicio con id {datos.id_servicio}.",
        )


def _verificar_disponibilidad(
    sesion: Session,
    id_barbero: int,
    fecha_hora: datetime,
    id_cita_excluida: int | None = None,
) -> None:
    """RF-07: el barbero no puede tener otra cita agendada en el mismo horario."""
    consulta = select(CitaTabla.id_cita).where(
        CitaTabla.id_barbero == id_barbero,
        CitaTabla.fecha_hora == fecha_hora,
        CitaTabla.estado == EstadoCita.agendada.value,
    )
    if id_cita_excluida is not None:
        consulta = consulta.where(CitaTabla.id_cita != id_cita_excluida)

    if sesion.scalars(consulta).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"El barbero {id_barbero} ya tiene una cita agendada para "
                f"{fecha_hora.isoformat()}. Seleccione otro horario."
            ),
        )


@router.post(
    "/",
    response_model=Cita,
    status_code=status.HTTP_201_CREATED,
    summary="Agendar una cita",
)
def agendar_cita(datos: CitaCrear, sesion: Session = Depends(get_sesion)):
    """RF-05: agenda una cita validando la disponibilidad del barbero (RF-07)."""
    _verificar_referencias(sesion, datos)

    if datos.estado is EstadoCita.agendada:
        _verificar_disponibilidad(sesion, datos.id_barbero, datos.fecha_hora)

    cita = CitaTabla(
        id_cliente=datos.id_cliente,
        id_barbero=datos.id_barbero,
        id_servicio=datos.id_servicio,
        fecha_hora=datos.fecha_hora,
        estado=datos.estado.value,
    )
    sesion.add(cita)
    sesion.commit()
    sesion.refresh(cita)
    return cita


@router.get("/", response_model=list[Cita], summary="Listar y filtrar citas")
def listar_citas(
    id_barbero: int | None = Query(default=None, description="Filtrar por barbero"),
    id_cliente: int | None = Query(default=None, description="Filtrar por cliente"),
    fecha: date | None = Query(default=None, description="Filtrar por día (AAAA-MM-DD)"),
    estado: EstadoCita | None = Query(default=None, description="Filtrar por estado"),
    skip: int = 0,
    limit: int = 50,
    sesion: Session = Depends(get_sesion),
):
    """RF-06: lista las citas con filtros por barbero, cliente, fecha y estado."""
    consulta = select(CitaTabla)

    if id_barbero is not None:
        consulta = consulta.where(CitaTabla.id_barbero == id_barbero)
    if id_cliente is not None:
        consulta = consulta.where(CitaTabla.id_cliente == id_cliente)
    if estado is not None:
        consulta = consulta.where(CitaTabla.estado == estado.value)
    if fecha is not None:
        inicio = datetime.combine(fecha, time.min, tzinfo=timezone.utc)
        fin = datetime.combine(fecha, time.max, tzinfo=timezone.utc)
        consulta = consulta.where(CitaTabla.fecha_hora.between(inicio, fin))

    consulta = consulta.order_by(CitaTabla.fecha_hora).offset(skip).limit(limit)
    return sesion.scalars(consulta).all()


@router.get("/{id_cita}", response_model=Cita, summary="Consultar una cita")
def obtener_cita(id_cita: int, sesion: Session = Depends(get_sesion)):
    """RF-06: consulta una cita por su identificador."""
    return _buscar_cita(sesion, id_cita)


@router.put("/{id_cita}", response_model=Cita, summary="Reprogramar una cita")
def reprogramar_cita(
    id_cita: int, datos: CitaReprogramar, sesion: Session = Depends(get_sesion)
):
    """RF-08: modifica la fecha y hora de una cita, revalidando disponibilidad."""
    cita = _buscar_cita(sesion, id_cita)

    if cita.estado != EstadoCita.agendada.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Solo se pueden reprogramar citas en estado 'agendada'. "
                f"La cita {id_cita} está en estado '{cita.estado}'."
            ),
        )

    _verificar_disponibilidad(
        sesion, cita.id_barbero, datos.fecha_hora, id_cita_excluida=id_cita
    )

    cita.fecha_hora = datos.fecha_hora
    sesion.commit()
    sesion.refresh(cita)
    return cita


@router.patch(
    "/{id_cita}/estado", response_model=Cita, summary="Actualizar el estado de una cita"
)
def actualizar_estado_cita(
    id_cita: int, datos: CitaCambiarEstado, sesion: Session = Depends(get_sesion)
):
    """RF-09: cambia el estado de la cita entre agendada, cancelada y atendida."""
    cita = _buscar_cita(sesion, id_cita)

    # Al reactivar una cita cancelada hay que revalidar que el horario siga libre.
    if (
        datos.estado is EstadoCita.agendada
        and cita.estado != EstadoCita.agendada.value
    ):
        _verificar_disponibilidad(
            sesion, cita.id_barbero, cita.fecha_hora, id_cita_excluida=id_cita
        )

    cita.estado = datos.estado.value
    sesion.commit()
    sesion.refresh(cita)
    return cita


@router.delete("/{id_cita}", summary="Cancelar una cita")
def cancelar_cita(id_cita: int, sesion: Session = Depends(get_sesion)):
    """RF-08: cancela una cita cambiando su estado a 'cancelada'."""
    cita = _buscar_cita(sesion, id_cita)
    cita.estado = EstadoCita.cancelada.value
    sesion.commit()
    return {"mensaje": f"Cita {id_cita} cancelada correctamente."}
