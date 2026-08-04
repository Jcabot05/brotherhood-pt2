from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.routers import auth, barberos, citas, clientes, servicios

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

app.include_router(auth.router)
app.include_router(clientes.router)
app.include_router(barberos.router)
app.include_router(servicios.router)
app.include_router(citas.router)


@app.exception_handler(IntegrityError)
def manejar_error_integridad(request: Request, exc: IntegrityError) -> JSONResponse:
    """Traduce las violaciones de restricciones a respuestas HTTP claras (RNF-05).

    El índice único parcial `cita_barbero_horario_unico` cubre el caso de dos
    peticiones simultáneas sobre la hora de inicio exacta: Postgres rechaza la
    segunda y aquí se devuelve un 409 en lugar de un error interno.

    El solapamiento parcial que exige RN-07 —una cita que empieza en mitad de
    otra— lo verifica la API antes de insertar, comparando intervalos según la
    duración del servicio. El índice no puede expresar esa condición sin la
    extensión `btree_gist`, que no se instala en esta base de datos por tratarse
    del proyecto de un cliente en operación.
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
        "recursos": ["/auth", "/clientes", "/barberos", "/servicios", "/citas"],
    }


@app.get("/salud", tags=["General"], summary="Verificación de disponibilidad")
def salud():
    """RNF-06: endpoint simple para comprobar que el servicio está en línea."""
    return {"estado": "ok"}
