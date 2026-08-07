# Fase de Análisis

**Proyecto 04 — Desarrollo de Aplicaciones Web**
Cliente: TheBrotherhood (barbería) · Integrantes: Alejandro Tapia · Jeremías Cabot

Continuación del Proyecto 03, donde se construyó y desplegó la REST API de gestión de citas
([brotherhood-api](https://github.com/alejandrotapia20/brotherhood-api)). En esta fase se
incorpora autenticación y control de permisos sobre dos de los requerimientos funcionales ya
especificados.

---

## 1. Requerimientos funcionales seleccionados

De los nueve requisitos funcionales definidos en el Proyecto 03, el equipo selecciona dos:

| ID | Requisito | Tipo de acceso |
|---|---|---|
| RF-04 | Listado de servicios | Público (sin autenticación) |
| RF-05 | Agendar cita | Autenticado (con permisos) |

**Justificación.** El catálogo de servicios es información comercial que la barbería quiere
mostrar abiertamente: cualquier persona que llegue al sitio debe poder ver qué se ofrece, a qué
precio y cuánto dura, sin ninguna barrera previa. Agendar una cita, en cambio, crea un
compromiso con un barbero en un horario concreto y consume disponibilidad real del negocio, por
lo que exige identificar quién reserva. Los dos requisitos cubren así los dos niveles de acceso
que pide la fase de análisis, y entre ambos existe una continuidad natural: el visitante consulta
el catálogo y, para reservar, debe autenticarse.

---

## 2. Historias de usuario

### HU-01 — Consultar el catálogo de servicios (acceso público)

> **Como** visitante del sitio de TheBrotherhood
> **quiero** ver la lista de servicios disponibles con su precio y duración estimada
> **para** decidir qué servicio me conviene reservar antes de crear una cuenta.

**Requisito asociado:** RF-04
**Endpoint:** `GET /servicios/`
**Autenticación:** no requerida

**Criterios de aceptación**

1. La petición se atiende sin enviar credenciales ni token; el sistema responde `200 OK`.
2. La respuesta es un arreglo JSON donde cada servicio incluye `id_servicio`, `nombre`, `precio`
   y `duracion_min`.
3. Un servicio marcado como inactivo no aparece en el listado.
4. Si el catálogo está vacío, la respuesta es `200 OK` con un arreglo vacío, no un error.
5. La respuesta no expone datos de clientes, barberos ni citas.
6. Consultar un servicio inexistente por identificador (`GET /servicios/{id}`) devuelve `404 Not
   Found` con un mensaje descriptivo.

---

### HU-02 — Agendar una cita (acceso autenticado)

> **Como** cliente registrado de TheBrotherhood
> **quiero** agendar una cita indicando barbero, servicio y fecha/hora
> **para** asegurar mi lugar sin tener que escribir por WhatsApp.

**Requisito asociado:** RF-05 (con RF-07, validación de disponibilidad, como regla de negocio)
**Endpoint:** `POST /citas/`
**Autenticación:** requerida (token Bearer)

**Criterios de aceptación**

1. Sin token, la petición devuelve `401 Unauthorized` y la cita no se crea.
2. Con un token inválido o expirado, la petición devuelve `401 Unauthorized`.
3. Con un token válido, una cita correcta devuelve `201 Created` y el cuerpo incluye el
   `id_cita` asignado y el estado `agendada`.
4. La cita se asocia al cliente dueño del token; el cliente no puede agendar en nombre de otro.
5. Si el barbero ya tiene una cita que se solapa con el horario solicitado, la respuesta es `409
   Conflict` y no se crea el registro.
6. Si la fecha/hora está en el pasado, la respuesta es `422 Unprocessable Entity`.
7. Si el `id_barbero` o el `id_servicio` no existen, la respuesta es `404 Not Found`.
8. Faltar un campo obligatorio o enviar un formato de fecha inválido devuelve `422` con el
   detalle del campo que falló.
9. La cita creada queda registrada en la tabla `daw.cita` y es consultable por su identificador.

---

## 3. Reglas de negocio

Restricciones, condiciones y validaciones que gobiernan el comportamiento del sistema y deben
implementarse en el backend.

### Acceso y permisos

| ID | Regla |
|---|---|
| RN-01 | El catálogo de servicios es de lectura pública. Ninguna operación de lectura sobre `/servicios` exige autenticación. |
| RN-02 | Toda operación de escritura (crear, modificar, eliminar) exige un token válido. |
| RN-03 | Un cliente autenticado solo puede crear, consultar y modificar sus propias citas. Intentar operar sobre la cita de otro cliente devuelve `403 Forbidden`. |
| RN-04 | Solo un usuario con rol administrador puede crear, modificar o eliminar servicios y barberos. |
| RN-05 | Las contraseñas se almacenan siempre con hash; nunca en texto plano ni recuperables. |
| RN-06 | El token de sesión tiene una vigencia limitada; una vez expirado obliga a autenticarse de nuevo. |

### Agenda y disponibilidad

| ID | Regla |
|---|---|
| RN-07 | Un barbero no puede tener dos citas cuyos intervalos se solapen. El intervalo ocupado va desde la fecha/hora de la cita hasta esa hora más la duración del servicio. |
| RN-08 | Una cita solo puede agendarse en una fecha/hora futura. |
| RN-09 | El estado de una cita pertenece al conjunto cerrado `agendada`, `cancelada`, `atendida`. Ningún otro valor se acepta. |
| RN-10 | Una cita nueva nace siempre en estado `agendada`. |
| RN-11 | Una cita `cancelada` o `atendida` no puede reprogramarse; su horario queda liberado para otras reservas. |
| RN-12 | Una cita solo puede cancelarse mientras su horario siga siendo futuro. |

### Horario de atención

Reglas incorporadas durante la implementación. Al probar el sistema se advirtió que el horario de
atención de la barbería nunca se había especificado: las reglas anteriores admitían una reserva en
cualquier instante futuro, incluida la madrugada o un día de cierre. Las siguientes tres reglas
cierran ese vacío.

| ID | Regla |
|---|---|
| RN-21 | Una cita solo puede agendarse dentro del horario de atención de la barbería: de lunes a sábado, de 9:00 a 19:00. Los domingos no se atiende. |
| RN-22 | Los inicios de cita ocurren en intervalos regulares de 30 minutos. No se aceptan horarios con minutos arbitrarios. |
| RN-23 | El servicio reservado debe caber completo antes de la hora de cierre. Un servicio de 45 minutos no puede empezar a las 18:30. |

El horario y el intervalo son parámetros de configuración, de modo que un cambio en la operación
del negocio no exija modificar el código.

### Integridad de datos

| ID | Regla |
|---|---|
| RN-13 | Una cita exige la existencia previa de cliente, barbero y servicio. No se aceptan referencias huérfanas. |
| RN-14 | El correo electrónico de un cliente es único en el sistema y debe tener formato válido. |
| RN-15 | El precio y la duración de un servicio son valores mayores que cero. |
| RN-16 | Un servicio con citas asociadas no se elimina físicamente: se marca como inactivo para preservar el historial. |
| RN-17 | Todas las fechas y horas se manejan y almacenan en UTC; la conversión a hora local ocurre en el cliente. |

### Respuestas del sistema

| ID | Regla |
|---|---|
| RN-18 | Todas las peticiones y respuestas se manejan en formato JSON. |
| RN-19 | Cada error devuelve el código HTTP que corresponde a su causa: `401` sin credenciales, `403` sin permisos, `404` recurso ausente, `409` conflicto de horario, `422` datos inválidos. |
| RN-20 | Los mensajes de error describen el problema sin filtrar detalles internos de la base de datos ni del servidor. |

---

## 4. Trazabilidad

| Historia | Requisito | Reglas que la gobiernan |
|---|---|---|
| HU-01 | RF-04 | RN-01, RN-16, RN-18, RN-19 |
| HU-02 | RF-05, RF-07 | RN-02, RN-03, RN-06, RN-07, RN-08, RN-10, RN-13, RN-17, RN-18, RN-19, RN-21, RN-22, RN-23 |
