-- Atomic per-key merge into journal_entries.meaning_translations_cache

create or replace function public.merge_meaning_translation(
  p_entry_id uuid,
  p_user_id uuid,
  p_key text,
  p_value jsonb
)
returns void
language sql
security invoker
set search_path = public
as $$
  update public.journal_entries
  set meaning_translations_cache =
    coalesce(meaning_translations_cache, '{}'::jsonb) || jsonb_build_object(p_key, p_value)
  where id = p_entry_id and user_id = p_user_id;
$$;

revoke all on function public.merge_meaning_translation(uuid, uuid, text, jsonb) from public, anon, authenticated;
grant execute on function public.merge_meaning_translation(uuid, uuid, text, jsonb) to service_role;
