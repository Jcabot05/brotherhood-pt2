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

- Python · Django · Django REST Framework
- React · Vite · React Router
- PostgreSQL (Supabase), esquema aislado `daw`
- Documentación interactiva vía Swagger/OpenAPI en `/docs`

## Estructura

```
manage.py            Punto de entrada de Django
config/
  settings.py        Configuración: base de datos, DRF, cookie de sesión, CORS
  urls.py            Rutas de primer nivel y documentación interactiva
  excepciones.py     Traducción de errores al contrato publicado (422, integridad)
apps/
  usuarios/
    models.py        Cuentas de acceso y fichas de cliente
    seguridad.py     Hash de contraseñas (bcrypt) y tokens de acceso (JWT)
    autenticacion.py Lectura de la sesión desde la cookie o la cabecera Bearer
    permisos.py      Reglas de acceso RN-01 a RN-04
    views.py         Registro, login, logout, cuenta propia y fichas de cliente
  catalogo/          Servicios y barberos (RF-02, RF-03, RF-04)
  citas/
    agenda.py        Horario de atención y generación de horarios reservables
    views.py         Agendar, consultar, reprogramar y cancelar (RF-05 a RF-09)
cliente/
  src/
    api/cliente.js   Peticiones a la API y traducción de errores HTTP
    api/sesion.jsx   Estado de la sesión, consultado al servidor
    paginas/         Servicios (HU-01), Acceso, Agendar (HU-02)
    componentes/     Barra de navegación y avisos
    estilos.css      Hoja de estilos, sin dependencias externas
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

Requiere Python 3.12 o superior y Node.js 18 o superior.

```bash
git clone https://github.com/Jcabot05/brotherhood-pt2.git
cd brotherhood-pt2

python3 -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate

pip install -r requirements.txt

cd cliente && npm install && cd ..
```

> El esquema de la base lo administran los scripts de `db/`, no las migraciones de Django: los
> modelos van declarados con `managed = False`. La base pertenece a un cliente real y su estructura
> se cambia con SQL revisado a mano, así que **no se ejecuta `makemigrations` ni `migrate`**.

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

Django sirve tanto la API como el cliente web, de modo que todo queda en **una sola dirección**:
`http://127.0.0.1:8000`.

```bash
cd cliente && npm run build && cd ..   # compila el cliente
python manage.py runserver
```

| Recurso | Dirección |
|---|---|
| Cliente web | `http://127.0.0.1:8000/` |
| API | `http://127.0.0.1:8000/servicios/`, `/citas/`, `/auth/`… |
| Documentación interactiva | `http://127.0.0.1:8000/docs` |

Que la interfaz y la API compartan origen no es sólo comodidad: es lo que permite mantener la
cookie de sesión en `SameSite=Lax` sin necesidad de un token CSRF aparte (ver más abajo).

El build queda en `static_build/`, que no se versiona. Hay que recompilar tras cambiar el código
del cliente.

### Desarrollo del cliente

Para trabajar sobre la interfaz conviene el servidor de Vite, que recompila al guardar:

```bash
# API, en una terminal
python manage.py runserver

# Cliente, en otra
cd cliente && npm run dev
```

Queda en `http://localhost:5173` y reenvía las peticiones de la API al backend, así que el
navegador las sigue viendo del mismo origen.

## Cliente web

| Página | Ruta | Acceso |
|---|---|---|
| Catálogo de servicios | `/` | Público |
| Registro e inicio de sesión | `/login` | Público |
| Agendar cita y ver las propias | `/agendar` | Requiere sesión |

Las rutas las resuelve react-router dentro del navegador. Django devuelve `index.html` para
cualquier dirección que no reclame la API, de modo que recargar la página en `/agendar` funciona
igual que llegar navegando.

Los errores de la API se muestran con un mensaje legible: `401` invita a acceder de nuevo, `403`
explica la falta de permisos, `409` describe el conflicto de horario y `422` enumera los campos
inválidos uno por uno.

### La sesión

El token de acceso viaja en una **cookie httpOnly**, no en el almacenamiento del navegador. La
diferencia importa: `localStorage` y `sessionStorage` son legibles por cualquier script de la
página, de modo que una inyección de código bastaría para llevarse la sesión. Marcada `httpOnly`,
la cookie queda fuera del alcance del JavaScript, incluido el que un atacante consiguiera
introducir.

Como consecuencia, el cliente no puede consultar el token para saber si sigue vigente: lo pregunta
al servidor con `GET /auth/yo`, que valida firma y vigencia. Esto detecta además las sesiones ya
caducadas, que antes se daban por buenas hasta que fallaba la primera petición.

Cerrar sesión exige `POST /auth/logout`, porque una cookie httpOnly sólo puede borrarla quien la
puso.

**Sobre CSRF.** La cookie va con `SameSite=Lax`, que impide al navegador enviarla en peticiones
originadas por otro sitio, salvo en navegaciones de primer nivel con `GET`. Como ninguna operación
de escritura de esta API usa `GET`, esa excepción no es aprovechable, y no hace falta un token CSRF
aparte. La conclusión depende de que el cliente y la API compartan origen: si el cliente se
desplegara en otro dominio, la cookie necesitaría `SameSite=None` y entonces sí habría que añadir
protección CSRF explícita.

## Pruebas

Las reglas del horario de atención (RN-21 a RN-23) se comprueban sin base de datos:

```bash
python manage.py test apps.citas
```

El recorrido completo sobre la API en marcha escribe en la base a la que ésta apunte:

```bash
python tests/prueba_endpoints.py http://127.0.0.1:8000
```

Sin argumento, corre contra la API local.

## Despliegue

La aplicación se publica en Railway desde la rama `produccion`, en un servicio conectado al
repositorio de GitHub. Un mismo servicio compila el cliente y atiende la API.

### Configuración del servicio

| Campo | Valor |
|---|---|
| Rama | `produccion` |
| Custom Build Command | `pip install -r requirements.txt && npm ci --prefix cliente && npm run build --prefix cliente` |
| Pre-deploy Step | `python manage.py collectstatic --noinput` |
| Custom Start Command | `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2` |

El orden del build no es intercambiable: `npm run build` deja el cliente en `static_build/`, y
`collectstatic` sólo recoge sus archivos si ese directorio ya existe. Invertirlos no da error;
sencillamente no recogería nada.

El Pre-deploy **no ejecuta `migrate` ni `createsuperuser`**. La base es externa y sus tablas las
crea `db/schema.sql`, de modo que los modelos declaran `managed = False`: una migración
escribiría sobre datos en uso. La creación de un superusuario tampoco aplica, porque el proyecto
no instala `django.contrib.auth` y resuelve la autenticación por su cuenta.

### Variables de entorno

| Variable | Valor en producción | Consecuencia de omitirla |
|---|---|---|
| `DATABASE_URL` | la cadena de Supabase | El servicio no arranca |
| `DJANGO_DEBUG` | `false` | Se exponen trazas internas ante cualquier error |
| `DJANGO_HOSTS_PERMITIDOS` | el dominio asignado | Django responde 400 a toda petición |
| `COOKIE_SEGURA` | `true` | La sesión no viaja y el acceso falla |
| `DJANGO_SECRET_KEY`, `JWT_SECRETO` | valores nuevos | Se comparten secretos con el entorno local |

El resto se documenta en `.env.example`. Con `DJANGO_DEBUG=false`, la configuración añade sola
`.up.railway.app` a los dominios admitidos y `https://*.up.railway.app` a los orígenes de
confianza, porque el subdominio no se conoce hasta que la plataforma lo asigna.

El dominio público se genera en **Settings → Networking**.

### Comprobación en local

Para reproducir lo que hace la plataforma:

```bash
cd cliente && npm ci && npm run build && cd ..
DJANGO_DEBUG=false DJANGO_REDIRIGIR_A_HTTPS=false python manage.py collectstatic --noinput
DJANGO_DEBUG=false DJANGO_REDIRIGIR_A_HTTPS=false gunicorn config.wsgi:application -b 127.0.0.1:8001
```

`DJANGO_REDIRIGIR_A_HTTPS=false` hace falta sólo en local, donde no hay certificado.

## Aislamiento de la base de datos

El proyecto Supabase pertenece a un cliente real en operación. **Todo el trabajo académico vive
en el esquema `daw`**, separado del esquema `public` donde corren los sistemas del cliente. El rol
`daw_api` con el que se conecta la API tiene los privilegios sobre `public` explícitamente
revocados, de modo que el aislamiento lo impone PostgreSQL y no la lógica de la aplicación.

## Antecedente

Proyecto 03 — API construida, desplegada y verificada (22/22 pruebas de extremo a extremo):
[alejandrotapia20/brotherhood-api](https://github.com/alejandrotapia20/brotherhood-api)
