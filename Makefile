.PHONY: test test-backend dev stop sync-local-env

# Run backend tests
test-backend:
	cd backend && pytest

# Master test command (will include frontend tests in the future)
test: test-backend
	@echo "All tests completed." 

SUPABASE_NPX=~/.nvm/versions/node/v22.23.1/bin/npx supabase

sync-local-env:
	@env_output="$$( $(SUPABASE_NPX) status -o env )"; \
	api_url="$$(printf '%s\n' "$$env_output" | awk -F= '/^API_URL=/{print $$2}')"; \
	anon_key="$$(printf '%s\n' "$$env_output" | awk -F= '/^ANON_KEY=/{sub(/^ANON_KEY=/, ""); print}')"; \
	service_key="$$(printf '%s\n' "$$env_output" | awk -F= '/^SERVICE_ROLE_KEY=/{sub(/^SERVICE_ROLE_KEY=/, ""); print}')"; \
	if [ -z "$$api_url" ] || [ -z "$$anon_key" ] || [ -z "$$service_key" ]; then \
		echo "Could not parse local Supabase env output."; \
		exit 1; \
	fi; \
	printf "SUPABASE_URL=http://host.docker.internal:54321\nSUPABASE_SERVICE_KEY=%s\nOPENAI_API_KEY=\nOPEN_AI_API_KEY=\nGEMINI_API_KEY=\nUSE_MISTRAL=false\nAPI_PORT=8000\nWEB_PORT=3000\nNEXT_PUBLIC_API_URL=http://localhost:8000\nCORS_ALLOW_ORIGINS=http://localhost:3000\n" "$$service_key" > .env; \
	printf "NEXT_PUBLIC_SUPABASE_URL=%s\nNEXT_PUBLIC_SUPABASE_ANON_KEY=%s\nNEXT_PUBLIC_API_URL=http://localhost:8000\n" "$$api_url" "$$anon_key" > frontend/v0_lingua-log/.env.local

dev:
	@$(SUPABASE_NPX) start
	@$(MAKE) sync-local-env
	@$(SUPABASE_NPX) db reset --local
	@docker compose up --build -d
	@echo "Supabase Studio: http://127.0.0.1:54323"
	@echo "App: http://localhost:3000"
	@echo "API docs: http://localhost:8000/docs"

stop:
	@docker compose down
	@$(SUPABASE_NPX) stop