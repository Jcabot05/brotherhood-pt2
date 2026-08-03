from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_sesion
from app.models import Barbero, BarberoActualizar, BarberoCrear
from app.tablas import BarberoTabla

router = APIRouter(prefix="/barberos", tags=["Barberos"])


def _buscar_barbero(sesion: Session, id_barbero: int) -> BarberoTabla:
    barbero = sesion.get(BarberoTabla, id_barbero)
    if barbero is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un barbero con id {id_barbero}.",
        )
    return barbero


@router.post(
    "/",
    response_model=Barbero,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un barbero",
)
def crear_barbero(datos: BarberoCrear, sesion: Session = Depends(get_sesion)):
    """RF-02: registra un nuevo barbero."""
    barbero = BarberoTabla(**datos.model_dump())
    sesion.add(barbero)
    sesion.commit()
    sesion.refresh(barbero)
    return barbero


@router.get("/", response_model=list[Barbero], summary="Listar barberos")
def listar_barberos(
    skip: int = 0, limit: int = 50, sesion: Session = Depends(get_sesion)
):
    """RF-02: lista los barberos de la barbería."""
    consulta = (
        select(BarberoTabla).order_by(BarberoTabla.id_barbero).offset(skip).limit(limit)
    )
    return sesion.scalars(consulta).all()


@router.get("/{id_barbero}", response_model=Barbero, summary="Consultar un barbero")
def obtener_barbero(id_barbero: int, sesion: Session = Depends(get_sesion)):
    """RF-02: consulta un barbero por su identificador."""
    return _buscar_barbero(sesion, id_barbero)


@router.put("/{id_barbero}", response_model=Barbero, summary="Actualizar un barbero")
def actualizar_barbero(
    id_barbero: int, datos: BarberoActualizar, sesion: Session = Depends(get_sesion)
):
    """RF-02: actualiza los datos de un barbero existente."""
    barbero = _buscar_barbero(sesion, id_barbero)
    for campo, valor in datos.model_dump().items():
        setattr(barbero, campo, valor)
    sesion.commit()
    sesion.refresh(barbero)
    return barbero


@router.delete("/{id_barbero}", summary="Eliminar un barbero")
def eliminar_barbero(id_barbero: int, sesion: Session = Depends(get_sesion)):
    """RF-02: elimina un barbero y sus citas asociadas."""
    barbero = _buscar_barbero(sesion, id_barbero)
    sesion.delete(barbero)
    sesion.commit()
    return {"mensaje": f"Barbero {id_barbero} eliminado correctamente."}
