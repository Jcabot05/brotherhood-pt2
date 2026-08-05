-- =====================================================================
-- MIGRACION 02 — Estado activo del servicio
-- Proyecto 04 (Desarrollo de Aplicaciones Web) — TheBrotherhood
--
-- Habilita el retiro logico de servicios del catalogo, exigido por la
-- regla RN-16: un servicio con citas asociadas no se elimina fisicamente,
-- se marca como inactivo para preservar el historial de citas.
--
-- ADVERTENCIA — Aislamiento del cliente real
-- Script ESTRICTAMENTE ADITIVO, confinado al esquema `daw`. No contiene
-- ninguna sentencia `drop`, no altera el tipo de ninguna columna y no
-- borra dato alguno. El valor por defecto `true` deja los cuatro
-- servicios ya registrados visibles en el catalogo, tal como estan hoy.
-- El esquema `public`, donde opera el cliente real, no se toca.
-- =====================================================================

alter table daw.servicio
    add column if not exists activo boolean not null default true;

-- El listado publico filtra por `activo`; el indice evita recorrer la
-- tabla completa en cada consulta al catalogo.
create index if not exists servicio_activo_idx on daw.servicio (activo);
