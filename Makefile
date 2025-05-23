.PHONY: test test-backend

# Run backend tests
test-backend:
	cd backend && pytest

# Master test command (will include frontend tests in the future)
test: test-backend
	@echo "All tests completed." 