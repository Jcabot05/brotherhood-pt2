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
  seguridad.py       Hash de contraseñas (bcrypt) y tokens de acceso (JWT)
  dependencias.py    Comprobaciones de autenticación y permisos para los routers
  tablas.py          Tablas del esquema `daw` para SQLAlchemy
  models.py          Esquemas de validación de entrada y salida (Pydantic)
  routers/           Un módulo por recurso: auth, clientes, barberos, servicios, citas
db/
  schema.sql                 Creación del esquema `daw`, tablas, índices y permisos
  migracion_01_usuarios.sql  Tabla de usuarios y vínculo con cliente (Proyecto 04)
  rollback.sql               Reversión completa de los cambios en la base de datos
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

Si el esquema aún no existe, ejecute `db/schema.sql` y después `db/migracion_01_usuarios.sql`
sobre la base de datos. Para deshacer todos los cambios, `db/rollback.sql`.

## Autenticación

El acceso se resuelve con tokens JWT. La cuenta se crea en `POST /auth/registro`, que registra el
usuario junto con su ficha de cliente, y `POST /auth/login` devuelve el token con el que se firman
las peticiones posteriores.

| Endpoint | Acceso | Descripción |
|---|---|---|
| `POST /auth/registro` | Público | Crea una cuenta de cliente y devuelve un token. |
| `POST /auth/login` | Público | Verifica las credenciales y emite un token. |
| `GET /auth/yo` | Autenticado | Devuelve los datos de la cuenta dueña del token. |

El token viaja en la cabecera `Authorization`:

```
Authorization: Bearer <token>
```

Decisiones de seguridad:

- Las contraseñas se guardan solo como hash bcrypt, con sal aleatoria por contraseña (RN-05). El
  sistema no almacena ni puede recuperar el texto plano.
- El token tiene vigencia limitada, configurable con `JWT_MINUTOS_VIGENCIA` (RN-06). Una vez
  expirado, la API responde `401` y obliga a autenticarse de nuevo.
- El secreto de firma se lee de `JWT_SECRETO` y nunca se versiona.
- El inicio de sesión responde lo mismo ante un correo inexistente que ante una contraseña
  incorrecta, para no revelar qué correos están registrados (RN-20).
- El rol administrador no se puede obtener desde la API: `POST /auth/registro` crea siempre
  cuentas con rol `cliente` (RN-04).

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
