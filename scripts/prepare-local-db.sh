#!/usr/bin/env bash
set -euo pipefail

SUPABASE_CMD="${SUPABASE_CMD:-npx supabase}"
PROJECT_ID="$(awk -F'"' '/^project_id *=/ { print $2; exit }' supabase/config.toml)"
DB_CONTAINER="supabase_db_${PROJECT_ID}"

has_schema="$(docker exec "$DB_CONTAINER" psql -U postgres -d postgres -tAc \
  "select to_regclass('public.users') is not null" 2>/dev/null || true)"

if [ "$has_schema" = "t" ]; then
  echo "Existing local database found; applying pending migrations only."
  $SUPABASE_CMD migration up --local
else
  echo "Local database not initialized; resetting with migrations and seed."
  $SUPABASE_CMD db reset --local
fi
