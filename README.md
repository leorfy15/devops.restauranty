# Restauranty

A restaurant management platform built with a **microservices architecture**: 3 Node.js/Express backends + a React frontend, unified behind HAProxy path-based routing.

## Architecture

```
                         ┌────────────────────────┐
                         │   HAProxy / Ingress    │
    Browser ───────────► │       (port 80)        │
                         └───────────┬────────────┘
                                     │
            ┌────────────────────────┼─────────────────────────┐
            │                        │                         │
       /api/auth/*             /api/items/*             /api/discounts/*
            │                        │                         │
   ┌────────▼────────┐     ┌─────────▼─────────┐    ┌─────────▼──────────┐
   │  Auth Service   │     │  Items Service    │    │ Discounts Service  │
   │   (port 3001)   │     │   (port 3003)     │    │   (port 3002)      │
   └────────┬────────┘     └─────────┬─────────┘    └──────────┬─────────┘
            │                        │                         │
            └────────────────────────┼─────────────────────────┘
                                     │
                              ┌──────▼──────┐
                              │   MongoDB   │
                              │ (port 27017)│
                              └─────────────┘
```

## Microservices

| Service | Port | Path | Responsibilities |
|---------|------|------|-----------------|
| **Auth** | 3001 | `/api/auth/*` | User signup, login, JWT authentication |
| **Discounts** | 3002 | `/api/discounts/*` | Coupon and campaign management |
| **Items** | 3003 | `/api/items/*` | Menu items, dietary categories, orders |
| **Frontend** | 3000 | `/` | React SPA (admin dashboard) |

## Quick Start

### 1. Start MongoDB

```bash
docker run -d \
  --name my-mongo \
  -p 27017:27017 \
  -v mongo-data:/data/db \
  mongo:latest
```

### 2. Start each microservice

```bash
# Terminal 1 - Auth
cd backend/auth && npm install && npm start

# Terminal 2 - Discounts
cd backend/discounts && npm install && npm start

# Terminal 3 - Items
cd backend/items && npm install && npm start

# Terminal 4 - Frontend
cd client && npm install && npm start
```

### 3. Start HAProxy

```bash
haproxy -f haproxy.cfg
```

Access the app at **http://localhost/**

## Environment Variables

Each microservice uses the same set of environment variables (see `.env.example` in each service folder):

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET` | JWT signing key | `MySecret1!` |
| `MONGODB_URI` | MongoDB connection string | `mongodb://127.0.0.1:27017/restauranty` |
| `CLOUD_NAME` | Cloudinary cloud name | _(ask instructor)_ |
| `CLOUD_API_KEY` | Cloudinary API key | _(ask instructor)_ |
| `CLOUD_API_SECRET` | Cloudinary API secret | _(ask instructor)_ |
| `PORT` | Service port | `3001` / `3002` / `3003` |

For the frontend, use the `REACT_APP_` prefix: `REACT_APP_API_URL=http://localhost:80`

## Tech Stack

- **Frontend**: React 18, React Router 6, Tailwind CSS, Axios, React Icons
- **Backend**: Express, Mongoose, JWT (jsonwebtoken + express-jwt), bcryptjs
- **Image Storage**: Cloudinary (via multer-storage-cloudinary)
- **Monitoring**: Prometheus metrics (`/metrics` endpoint on each backend service)
- **Routing**: HAProxy (local) / Kubernetes Ingress (production)
- **Database**: MongoDB