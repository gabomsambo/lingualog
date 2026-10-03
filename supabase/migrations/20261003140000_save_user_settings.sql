-- One transaction for a settings save: per-language profiles and user_settings.
-- A failed user_settings update rolls back the profile rows, so the legacy
-- immersion_level never disagrees with the default language profile.

create or replace function public.save_user_settings(
  p_user_id uuid,
  p_settings jsonb,
  p_profiles jsonb
)
returns void
language plpgsql
security invoker
set search_path = public
as $$
begin
  if p_profiles is not null and jsonb_array_length(p_profiles) > 0 then
    insert into public.user_language_profiles (user_id, l2, immersion_level, proficiency)
    select p_user_id, p.l2, p.immersion_level, p.proficiency
    from jsonb_to_recordset(p_profiles) as p(l2 text, immersion_level smallint, proficiency text)
    on conflict (user_id, l2) do update
    set immersion_level = excluded.immersion_level,
        proficiency = excluded.proficiency;
  end if;

  if p_settings is not null and p_settings <> '{}'::jsonb then
    update public.user_settings s
    set (
      native_language, target_languages, email_notifications, push_notifications,
      daily_reminders, weekly_progress, reminder_time, theme, app_language,
      sound_effects, animations, difficulty_level, daily_goal, weekly_goal,
      auto_save, show_hints, public_profile, share_progress, analytics_opt_in,
      interface_lang, native_lang, default_target_lang, explanation_mode,
      explanation_mode_explicit, immersion_level, strictness, formality
    ) = (
      select
        r.native_language, r.target_languages, r.email_notifications, r.push_notifications,
        r.daily_reminders, r.weekly_progress, r.reminder_time, r.theme, r.app_language,
        r.sound_effects, r.animations, r.difficulty_level, r.daily_goal, r.weekly_goal,
        r.auto_save, r.show_hints, r.public_profile, r.share_progress, r.analytics_opt_in,
        r.interface_lang, r.native_lang, r.default_target_lang, r.explanation_mode,
        r.explanation_mode_explicit, r.immersion_level, r.strictness, r.formality
      from jsonb_populate_record(s, p_settings) as r
    )
    where s.user_id = p_user_id;

    if not found then
      raise exception 'No settings found to update for user %', p_user_id;
    end if;
  end if;
end;
$$;

revoke all on function public.save_user_settings(uuid, jsonb, jsonb) from public, anon, authenticated;
grant execute on function public.save_user_settings(uuid, jsonb, jsonb) to service_role;
