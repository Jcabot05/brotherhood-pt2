"""Pruebas de los endpoints de la API — fase de Verificación y Validación.

Ejecuta un recorrido completo sobre la API en marcha y verifica que cada
requisito funcional responda con el código HTTP esperado.

Desde el Proyecto 04 la administración del catálogo exige rol administrador
(RN-04), de modo que las operaciones de escritura sobre servicios viajan
firmadas con el token de una cuenta administradora.

Uso:
    python tests/prueba_endpoints.py                      # contra localhost
    python tests/prueba_endpoints.py https://mi-api.app   # contra el despliegue

Variables de entorno:
    ADMIN_CORREO, ADMIN_CONTRASENA   credenciales de la cuenta administradora
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

# Las credenciales no se versionan: se leen del entorno o del archivo .env.
ADMIN_CORREO = os.getenv("ADMIN_CORREO", "")
ADMIN_CONTRASENA = os.getenv("ADMIN_CONTRASENA", "")

resultados: list[tuple[str, str, bool, str]] = []


def token_de_administrador(cliente: httpx.Client) -> str:
    """Inicia sesión con la cuenta administradora y devuelve su token."""
    if not ADMIN_CORREO or not ADMIN_CONTRASENA:
        raise SystemExit(
            "Faltan las credenciales de administrador. Defina ADMIN_CORREO y "
            "ADMIN_CONTRASENA en el archivo .env o como variables de entorno. "
            "Deben corresponder a una cuenta con rol `admin`."
        )

    respuesta = cliente.post(
        "/auth/login",
        json={"correo": ADMIN_CORREO, "contrasena": ADMIN_CONTRASENA},
    )
    if respuesta.status_code != 200:
        raise SystemExit(
            "No se pudo iniciar sesión como administrador "
            f"({respuesta.status_code}). Defina ADMIN_CORREO y ADMIN_CONTRASENA "
            "con las credenciales de una cuenta con rol `admin`."
        )
    return respuesta.json()["token_acceso"]


def verificar(requisito: str, descripcion: str, esperado: int, respuesta: httpx.Response):
    ok = respuesta.status_code == esperado
    detalle = f"esperado {esperado}, recibido {respuesta.status_code}"
    resultados.append((requisito, descripcion, ok, detalle))
    return respuesta


def main() -> int:
    cliente = httpx.Client(base_url=BASE_URL, timeout=30)
    horario = (datetime.now(timezone.utc) + timedelta(days=3)).replace(
        minute=0, second=0, microsecond=0
    )

    # La administración del catálogo exige rol administrador (RN-04).
    admin = {"Authorization": f"Bearer {token_de_administrador(cliente)}"}

    # --- RF-01: gestión de clientes -------------------------------------
    r = verificar(
        "RF-01",
        "Registrar un cliente",
        201,
        cliente.post(
            "/clientes/",
            json={
                "nombre": "Cliente de Prueba",
                "telefono": "0999999999",
                "correo": "prueba.daw@example.com",
            },
        ),
    )
    id_cliente = r.json()["id_cliente"]

    verificar("RF-01", "Listar clientes", 200, cliente.get("/clientes/"))
    verificar("RF-01", "Consultar un cliente", 200, cliente.get(f"/clientes/{id_cliente}"))
    verificar(
        "RF-01",
        "Actualizar un cliente",
        200,
        cliente.put(
            f"/clientes/{id_cliente}",
            json={
                "nombre": "Cliente de Prueba Actualizado",
                "telefono": "0988888888",
                "correo": "prueba.daw@example.com",
            },
        ),
    )
    verificar(
        "RNF-05",
        "Rechazar un correo con formato inválido",
        422,
        cliente.post(
            "/clientes/",
            json={"nombre": "Correo Malo", "telefono": "0900000000", "correo": "no-es-correo"},
        ),
    )
    verificar(
        "RNF-05",
        "Responder 404 ante un cliente inexistente",
        404,
        cliente.get("/clientes/99999999"),
    )

    # --- RF-02: gestión de barberos -------------------------------------
    r = verificar(
        "RF-02",
        "Registrar un barbero",
        201,
        cliente.post("/barberos/", json={"nombre": "Barbero de Prueba", "especialidad": "Fade"}),
    )
    id_barbero = r.json()["id_barbero"]
    verificar("RF-02", "Listar barberos", 200, cliente.get("/barberos/"))

    # --- RF-03 y RF-04: servicios ---------------------------------------
    r = verificar(
        "RF-03",
        "Registrar un servicio",
        201,
        cliente.post(
            "/servicios/",
            json={"nombre": "Servicio de Prueba", "precio": 15.0, "duracion_min": 30},
            headers=admin,
        ),
    )
    id_servicio = r.json()["id_servicio"]
    verificar("RF-04", "Consultar el catálogo de servicios", 200, cliente.get("/servicios/"))
    verificar(
        "RNF-05",
        "Rechazar un servicio con precio negativo",
        422,
        cliente.post(
            "/servicios/",
            json={"nombre": "Precio Malo", "precio": -5, "duracion_min": 30},
            headers=admin,
        ),
    )

    # --- RF-05: agendar cita --------------------------------------------
    r = verificar(
        "RF-05",
        "Agendar una cita",
        201,
        cliente.post(
            "/citas/",
            json={
                "id_cliente": id_cliente,
                "id_barbero": id_barbero,
                "id_servicio": id_servicio,
                "fecha_hora": horario.isoformat(),
            },
        ),
    )
    id_cita = r.json()["id_cita"]

    verificar(
        "RF-05",
        "Rechazar una cita con un cliente inexistente",
        404,
        cliente.post(
            "/citas/",
            json={
                "id_cliente": 99999999,
                "id_barbero": id_barbero,
                "id_servicio": id_servicio,
                "fecha_hora": horario.isoformat(),
            },
        ),
    )

    # --- RF-07: validar disponibilidad ----------------------------------
    verificar(
        "RF-07",
        "Rechazar una segunda cita del mismo barbero en el mismo horario",
        409,
        cliente.post(
            "/citas/",
            json={
                "id_cliente": id_cliente,
                "id_barbero": id_barbero,
                "id_servicio": id_servicio,
                "fecha_hora": horario.isoformat(),
            },
        ),
    )

    # --- RF-06: consultar y filtrar citas -------------------------------
    verificar("RF-06", "Listar citas", 200, cliente.get("/citas/"))
    verificar("RF-06", "Consultar una cita", 200, cliente.get(f"/citas/{id_cita}"))
    verificar(
        "RF-06",
        "Filtrar citas por barbero",
        200,
        cliente.get("/citas/", params={"id_barbero": id_barbero}),
    )
    verificar(
        "RF-06",
        "Filtrar citas por fecha",
        200,
        cliente.get("/citas/", params={"fecha": horario.date().isoformat()}),
    )

    # --- RF-08: reprogramar ---------------------------------------------
    nuevo_horario = horario + timedelta(hours=2)
    verificar(
        "RF-08",
        "Reprogramar una cita",
        200,
        cliente.put(f"/citas/{id_cita}", json={"fecha_hora": nuevo_horario.isoformat()}),
    )

    # --- RF-09: cambiar estado ------------------------------------------
    verificar(
        "RF-09",
        "Marcar la cita como atendida",
        200,
        cliente.patch(f"/citas/{id_cita}/estado", json={"estado": "atendida"}),
    )
    verificar(
        "RNF-05",
        "Rechazar un estado no permitido",
        422,
        cliente.patch(f"/citas/{id_cita}/estado", json={"estado": "inventado"}),
    )

    # --- RF-08: cancelar -------------------------------------------------
    verificar("RF-08", "Cancelar una cita", 200, cliente.delete(f"/citas/{id_cita}"))

    # --- Limpieza de los datos de prueba ---------------------------------
    # El servicio no se borra: desde el Proyecto 04, DELETE lo retira del
    # catálogo marcándolo como inactivo para preservar el historial de citas
    # (RN-16). Queda fuera del listado público, que es el efecto buscado.
    cliente.delete(f"/clientes/{id_cliente}")
    cliente.delete(f"/barberos/{id_barbero}")
    cliente.delete(f"/servicios/{id_servicio}", headers=admin)
    cliente.close()

    # --- Informe ---------------------------------------------------------
    print(f"\nPruebas de la API — {BASE_URL}\n")
    print(f"{'Req.':<8}{'Caso de prueba':<58}{'Resultado'}")
    print("-" * 82)
    for requisito, descripcion, ok, detalle in resultados:
        estado = "PASA" if ok else f"FALLA ({detalle})"
        print(f"{requisito:<8}{descripcion:<58}{estado}")

    fallidas = [r for r in resultados if not r[2]]
    print("-" * 82)
    print(f"{len(resultados) - len(fallidas)}/{len(resultados)} pruebas superadas.\n")
    return 1 if fallidas else 0


if __name__ == "__main__":
    raise SystemExit(main())
