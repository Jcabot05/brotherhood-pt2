"""Catálogo de servicios.

Implementa HU-01: el catálogo es información comercial que la barbería quiere
mostrar abiertamente, de modo que cualquier visitante pueda consultarlo sin
credenciales antes de decidir si se registra.

Reglas de negocio aplicadas:

- RN-01: la lectura del catálogo es pública; no exige autenticación.
- RN-04: solo un administrador puede crear, modificar o retirar servicios.
- RN-15: precio y duración son valores mayores que cero (validado además por
  las restricciones de la base de datos).
- RN-16: un servicio con citas asociadas no se elimina físicamente; se marca
  como inactivo para preservar el historial.
- RN-19: cada error devuelve el código HTTP que corresponde a su causa.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_sesion
from app.dependencias import requiere_admin
from app.models import Servicio, ServicioActualizar, ServicioCrear
from app.tablas import ServicioTabla, UsuarioTabla

router = APIRouter(prefix="/servicios", tags=["Servicios"])


def _buscar_servicio(sesion: Session, id_servicio: int) -> ServicioTabla:
    servicio = sesion.get(ServicioTabla, id_servicio)
    if servicio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un servicio con id {id_servicio}.",
        )
    return servicio


# --------------------------------------------------------------------
# Lectura pública (HU-01 · RN-01)
# --------------------------------------------------------------------


@router.get(
    "/",
    response_model=list[Servicio],
    summary="Consultar el catálogo de servicios",
)
def listar_servicios(
    skip: int = 0,
    limit: int = 50,
    incluir_inactivos: bool = False,
    sesion: Session = Depends(get_sesion),
):
    """RF-04: consulta el catálogo con su precio y duración. Acceso público.

    Los servicios retirados quedan fuera del listado (RN-16). Si el catálogo
    está vacío la respuesta es `200` con un arreglo vacío, no un error.

    `incluir_inactivos` está pensado para la administración del catálogo; el
    listado público usa el valor por omisión.
    """
    consulta = select(ServicioTabla)
    if not incluir_inactivos:
        consulta = consulta.where(ServicioTabla.activo.is_(True))

    consulta = consulta.order_by(ServicioTabla.id_servicio).offset(skip).limit(limit)
    return sesion.scalars(consulta).all()


@router.get(
    "/{id_servicio}",
    response_model=Servicio,
    summary="Consultar un servicio",
)
def obtener_servicio(id_servicio: int, sesion: Session = Depends(get_sesion)):
    """RF-03: consulta un servicio por su identificador. Acceso público.

    Un identificador inexistente devuelve `404` con un mensaje descriptivo.
    """
    return _buscar_servicio(sesion, id_servicio)


# --------------------------------------------------------------------
# Administración del catálogo (RN-04)
# --------------------------------------------------------------------


@router.post(
    "/",
    response_model=Servicio,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un servicio",
)
def crear_servicio(
    datos: ServicioCrear,
    sesion: Session = Depends(get_sesion),
    _admin: UsuarioTabla = Depends(requiere_admin),
):
    """RF-03: registra un servicio con su precio y duración. Requiere administrador."""
    servicio = ServicioTabla(**datos.model_dump())
    sesion.add(servicio)
    sesion.commit()
    sesion.refresh(servicio)
    return servicio


@router.put(
    "/{id_servicio}",
    response_model=Servicio,
    summary="Actualizar un servicio",
)
def actualizar_servicio(
    id_servicio: int,
    datos: ServicioActualizar,
    sesion: Session = Depends(get_sesion),
    _admin: UsuarioTabla = Depends(requiere_admin),
):
    """RF-03: actualiza los datos de un servicio. Requiere administrador."""
    servicio = _buscar_servicio(sesion, id_servicio)
    for campo, valor in datos.model_dump().items():
        setattr(servicio, campo, valor)
    sesion.commit()
    sesion.refresh(servicio)
    return servicio


@router.delete(
    "/{id_servicio}",
    response_model=Servicio,
    summary="Retirar un servicio del catálogo",
)
def retirar_servicio(
    id_servicio: int,
    sesion: Session = Depends(get_sesion),
    _admin: UsuarioTabla = Depends(requiere_admin),
):
    """RN-16: retira el servicio del catálogo sin borrar su registro.

    El servicio se marca como inactivo y deja de aparecer en el listado
    público, pero las citas que lo referencian conservan su historial. Requiere
    administrador.
    """
    servicio = _buscar_servicio(sesion, id_servicio)
    servicio.activo = False
    sesion.commit()
    sesion.refresh(servicio)
    return servicio


@router.post(
    "/{id_servicio}/reactivar",
    response_model=Servicio,
    summary="Reincorporar un servicio al catálogo",
)
def reactivar_servicio(
    id_servicio: int,
    sesion: Session = Depends(get_sesion),
    _admin: UsuarioTabla = Depends(requiere_admin),
):
    """Devuelve al catálogo un servicio retirado. Requiere administrador."""
    servicio = _buscar_servicio(sesion, id_servicio)
    servicio.activo = True
    sesion.commit()
    sesion.refresh(servicio)
    return servicio
