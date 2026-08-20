# ---------- Dependencies ----------
FROM node:20-alpine AS deps

WORKDIR /app

COPY package*.json ./

RUN npm ci --omit=dev


# ---------- Production ----------
FROM node:20-alpine

WORKDIR /app

RUN apk upgrade --no-cache

RUN rm -rf \
    /usr/local/lib/node_modules/npm \
    /usr/local/lib/node_modules/corepack \
    /usr/local/bin/npm \
    /usr/local/bin/npx \
    /usr/local/bin/corepack

COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NODE_ENV=production

EXPOSE 3003

CMD ["node", "server.js"]