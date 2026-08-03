import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "Falta la variable de entorno DATABASE_URL. "
        "Copie .env.example a .env y complete la cadena de conexión de Supabase."
    )

# La API se conecta a la base de datos PostgreSQL de Supabase mediante el rol
# `daw_api`, que solo tiene privilegios sobre el esquema `daw`.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    connect_args={"options": "-c search_path=daw"},
)

SesionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_sesion() -> Generator[Session, None, None]:
    """Dependencia de FastAPI: entrega una sesión de base de datos por petición."""
    sesion = SesionLocal()
    try:
        yield sesion
    finally:
        sesion.close()
