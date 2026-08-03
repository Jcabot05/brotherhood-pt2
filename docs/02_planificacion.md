# Fase de Planificación

**Proyecto 04 — Desarrollo de Aplicaciones Web**
Cliente: TheBrotherhood (barbería) · Integrantes: Alejandro Tapia · Jeremías Cabot

---

## 1. Repositorio de trabajo colaborativo

| Dato | Valor |
|---|---|
| Repositorio | https://github.com/Jcabot05/brotherhood-pt2 |
| Propietario | Jeremías Cabot (`Jcabot05`) |
| Colaborador | Alejandro Tapia (`alejandrotapia20`), permiso de escritura |
| Visibilidad | Público |
| Rama por defecto | `main` |
| Antecedente | https://github.com/alejandrotapia20/brotherhood-api (Proyecto 03) |

El repositorio es el espacio central del proyecto: aloja el código del backend, la documentación
de cada fase y el historial de cambios. Ambos integrantes trabajan sobre el mismo repositorio con
permiso de escritura, sin necesidad de forks.

### Organización de carpetas prevista

```
brotherhood-pt2/
├── app/
│   ├── auth/          # autenticación, hash de contraseñas, emisión y lectura de tokens
│   ├── routers/       # un módulo por recurso
│   ├── models.py      # esquemas de entrada y salida
│   ├── tablas.py      # definición de tablas
│   └── database.py    # conexión a PostgreSQL
├── db/                # scripts SQL de esquema
├── docs/              # documentación por fase
├── tests/             # pruebas de endpoints
└── main.py            # punto de entrada de la aplicación
```

---

## 2. Estrategia de ramas

El equipo adopta un modelo **GitHub Flow**: una rama estable permanente y ramas de vida corta por
tarea. Es el modelo adecuado para un equipo de dos personas con entregas frecuentes, porque evita
la sobrecarga de mantener varias ramas de larga duración sin renunciar al aislamiento del trabajo
en curso.

### Ramas permanentes

| Rama | Propósito |
|---|---|
| `main` | Código estable y desplegable. Refleja lo que se entrega al profesor. Nunca se hace commit directo. |

### Ramas de trabajo

Se crean desde `main`, viven mientras dure la tarea y se eliminan tras integrarse.

| Prefijo | Uso | Ejemplo |
|---|---|---|
| `feature/` | Funcionalidad nueva | `feature/auth-login` |
| `fix/` | Corrección de un defecto | `fix/validacion-fecha-pasada` |
| `docs/` | Documentación | `docs/analisis-planificacion` |
| `test/` | Pruebas | `test/citas-autenticadas` |

**Convención de nombre:** `<prefijo>/<descripción-en-kebab-case>`. Descripción breve, en
minúsculas, sin tildes ni caracteres especiales.

### Flujo de trabajo

1. Actualizar la rama local: `git switch main && git pull`.
2. Crear la rama de la tarea: `git switch -c feature/nombre-tarea`.
3. Trabajar con commits pequeños y con mensaje descriptivo en español, en modo imperativo
   ("Añadir validación de horario", no "añadidos cambios").
4. Subir la rama: `git push -u origin feature/nombre-tarea`.
5. Abrir un Pull Request hacia `main` describiendo qué cambia y por qué.
6. El otro integrante revisa el PR y aprueba o comenta.
7. Integrar con **Squash and merge** para mantener un historial lineal y legible en `main`.
8. Eliminar la rama ya integrada.

### Reglas de protección de `main`

- Prohibido el push directo: todo entra por Pull Request.
- Un Pull Request necesita la aprobación del otro integrante antes de integrarse.
- Las pruebas de endpoints deben pasar antes de integrar.

### Resolución de conflictos

Quien abre el Pull Request es responsable de resolver los conflictos: actualiza su rama con
`git pull origin main`, resuelve localmente, verifica que la aplicación siga funcionando y vuelve
a subir. Los conflictos se resuelven antes de pedir revisión, no durante.

---

## 3. Roles y responsabilidades

| Integrante | Rol | Responsabilidades |
|---|---|---|
| **Jeremías Cabot** | Backend — Autenticación y seguridad | Registro y login de usuarios; hash de contraseñas; emisión y validación de tokens; middleware de permisos y roles; aplicar RN-01 a RN-06; administrar el repositorio (protección de `main`, gestión de colaboradores). |
| **Alejandro Tapia** | Backend — Recursos y reglas de negocio | Endpoints de servicios (RF-04) y citas (RF-05); validación de disponibilidad (RF-07); aplicar RN-07 a RN-20; esquema de base de datos; pruebas de endpoints; despliegue. |

### Responsabilidades compartidas

Ambos integrantes revisan los Pull Requests del otro, mantienen la documentación de la fase que
les toca y participan en la redacción del reporte final. Ninguna rama se integra a `main` sin la
revisión del compañero.

### Reparto por historia de usuario

| Historia | Responsable principal | Apoyo |
|---|---|---|
| HU-01 — Catálogo público de servicios | Alejandro Tapia | Jeremías Cabot (revisión) |
| HU-02 — Agendar cita autenticada | Alejandro Tapia (lógica de cita y disponibilidad) | Jeremías Cabot (capa de autenticación y permisos) |

HU-02 depende de la capa de autenticación, así que el trabajo de Jeremías Cabot va primero en el
orden de ejecución: hasta que exista emisión y validación de tokens, el endpoint de creación de
citas no puede exigirlos.

---

## 4. Coordinación

- **Canal de comunicación:** WhatsApp para coordinación diaria; los Pull Requests para todo lo
  que sea discusión técnica sobre el código, de modo que quede registrada.
- **Punto de sincronización:** revisión conjunta al cerrar cada fase, antes de etiquetar la
  entrega.
- **Registro de avance:** el historial de commits y los Pull Requests integrados son la evidencia
  del trabajo de cada integrante.
