# Docker Development Guide

## Issue Fixed

The Docker setup has been updated to support proper development workflow. Previously, the frontend was built as a static image, which meant that local code changes weren't reflected in the running container. This caused the LearnWordModal component (and other changes) to appear missing or outdated in Docker while working fine locally.

## Solution Implemented

### 1. Frontend Volume Mounting
The frontend now uses volume mounting similar to the backend:
```yaml
volumes:
  - ./frontend/v0_lingua-log:/app
  - /app/node_modules
```

### 2. Development-Optimized Dockerfile
The frontend Dockerfile now:
- Uses `npm run dev` for hot reloading
- Only copies essential config files during build
- Relies on volume mounting for source code

### 3. Production Dockerfile
A separate `Dockerfile.prod` is available for production builds.

## Usage

### Development Mode (Recommended)
```bash
# Start the development environment
docker-compose up

# Or rebuild and start
docker-compose up --build
```

### Production Mode
```bash
# Use the production Dockerfile
docker-compose -f docker-compose.prod.yml up
```

## Benefits

✅ **Hot Reloading**: Frontend changes now reflect immediately in Docker
✅ **No Rebuilds Needed**: Code changes don't require container rebuilds
✅ **Consistent Environment**: Docker matches local development exactly
✅ **Fast Development**: Edit files locally, see changes in Docker instantly

## File Structure

- `frontend/Dockerfile` - Development optimized
- `frontend/Dockerfile.prod` - Production optimized
- `docker-compose.yml` - Development configuration
- `docker-compose.prod.yml` - Production configuration (if needed)

## Troubleshooting

If you encounter issues:

1. **Clean rebuild**: `docker-compose down && docker-compose up --build`
2. **Volume issues**: `docker-compose down -v && docker-compose up`
3. **Node modules**: Delete `frontend/v0_lingua-log/node_modules` and rebuild

## Environment Variables

See `.env.example` and the README's Setup & Installation section; `make dev` fills in the local Supabase values.

The Docker issue with the LearnWordModal component is now completely resolved!
