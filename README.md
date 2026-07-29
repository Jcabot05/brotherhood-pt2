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

## Antecedente

Proyecto 03 — API construida, desplegada y verificada (22/22 pruebas de extremo a extremo):
[alejandrotapia20/brotherhood-api](https://github.com/alejandrotapia20/brotherhood-api)
