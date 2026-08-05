-- =====================================================================
-- ROLLBACK — Proyecto 03 (Desarrollo de Aplicaciones Web)
-- Base de datos: PostgreSQL sobre Supabase
--
-- Deja la base de datos exactamente como estaba antes del proyecto
-- academico. Ejecutar en el SQL Editor de Supabase una vez entregado y
-- calificado el proyecto.
-- =====================================================================

-- ---------------------------------------------------------------------
-- ESTADO ORIGINAL (verificado antes de iniciar el proyecto)
--
-- Esquema `public` — datos reales del cliente, NUNCA modificados:
--     base_conocimiento   28 filas    RLS activo
--     contactos           13 filas    RLS activo
--     conversaciones      77 filas    RLS activo
--     servicios            0 filas    RLS activo
--     task                 0 filas    RLS activo, 4 politicas
--
-- Esquema `daw` — no existia. Creado por este proyecto.
-- Rol `daw_api` — no existia. Creado por este proyecto.
--
-- Configuracion de la Data API: NO fue modificada. Se intento exponer el
-- esquema `daw` en el dashboard, pero el cambio no persistio (incidente de
-- Supabase). La API se conecta por Postgres directo, de modo que la lista de
-- "Exposed schemas" permanece con su valor original: public, graphql_public.
-- No hay nada que revertir en el dashboard.
-- ---------------------------------------------------------------------


-- ---------------------------------------------------------------------
-- 1. Eliminar el rol dedicado del proyecto academico.
--    Primero se retiran sus privilegios y las politicas RLS que lo nombran;
--    de lo contrario Postgres impide eliminar el rol por dependencias.
--    (Las politicas se eliminan igualmente con el DROP SCHEMA del paso 2,
--    pero se listan aqui de forma explicita para dejar constancia.)
-- ---------------------------------------------------------------------
drop policy if exists daw_cliente_acceso_api  on daw.cliente;
drop policy if exists daw_barbero_acceso_api  on daw.barbero;
drop policy if exists daw_servicio_acceso_api on daw.servicio;
drop policy if exists daw_cita_acceso_api     on daw.cita;
drop policy if exists daw_usuario_acceso_api  on daw.usuario;

revoke all on all tables in schema daw from daw_api;
revoke all on all sequences in schema daw from daw_api;
revoke all on schema daw from daw_api;
revoke connect on database postgres from daw_api;

alter default privileges in schema daw
    revoke select, insert, update, delete on tables from daw_api;
alter default privileges in schema daw
    revoke usage, select on sequences from daw_api;

drop owned by daw_api;
drop role if exists daw_api;


-- ---------------------------------------------------------------------
-- 2. Eliminar el esquema academico completo.
--    CASCADE arrastra: daw.cliente, daw.barbero, daw.servicio, daw.cita,
--    daw.usuario (Proyecto 04), sus indices (incl. cita_barbero_horario_unico,
--    usuario_correo_idx y servicio_activo_idx), sus politicas RLS, sus claves
--    foraneas (incl. cliente.id_usuario), las columnas anadidas por el
--    Proyecto 04 (cliente.id_usuario, servicio.activo) y sus secuencias
--    de identidad.
-- ---------------------------------------------------------------------
drop schema if exists daw cascade;


-- ---------------------------------------------------------------------
-- 3. VERIFICACION POSTERIOR
--    Las cinco tablas del cliente deben seguir presentes con sus conteos
--    originales, el esquema `daw` no debe existir y el rol `daw_api` tampoco.
-- ---------------------------------------------------------------------

-- 3.a El esquema daw ya no existe (debe devolver 0 filas).
--     select schema_name from information_schema.schemata where schema_name = 'daw';

-- 3.b El rol daw_api ya no existe (debe devolver 0 filas).
--     select rolname from pg_roles where rolname = 'daw_api';

-- 3.c Las tablas del cliente estan intactas (deben coincidir con el estado original).
--     select 'base_conocimiento' as tabla, count(*) from public.base_conocimiento
--     union all select 'contactos',      count(*) from public.contactos
--     union all select 'conversaciones', count(*) from public.conversaciones
--     union all select 'servicios',      count(*) from public.servicios
--     union all select 'task',           count(*) from public.task;
