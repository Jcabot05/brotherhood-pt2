from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_sesion
from app.models import Servicio, ServicioActualizar, ServicioCrear
from app.tablas import ServicioTabla

router = APIRouter(prefix="/servicios", tags=["Servicios"])


def _buscar_servicio(sesion: Session, id_servicio: int) -> ServicioTabla:
    servicio = sesion.get(ServicioTabla, id_servicio)
    if servicio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un servicio con id {id_servicio}.",
        )
    return servicio


@router.post(
    "/",
    response_model=Servicio,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un servicio",
)
def crear_servicio(datos: ServicioCrear, sesion: Session = Depends(get_sesion)):
    """RF-03: registra un servicio con su precio y duración estimada."""
    servicio = ServicioTabla(**datos.model_dump())
    sesion.add(servicio)
    sesion.commit()
    sesion.refresh(servicio)
    return servicio


@router.get(
    "/", response_model=list[Servicio], summary="Consultar el catálogo de servicios"
)
def listar_servicios(
    skip: int = 0, limit: int = 50, sesion: Session = Depends(get_sesion)
):
    """RF-04: consulta el catálogo de servicios con su precio y duración."""
    consulta = (
        select(ServicioTabla)
        .order_by(ServicioTabla.id_servicio)
        .offset(skip)
        .limit(limit)
    )
    return sesion.scalars(consulta).all()


@router.get("/{id_servicio}", response_model=Servicio, summary="Consultar un servicio")
def obtener_servicio(id_servicio: int, sesion: Session = Depends(get_sesion)):
    """RF-03: consulta un servicio por su identificador."""
    return _buscar_servicio(sesion, id_servicio)


@router.put("/{id_servicio}", response_model=Servicio, summary="Actualizar un servicio")
def actualizar_servicio(
    id_servicio: int, datos: ServicioActualizar, sesion: Session = Depends(get_sesion)
):
    """RF-03: actualiza los datos de un servicio existente."""
    servicio = _buscar_servicio(sesion, id_servicio)
    for campo, valor in datos.model_dump().items():
        setattr(servicio, campo, valor)
    sesion.commit()
    sesion.refresh(servicio)
    return servicio


@router.delete("/{id_servicio}", summary="Eliminar un servicio")
def eliminar_servicio(id_servicio: int, sesion: Session = Depends(get_sesion)):
    """RF-03: elimina un servicio del catálogo."""
    servicio = _buscar_servicio(sesion, id_servicio)
    sesion.delete(servicio)
    sesion.commit()
    return {"mensaje": f"Servicio {id_servicio} eliminado correctamente."}
