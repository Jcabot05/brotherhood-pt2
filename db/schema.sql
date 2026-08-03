-- =====================================================================
-- ESQUEMA — Proyecto 03 (Desarrollo de Aplicaciones Web)
-- REST API de gestion de citas — TheBrotherhood (barberia)
-- Base de datos: PostgreSQL sobre Supabase
--
-- Todo el proyecto academico vive en el esquema `daw`, aislado del
-- esquema `public` donde opera el cliente. Ver db/rollback.sql para
-- revertir estos cambios.
-- =====================================================================

create schema if not exists daw;

-- --------------------------------------------------------------------
-- Tablas (segun el diagrama entidad-relacion de la fase de Diseno)
-- --------------------------------------------------------------------

create table if not exists daw.cliente (
    id_cliente bigint generated always as identity primary key,
    nombre     text not null,
    telefono   text not null,
    correo     text not null,
    creado_en  timestamptz not null default now(),
    constraint cliente_correo_formato check (correo ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$')
);

create table if not exists daw.barbero (
    id_barbero   bigint generated always as identity primary key,
    nombre       text not null,
    especialidad text,
    creado_en    timestamptz not null default now()
);

create table if not exists daw.servicio (
    id_servicio  bigint generated always as identity primary key,
    nombre       text not null,
    precio       numeric(10, 2) not null,
    duracion_min integer not null,
    creado_en    timestamptz not null default now(),
    constraint servicio_precio_no_negativo check (precio >= 0),
    constraint servicio_duracion_positiva check (duracion_min > 0)
);

create table if not exists daw.cita (
    id_cita     bigint generated always as identity primary key,
    id_cliente  bigint not null references daw.cliente (id_cliente) on delete cascade,
    id_barbero  bigint not null references daw.barbero (id_barbero) on delete cascade,
    id_servicio bigint not null references daw.servicio (id_servicio) on delete cascade,
    fecha_hora  timestamptz not null,
    estado      text not null default 'agendada',
    creado_en   timestamptz not null default now(),
    constraint cita_estado_valido check (estado in ('agendada', 'cancelada', 'atendida'))
);

-- RF-07: un barbero no puede tener dos citas agendadas en el mismo horario.
-- El indice unico parcial garantiza la regla a nivel de base de datos, ademas
-- de la verificacion que hace la API antes de insertar.
create unique index if not exists cita_barbero_horario_unico
    on daw.cita (id_barbero, fecha_hora)
    where estado = 'agendada';

create index if not exists cita_id_cliente_idx on daw.cita (id_cliente);
create index if not exists cita_fecha_hora_idx on daw.cita (fecha_hora);

-- --------------------------------------------------------------------
-- Permisos y RLS
-- --------------------------------------------------------------------

grant usage on schema daw to anon, authenticated, service_role;
grant all on all tables in schema daw to anon, authenticated, service_role;
grant all on all sequences in schema daw to anon, authenticated, service_role;

alter default privileges in schema daw
    grant all on tables to anon, authenticated, service_role;
alter default privileges in schema daw
    grant all on sequences to anon, authenticated, service_role;

alter table daw.cliente  enable row level security;
alter table daw.barbero  enable row level security;
alter table daw.servicio enable row level security;
alter table daw.cita     enable row level security;

-- La API academica no implementa autenticacion de usuarios (fuera del alcance
-- definido para el Proyecto 03), por lo que las politicas permiten el acceso
-- del rol anonimo sobre las tablas del esquema `daw`.
create policy daw_cliente_acceso  on daw.cliente  for all to anon, authenticated using (true) with check (true);
create policy daw_barbero_acceso  on daw.barbero  for all to anon, authenticated using (true) with check (true);
create policy daw_servicio_acceso on daw.servicio for all to anon, authenticated using (true) with check (true);
create policy daw_cita_acceso     on daw.cita     for all to anon, authenticated using (true) with check (true);

-- --------------------------------------------------------------------
-- Rol dedicado de la API
-- --------------------------------------------------------------------
-- La API se conecta a PostgreSQL con un rol propio, `daw_api`, cuyos privilegios
-- se limitan al esquema `daw`. El esquema `public` (donde reside la operacion
-- real del cliente) le queda explicitamente denegado, de modo que el aislamiento
-- lo impone la base de datos y no la logica de la aplicacion.

create role daw_api with login password '<definir_al_desplegar>';

grant connect on database postgres to daw_api;
grant usage on schema daw to daw_api;
grant select, insert, update, delete on all tables in schema daw to daw_api;
grant usage, select on all sequences in schema daw to daw_api;

alter default privileges in schema daw
    grant select, insert, update, delete on tables to daw_api;
alter default privileges in schema daw
    grant usage, select on sequences to daw_api;

revoke all on schema public from daw_api;
revoke all on all tables in schema public from daw_api;

-- Politicas RLS para el rol de la API sobre las tablas academicas.
create policy daw_cliente_acceso_api  on daw.cliente  for all to daw_api using (true) with check (true);
create policy daw_barbero_acceso_api  on daw.barbero  for all to daw_api using (true) with check (true);
create policy daw_servicio_acceso_api on daw.servicio for all to daw_api using (true) with check (true);
create policy daw_cita_acceso_api     on daw.cita     for all to daw_api using (true) with check (true);
