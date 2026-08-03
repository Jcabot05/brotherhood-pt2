# TheBrotherhood — REST API con autenticación

Proyecto 04 de la materia **Desarrollo de Aplicaciones Web**. Continuación del Proyecto 03:
sobre la REST API de gestión de citas ya construida se incorpora autenticación y control de
permisos.

**Cliente:** TheBrotherhood (barbería)
**Integrantes:** Alejandro Tapia · Jeremías Cabot

## Alcance

Se seleccionaron dos de los nueve requisitos funcionales especificados en el Proyecto 03, uno por
cada nivel de acceso:

| Requisito | Historia | Acceso | Endpoint |
|---|---|---|---|
| RF-04 — Listado de servicios | HU-01 | Público | `GET /servicios/` |
| RF-05 — Agendar cita | HU-02 | Autenticado | `POST /citas/` |

La validación de disponibilidad de barbero (RF-07) se incorpora como regla de negocio de HU-02.

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/01_analisis.md`](docs/01_analisis.md) | Requisitos seleccionados, las dos historias de usuario con sus criterios de aceptación, y las reglas de negocio. |
| [`docs/02_planificacion.md`](docs/02_planificacion.md) | Repositorio, estrategia de ramas, roles y responsabilidades. |

## Stack

- Python · FastAPI · Uvicorn
- PostgreSQL (Supabase), esquema aislado `daw`
- Documentación interactiva vía Swagger/OpenAPI en `/docs`

## Estructura

```
main.py              Aplicación FastAPI: routers y manejo de errores
app/
  database.py        Conexión a PostgreSQL (search_path limitado a `daw`)
  tablas.py          Tablas del esquema `daw` para SQLAlchemy
  models.py          Esquemas de validación de entrada y salida (Pydantic)
  routers/           Un módulo por recurso: clientes, barberos, servicios, citas
db/
  schema.sql         Creación del esquema `daw`, tablas, índices y permisos
  rollback.sql       Reversión completa de los cambios en la base de datos
tests/
  prueba_endpoints.py  Pruebas de extremo a extremo contra la API
docs/                Documentación de las fases del proyecto
```

## Instalación

Requiere Python 3.12 o superior.

```bash
git clone https://github.com/Jcabot05/brotherhood-pt2.git
cd brotherhood-pt2

python3 -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### Configuración

La cadena de conexión no se versiona. Copie la plantilla y complete sus datos:

```bash
cp .env.example .env
```

```
DATABASE_URL=postgresql+psycopg://<usuario>:<password>@<host>:5432/postgres
```

La API se conecta con el rol `daw_api`, cuyos privilegios se limitan al esquema `daw`.

### Base de datos

Si el esquema aún no existe, ejecute `db/schema.sql` sobre la base de datos. Para deshacer los
cambios, `db/rollback.sql`.

## Ejecución

```bash
fastapi dev main.py
```

La API queda en `http://127.0.0.1:8000` y la documentación interactiva en
`http://127.0.0.1:8000/docs`.

## Pruebas

```bash
python tests/prueba_endpoints.py http://127.0.0.1:8000
```

Sin argumento, las pruebas corren contra la API local.

## Aislamiento de la base de datos

El proyecto Supabase pertenece a un cliente real en operación. **Todo el trabajo académico vive
en el esquema `daw`**, separado del esquema `public` donde corren los sistemas del cliente. El rol
`daw_api` con el que se conecta la API tiene los privilegios sobre `public` explícitamente
revocados, de modo que el aislamiento lo impone PostgreSQL y no la lógica de la aplicación.

## Antecedente

Proyecto 03 — API construida, desplegada y verificada (22/22 pruebas de extremo a extremo):
[alejandrotapia20/brotherhood-api](https://github.com/alejandrotapia20/brotherhood-api)
