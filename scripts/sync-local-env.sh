#!/usr/bin/env bash
set -euo pipefail

SUPABASE_CMD="${SUPABASE_CMD:-npx supabase}"
ROOT_ENV=".env"
WEB_ENV="frontend/v0_lingua-log/.env.local"

set_env() {
  local file="$1" key="$2" value="$3"
  if grep -q "^${key}=" "$file"; then
    awk -v k="$key" -v v="$value" 'index($0, k "=") == 1 { print k "=" v; next } { print }' "$file" > "$file.tmp"
    mv "$file.tmp" "$file"
  else
    printf '%s=%s\n' "$key" "$value" >> "$file"
  fi
}

env_output="$($SUPABASE_CMD status -o env)"
read_var() { printf '%s\n' "$env_output" | awk -v k="$1" 'index($0, k "=") == 1 { v = substr($0, length(k) + 2); gsub(/^"|"$/, "", v); print v }'; }
api_url="$(read_var API_URL)"
anon_key="$(read_var ANON_KEY)"
service_key="$(read_var SERVICE_ROLE_KEY)"

if [ -z "$api_url" ] || [ -z "$anon_key" ] || [ -z "$service_key" ]; then
  echo "Could not parse local Supabase env output."
  exit 1
fi

[ -f "$ROOT_ENV" ] || cp .env.example "$ROOT_ENV"
[ -f "$WEB_ENV" ] || cp frontend/v0_lingua-log/.env.example "$WEB_ENV"

set_env "$ROOT_ENV" SUPABASE_URL "http://host.docker.internal:54321"
set_env "$ROOT_ENV" SUPABASE_SERVICE_KEY "$service_key"
set_env "$WEB_ENV" NEXT_PUBLIC_SUPABASE_URL "$api_url"
set_env "$WEB_ENV" NEXT_PUBLIC_SUPABASE_ANON_KEY "$anon_key"
