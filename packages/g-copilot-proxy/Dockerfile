# Dockerfile for g-copilot-proxy (TypeScript version)
# Single runtime (Node.js) - no Python needed!

FROM node:20-alpine AS builder

# Install build dependencies
RUN apk add --no-cache python3 make g++

WORKDIR /app

# Copy package files
COPY package-ts.json package.json
COPY tsconfig.json ./
COPY vitest.config.ts ./

# Install dependencies
RUN npm ci

# Copy source code
COPY src/ ./src/

# Build TypeScript
RUN npm run build

# Runtime stage
FROM node:20-alpine AS runtime

# Install dumb-init for proper signal handling
RUN apk add --no-cache dumb-init

WORKDIR /app

# Copy package files
COPY package-ts.json package.json

# Install production dependencies only
RUN npm ci --only=production

# Copy built files from builder
COPY --from=builder /app/dist ./dist

# Create data directory for auth storage
RUN mkdir -p /app/data

# Create non-root user
RUN addgroup -g 1001 -S appuser && \
    adduser -S -u 1001 -G appuser appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD node -e "require('node-fetch').default('http://localhost:8000/health')" || exit 1

# Run the app
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "dist/index.js"]
