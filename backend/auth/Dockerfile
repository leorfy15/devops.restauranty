# ---------- Dependencies ----------
FROM node:20-alpine AS deps

WORKDIR /app

COPY package*.json ./

RUN npm ci --omit=dev


# ---------- Production ----------
FROM node:20-alpine

WORKDIR /app

# Install available Alpine security patches
RUN apk upgrade --no-cache

# Remove npm/corepack from runtime image
RUN rm -rf \
    /usr/local/lib/node_modules/npm \
    /usr/local/lib/node_modules/corepack \
    /usr/local/bin/npm \
    /usr/local/bin/npx \
    /usr/local/bin/corepack

COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NODE_ENV=production

EXPOSE 3001

CMD ["node", "server.js"]