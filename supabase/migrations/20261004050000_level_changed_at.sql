-- Level suggestions count only entries written since the learner reached the
-- current level. Accept and Settings both update user_language_profiles, so
-- the trigger stamps level_changed_at whenever immersion_level actually changes.

alter table public.user_language_profiles
  add column if not exists level_changed_at timestamptz;

comment on column public.user_language_profiles.level_changed_at is
  'When immersion_level last changed. Null until the first change.';

create or replace function public.stamp_level_changed_at()
returns trigger
language plpgsql
as $$
begin
  if new.immersion_level is distinct from old.immersion_level then
    new.level_changed_at = now();
  end if;
  return new;
end;
$$;

drop trigger if exists stamp_user_language_profiles_level_changed_at on public.user_language_profiles;
create trigger stamp_user_language_profiles_level_changed_at
before update on public.user_language_profiles
for each row
execute function public.stamp_level_changed_at();
