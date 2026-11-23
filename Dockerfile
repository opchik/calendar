# syntax=docker/dockerfile:1

ARG NODE_VERSION=22

# ── Сборка SvelteKit (adapter-static) ───────────────────────────
FROM node:${NODE_VERSION}-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY vite.config.js ./
COPY src ./src
RUN npm run build

# ── Runtime: статика + API-сервер + бот ─────────────────────────
FROM node:${NODE_VERSION}-alpine

ENV NODE_ENV=production \
    PORT=3000 \
    DATA_DIR=/data

WORKDIR /app

COPY --chown=node:node package.json ./
COPY --chown=node:node server ./server
COPY --from=build --chown=node:node /app/build ./static

RUN mkdir -p /data/files && chown -R node:node /data
USER node

EXPOSE 3000
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1:3000/healthz >/dev/null || exit 1

CMD ["node", "server/index.js"]
