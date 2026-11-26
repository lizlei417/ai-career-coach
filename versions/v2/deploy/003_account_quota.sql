-- Additive migration; old code remains compatible. No records/counters are reset.
-- Roll back application code first if necessary; added columns may safely remain.
begin;
alter table career_private.calls add column if not exists request_id text;
alter table career_private.calls add column if not exists step integer;
alter table career_private.calls add column if not exists status text not null default 'dispatched';
create unique index if not exists calls_request_step on career_private.calls(user_id,request_id,step) where request_id is not null;
create index if not exists calls_account_day on career_private.calls(user_id,day);
commit;
