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
main.py              Aplicación FastAPI: routers, manejo de errores y cliente web
web/
  index.html         Catálogo público de servicios (HU-01)
  login.html         Registro e inicio de sesión
  agendar.html       Formulario de cita y listado de citas propias (HU-02)
  api.js             Cliente de la API, sesión y traducción de errores HTTP
  estilos.css        Hoja de estilos, sin dependencias externas
app/
  database.py        Conexión a PostgreSQL (search_path limitado a `daw`)
  seguridad.py       Hash de contraseñas (bcrypt) y tokens de acceso (JWT)
  dependencias.py    Comprobaciones de autenticación y permisos para los routers
  tablas.py          Tablas del esquema `daw` para SQLAlchemy
  models.py          Esquemas de validación de entrada y salida (Pydantic)
  routers/           Un módulo por recurso: auth, clientes, barberos, servicios, citas
db/
  schema.sql                        Creación del esquema `daw`, tablas, índices y permisos
  migracion_01_usuarios.sql         Tabla de usuarios y vínculo con cliente (Proyecto 04)
  migracion_02_servicio_activo.sql  Retiro lógico de servicios del catálogo (Proyecto 04)
  rollback.sql                      Reversión completa de los cambios en la base de datos
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

Si el esquema aún no existe, ejecute en orden `db/schema.sql`,
`db/migracion_01_usuarios.sql` y `db/migracion_02_servicio_activo.sql` sobre la base de datos.
Para deshacer todos los cambios, `db/rollback.sql`.

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

## Catálogo de servicios (HU-01)

El catálogo es información comercial abierta: cualquier visitante puede consultarlo sin
credenciales antes de decidir si se registra. La administración, en cambio, exige rol
administrador.

| Endpoint | Acceso | Descripción |
|---|---|---|
| `GET /servicios/` | Público | Lista los servicios disponibles |
| `GET /servicios/{id}` | Público | Consulta un servicio por identificador |
| `POST /servicios/` | Administrador | Registra un servicio |
| `PUT /servicios/{id}` | Administrador | Actualiza un servicio |
| `DELETE /servicios/{id}` | Administrador | Retira el servicio del catálogo |
| `POST /servicios/{id}/reactivar` | Administrador | Lo reincorpora al catálogo |

`DELETE` **no borra el registro**: marca el servicio como inactivo (RN-16), de modo que
desaparece del listado público pero las citas que lo referencian conservan su historial. El
listado admite `?incluir_inactivos=true` para la administración del catálogo.

Un catálogo sin resultados devuelve `200` con un arreglo vacío, nunca un error.

## Citas (HU-02)

Agendar crea un compromiso con un barbero en un horario concreto y consume disponibilidad real
del negocio, por lo que toda operación sobre citas exige un token válido (RN-02).

| Endpoint | Acceso | Descripción |
|---|---|---|
| `GET /citas/disponibilidad` | Público | Horarios libres de un barbero para un servicio y día |
| `POST /citas/` | Autenticado | Agenda una cita a nombre del cliente del token |
| `GET /citas/` | Autenticado | Lista las citas propias (el administrador ve todas) |
| `GET /citas/{id}` | Autenticado | Consulta una cita propia |
| `PUT /citas/{id}` | Autenticado | Reprograma una cita propia |
| `PATCH /citas/{id}/estado` | Autenticado | Cambia el estado; *atendida* solo administrador |
| `DELETE /citas/{id}` | Autenticado | Cancela una cita propia |

El cuerpo de `POST /citas/` **no incluye `id_cliente`**: la cita se asocia siempre al dueño del
token, de modo que nadie pueda agendar en nombre de otro (RN-03).

```json
{
  "id_barbero": 1,
  "id_servicio": 2,
  "fecha_hora": "2026-09-15T14:00:00Z"
}
```

Reglas que gobiernan la operación:

- **RN-03** — un cliente solo consulta y modifica sus propias citas; operar sobre la cita de otro
  devuelve `403`. El administrador queda exento, porque gestiona la agenda del negocio.
- **RN-07** — un barbero no puede tener dos citas cuyos intervalos se solapen. El intervalo va
  desde la hora de la cita hasta esa hora más la duración del servicio, de modo que una reserva
  que empieza en mitad de otra se rechaza con `409`.
- **RN-08** — solo se agenda en fecha y hora futuras; una fecha pasada devuelve `422`.
- **RN-10** — la cita nace siempre en estado *agendada*.
- **RN-11** — una cita cancelada o atendida no se reprograma; su horario queda liberado.
- **RN-12** — una cita solo se cancela mientras su horario siga siendo futuro.
- **RN-17** — las fechas se manejan y almacenan en UTC.
- **RN-21 a RN-23** — la cita debe caer dentro del horario de atención, empezar en un intervalo
  regular y caber completa antes del cierre.

### Horarios de reserva

La barbería atiende de lunes a sábado, de 9:00 a 19:00, y las citas empiezan cada 30 minutos. Un
horario fuera de esa franja, con minutos arbitrarios o que no alcance a terminar antes del cierre
se rechaza con `422` y un mensaje que explica el motivo.

Para no dejar que el usuario descubra esas restricciones por ensayo y error,
`GET /citas/disponibilidad` devuelve las franjas realmente reservables:

```
GET /citas/disponibilidad?id_barbero=1&id_servicio=3&fecha=2026-09-14
```

```json
{
  "fecha": "2026-09-14",
  "duracion_min": 45,
  "atiende": true,
  "horario_atencion": "de lunes a sábado, de 9:00 a 19:00",
  "horarios": [
    { "inicio": "2026-09-14T14:00:00Z", "fin": "2026-09-14T14:45:00Z", "etiqueta": "09:00 a 09:45" }
  ]
}
```

La lista descuenta las citas ya agendadas del barbero y los horarios que no dejan tiempo antes del
cierre, de modo que depende del servicio elegido: un combo de 45 minutos ofrece menos franjas que
un corte de 30.

El horario se configura con variables de entorno (`HORA_APERTURA`, `HORA_CIERRE`,
`INTERVALO_MINUTOS`, `DIAS_LABORABLES`, `ZONA_HORARIA`), así que ajustarlo no exige tocar el
código.

## Ejecución

```bash
fastapi dev main.py
```

La API queda en `http://127.0.0.1:8000` y la documentación interactiva en
`http://127.0.0.1:8000/docs`.

## Cliente web

La misma aplicación sirve un cliente web en `http://127.0.0.1:8000/app/`, de modo que no hace
falta levantar un segundo servidor ni ejecutar un paso de construcción.

| Página | Ruta | Acceso |
|---|---|---|
| Catálogo de servicios | `/app/` | Público |
| Registro e inicio de sesión | `/app/login.html` | Público |
| Agendar cita y ver las propias | `/app/agendar.html` | Requiere sesión |

Está escrito en HTML, CSS y JavaScript sin dependencias externas: no usa CDN ni paquetes, así que
funciona sin conexión mientras la API esté en marcha.

El token se guarda en `sessionStorage`, de modo que la sesión termina al cerrar la pestaña. Los
errores de la API se muestran con su código y un mensaje legible: `401` invita a acceder de nuevo,
`403` explica la falta de permisos, `409` describe el conflicto de horario y `422` enumera los
campos inválidos.

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
