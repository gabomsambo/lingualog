FROM node:18-alpine

WORKDIR /app

# Copy package files for dependency installation
COPY v0_lingua-log/package*.json ./

# Install dependencies
RUN npm install --legacy-peer-deps

# For development with volume mounting, we don't copy all files here
# Instead, we rely on the volume mount to provide the source code
# Copy only essential files that won't change frequently
COPY v0_lingua-log/next.config.mjs ./
COPY v0_lingua-log/tailwind.config.ts ./
COPY v0_lingua-log/postcss.config.mjs ./
COPY v0_lingua-log/tsconfig.json ./
COPY v0_lingua-log/components.json ./

EXPOSE 3000

# Use development mode for hot reloading when volume is mounted
CMD ["npm", "run", "dev"] 