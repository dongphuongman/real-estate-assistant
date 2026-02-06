FROM node:20-alpine3.20 AS deps
WORKDIR /app
# Don't use apk upgrade as it can introduce variability
RUN apk add --no-cache libc6-compat
# Copy only frontend package files to avoid workspace issues
# The root package.json has workspaces config that causes issues in Docker
COPY apps/web/package*.json ./
RUN npm install

FROM node:20-alpine3.20 AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY apps/web ./apps/web
WORKDIR /app/apps/web
RUN npm run build

FROM node:20-alpine3.20 AS runner
WORKDIR /app
ENV NODE_ENV=production
# Don't use apk upgrade - add specific packages only
RUN apk add --no-cache curl wget dumb-init
RUN rm -rf /usr/local/lib/node_modules/npm /usr/local/bin/npm /usr/local/bin/npx
# Note: package.json name is "frontend", so Next.js creates .next/standalone/frontend/
COPY --from=builder /app/apps/web/.next/standalone ./frontend
COPY --from=builder /app/apps/web/.next/static ./frontend/.next/static
WORKDIR /app/frontend
EXPOSE 3000
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "server.js"]
