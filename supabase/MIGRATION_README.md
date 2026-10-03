# Supabase Migrations Guide

LinguaLog now uses Supabase CLI migrations from `supabase/migrations/`.

## Source of truth

- `supabase/config.toml`: local Supabase config
- `supabase/migrations/`: schema migrations (applied in timestamp order)
- `supabase/seed.sql`: demo auth user + sample journal/vocabulary data

## Local reset

```bash
~/.nvm/versions/node/v22.23.1/bin/npx supabase start
~/.nvm/versions/node/v22.23.1/bin/npx supabase db reset --local
```

`db reset` rebuilds from scratch and runs `seed.sql` automatically.

## Notes

- The old `supabase/sql/` folder is legacy history and is not used by CLI resets.
- Baseline migration includes tables required by the app: `users`, `user_settings`,
  `journal_entries`, `user_vocabulary`, and `word_ai_cache`.
- RLS is owner-only (`auth.uid()` ownership checks).
