from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.routers import barberos, citas, clientes, servicios

app = FastAPI(
    title="TheBrotherhood — API de gestión de citas",
    description=(
        "REST API para la gestión de citas de la barbería TheBrotherhood. "
        "Permite administrar clientes, barberos, servicios y citas, validando "
        "la disponibilidad del barbero para evitar cruces de horario.\n\n"
        "Proyecto 04 — Desarrollo de Aplicaciones Web. Continuación del Proyecto 03: "
        "sobre esta base se incorporan autenticación y control de permisos "
        "(HU-01 catálogo público, HU-02 agendar cita autenticada).\n"
        "Integrantes: Alejandro Tapia · Jeremías Cabot."
    ),
    version="2.0.0",
)

app.include_router(clientes.router)
app.include_router(barberos.router)
app.include_router(servicios.router)
app.include_router(citas.router)


@app.exception_handler(IntegrityError)
def manejar_error_integridad(request: Request, exc: IntegrityError) -> JSONResponse:
    """Traduce las violaciones de restricciones a respuestas HTTP claras (RNF-05).

    El índice único parcial `cita_barbero_horario_unico` protege la regla de
    disponibilidad (RF-07) en la base de datos: si dos peticiones intentan agendar
    el mismo horario a la vez, Postgres rechaza la segunda y aquí se devuelve un
    409 en lugar de un error interno.
    """
    codigo = getattr(getattr(exc, "orig", None), "sqlstate", None)

    if codigo == "23505":
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "El barbero ya tiene una cita agendada en ese horario."},
        )
    if codigo == "23503":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Alguno de los recursos referenciados no existe."},
        )
    if codigo == "23514":
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Los datos enviados no cumplen las reglas de validación."
            },
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error al procesar la solicitud en la base de datos."},
    )


@app.get("/", tags=["General"], summary="Estado de la API")
def raiz():
    return {
        "mensaje": "API de gestión de citas — TheBrotherhood",
        "documentacion": "/docs",
        "recursos": ["/clientes", "/barberos", "/servicios", "/citas"],
    }


@app.get("/salud", tags=["General"], summary="Verificación de disponibilidad")
def salud():
    """RNF-06: endpoint simple para comprobar que el servicio está en línea."""
    return {"estado": "ok"}
