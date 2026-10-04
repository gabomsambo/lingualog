-- Level suggestions count only entries written since the learner reached the
-- current level. Accept and Settings both write user_language_profiles, so the
-- trigger stamps level_changed_at when a row is created with a level and
-- whenever immersion_level actually changes.

alter table public.user_language_profiles
  add column if not exists level_changed_at timestamptz;

comment on column public.user_language_profiles.level_changed_at is
  'When immersion_level was first set or last changed.';

create or replace function public.stamp_level_changed_at()
returns trigger
language plpgsql
as $$
begin
  if tg_op = 'INSERT' then
    new.level_changed_at = coalesce(new.level_changed_at, now());
  elsif new.immersion_level is distinct from old.immersion_level then
    new.level_changed_at = now();
  end if;
  return new;
end;
$$;

drop trigger if exists stamp_user_language_profiles_level_changed_at on public.user_language_profiles;
create trigger stamp_user_language_profiles_level_changed_at
before insert or update on public.user_language_profiles
for each row
execute function public.stamp_level_changed_at();
