from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_sesion
from app.models import Cliente, ClienteActualizar, ClienteCrear
from app.tablas import ClienteTabla

router = APIRouter(prefix="/clientes", tags=["Clientes"])


def _buscar_cliente(sesion: Session, id_cliente: int) -> ClienteTabla:
    cliente = sesion.get(ClienteTabla, id_cliente)
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un cliente con id {id_cliente}.",
        )
    return cliente


@router.post(
    "/",
    response_model=Cliente,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un cliente",
)
def crear_cliente(datos: ClienteCrear, sesion: Session = Depends(get_sesion)):
    """RF-01: registra un nuevo cliente de la barbería."""
    cliente = ClienteTabla(**datos.model_dump())
    sesion.add(cliente)
    sesion.commit()
    sesion.refresh(cliente)
    return cliente


@router.get("/", response_model=list[Cliente], summary="Listar clientes")
def listar_clientes(
    skip: int = 0, limit: int = 50, sesion: Session = Depends(get_sesion)
):
    """RF-01: lista los clientes registrados, con paginación."""
    consulta = (
        select(ClienteTabla).order_by(ClienteTabla.id_cliente).offset(skip).limit(limit)
    )
    return sesion.scalars(consulta).all()


@router.get("/{id_cliente}", response_model=Cliente, summary="Consultar un cliente")
def obtener_cliente(id_cliente: int, sesion: Session = Depends(get_sesion)):
    """RF-01: consulta un cliente por su identificador."""
    return _buscar_cliente(sesion, id_cliente)


@router.put("/{id_cliente}", response_model=Cliente, summary="Actualizar un cliente")
def actualizar_cliente(
    id_cliente: int, datos: ClienteActualizar, sesion: Session = Depends(get_sesion)
):
    """RF-01: actualiza los datos de un cliente existente."""
    cliente = _buscar_cliente(sesion, id_cliente)
    for campo, valor in datos.model_dump().items():
        setattr(cliente, campo, valor)
    sesion.commit()
    sesion.refresh(cliente)
    return cliente


@router.delete("/{id_cliente}", summary="Eliminar un cliente")
def eliminar_cliente(id_cliente: int, sesion: Session = Depends(get_sesion)):
    """RF-01: elimina un cliente y sus citas asociadas."""
    cliente = _buscar_cliente(sesion, id_cliente)
    sesion.delete(cliente)
    sesion.commit()
    return {"mensaje": f"Cliente {id_cliente} eliminado correctamente."}
