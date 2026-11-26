begin;
create schema if not exists career_private;
do $$ begin
  if not exists(select from pg_roles where rolname='career_workspace') then
    create role career_workspace nologin nobypassrls;
  end if;
  execute format('grant career_workspace to %I',current_user);
end $$;
create table if not exists career_private.projects (
 user_id uuid not null, app_id text not null, id text not null, name text not null, revision bigint not null, state jsonb not null,
 primary key(user_id,app_id,id)
);
create table if not exists career_private.documents (
 user_id uuid not null, app_id text not null, id uuid not null, project_id text not null,
 primary key(user_id,app_id,id)
);
create sequence if not exists career_private.project_revisions;
grant usage on sequence career_private.project_revisions to career_workspace;
grant usage on schema career_private to career_workspace;
do $$ declare tab text; begin
 foreach tab in array array['projects','documents'] loop
 execute format('alter table career_private.%I enable row level security',tab);
 execute format('grant select, insert, update, delete on career_private.%I to career_workspace',tab);
 execute format('drop policy if exists own_workspace on career_private.%I',tab);
 execute format('create policy own_workspace on career_private.%I for all to career_workspace using
 (user_id=current_setting(''career.uid'',true)::uuid and app_id=current_setting(''career.app'',true))
 with check (user_id=current_setting(''career.uid'',true)::uuid and app_id=current_setting(''career.app'',true))',tab);
 end loop;
end $$;
-- Accounting is deliberately inaccessible to the workspace role and all client JWTs.
create table if not exists career_private.calls (
 id bigint generated always as identity primary key, day date not null, user_id uuid not null, app_id text not null, tokens integer
);
create index if not exists calls_day on career_private.calls(day,user_id,app_id);
create table if not exists career_private.billing (blocked boolean primary key check(blocked));
alter table career_private.calls enable row level security;
alter table career_private.billing enable row level security;
commit;
