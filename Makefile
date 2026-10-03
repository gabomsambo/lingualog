.PHONY: test test-backend dev stop sync-local-env prepare-db reset-db

# Run backend tests
test-backend:
	cd backend && pytest

# Master test command (will include frontend tests in the future)
test: test-backend
	@echo "All tests completed." 

SUPABASE_NPX ?= npx supabase

sync-local-env:
	@SUPABASE_CMD="$(SUPABASE_NPX)" ./scripts/sync-local-env.sh

prepare-db:
	@SUPABASE_CMD="$(SUPABASE_NPX)" ./scripts/prepare-local-db.sh

reset-db:
	@$(SUPABASE_NPX) db reset --local

dev:
	@$(SUPABASE_NPX) start
	@$(MAKE) sync-local-env
	@$(MAKE) prepare-db
	@docker compose up --build -d
	@echo "Supabase Studio: http://127.0.0.1:54323"
	@echo "App: http://localhost:3000"
	@echo "API docs: http://localhost:8000/docs"

stop:
	@docker compose down
	@$(SUPABASE_NPX) stop