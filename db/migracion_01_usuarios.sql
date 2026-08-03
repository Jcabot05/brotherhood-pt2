-- =====================================================================
-- MIGRACION 01 — Autenticacion de usuarios
-- Proyecto 04 (Desarrollo de Aplicaciones Web) — TheBrotherhood
--
-- Incorpora la capa de autenticacion sobre el esquema academico `daw`.
-- Cubre las reglas de negocio RN-05 (contrasenas siempre con hash) y
-- RN-04 (distincion entre usuario cliente y usuario administrador).
--
-- ADVERTENCIA — Aislamiento del cliente real
-- Este script es ESTRICTAMENTE ADITIVO y opera solo dentro del esquema
-- `daw`. No contiene ninguna sentencia `drop`, no altera el tipo de
-- ninguna columna existente y no modifica dato alguno de las tablas ya
-- creadas en el Proyecto 03. El esquema `public`, donde opera el
-- cliente real, no se toca en ningun punto.
-- =====================================================================

-- --------------------------------------------------------------------
-- Tabla de usuarios
-- --------------------------------------------------------------------
-- La contrasena se almacena unicamente como hash bcrypt (RN-05). El
-- sistema nunca guarda ni puede recuperar la contrasena en texto plano.

create table if not exists daw.usuario (
    id_usuario       bigint generated always as identity primary key,
    correo           text not null unique,
    contrasena_hash  text not null,
    rol              text not null default 'cliente',
    activo           boolean not null default true,
    creado_en        timestamptz not null default now(),
    constraint usuario_correo_formato check (correo ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'),
    constraint usuario_rol_valido check (rol in ('cliente', 'admin'))
);

create index if not exists usuario_correo_idx on daw.usuario (correo);

-- --------------------------------------------------------------------
-- Vinculo entre usuario y cliente
-- --------------------------------------------------------------------
-- Columna NULLABLE: las filas de `cliente` que ya existen desde el
-- Proyecto 03 siguen siendo validas sin usuario asociado. La restriccion
-- unica impide que dos clientes compartan la misma cuenta.

alter table daw.cliente
    add column if not exists id_usuario bigint;

do $$
begin
    if not exists (
        select 1 from pg_constraint where conname = 'cliente_id_usuario_fkey'
    ) then
        alter table daw.cliente
            add constraint cliente_id_usuario_fkey
            foreign key (id_usuario) references daw.usuario (id_usuario)
            on delete set null;
    end if;
end $$;

do $$
begin
    if not exists (
        select 1 from pg_constraint where conname = 'cliente_id_usuario_unico'
    ) then
        alter table daw.cliente
            add constraint cliente_id_usuario_unico unique (id_usuario);
    end if;
end $$;

-- --------------------------------------------------------------------
-- Permisos y RLS
-- --------------------------------------------------------------------
-- Mismo criterio que el resto del esquema `daw`: el rol `daw_api` es el
-- unico con el que se conecta la API, y sus privilegios no alcanzan al
-- esquema `public`.

grant select, insert, update, delete on daw.usuario to daw_api;
grant usage, select on all sequences in schema daw to daw_api;

grant all on daw.usuario to anon, authenticated, service_role;

alter table daw.usuario enable row level security;

do $$
begin
    if not exists (
        select 1 from pg_policies
        where schemaname = 'daw' and tablename = 'usuario'
          and policyname = 'daw_usuario_acceso_api'
    ) then
        create policy daw_usuario_acceso_api on daw.usuario
            for all to daw_api using (true) with check (true);
    end if;
end $$;
