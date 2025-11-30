# Cloud Optimizer Backend Setup

## Prerequisites
- Python 3.11+
- Podman or Docker
- Podman-compose (if using Podman)

## Quick Start with Containers (Podman)

### 1. Start all services (Postgres + Redis + Backend)
```powershell
# Using podman-compose
podman-compose up -d

# Or using docker-compose with Podman
podman-compose up --build -d
```

### 2. Run database migrations
```powershell
# Connect to backend container
podman exec -it pca_backend alembic upgrade head
```

### 3. Access services
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Postgres: localhost:5432
- Redis: localhost:6379

## Local Development Setup (without containers)

### 1. Install dependencies
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Start Postgres and Redis
```powershell
# Start Postgres
podman run -d --name pca_postgres `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=postgres `
  -e POSTGRES_DB=pca `
  -p 5432:5432 `
  postgres:15-alpine

# Start Redis
podman run -d --name pca_redis `
  -p 6379:6379 `
  redis:7-alpine
```

### 3. Run migrations
```powershell
cd backend
alembic upgrade head
```

### 4. Start development server
```powershell
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Authentication
- POST `/api/auth/login` - User login
- GET `/api/auth/me` - Get current user

### Clients (Tenants)
- GET `/api/clients/` - List all clients
- POST `/api/clients/` - Create client
- GET `/api/clients/{id}` - Get client by ID
- PUT `/api/clients/{id}` - Update client
- DELETE `/api/clients/{id}` - Delete client

### Users
- GET `/api/users/` - List all users
- POST `/api/users/` - Create user
- GET `/api/users/{id}` - Get user by ID
- PUT `/api/users/{id}` - Update user
- DELETE `/api/users/{id}` - Delete user

### Metrics
- GET `/api/metrics/current` - Get current metrics

### Chat (WebSocket)
- WS `/api/chat/ws/{client_id}` - Real-time chat per client

## Environment Variables

See `.env` file for configuration. Key variables:
- `DATABASE_URL` - Postgres connection string
- `REDIS_URL` - Redis connection string
- `JWT_SECRET` - Secret key for JWT tokens
- `APP_HOST` / `APP_PORT` - Server binding

## Testing
```powershell
pytest app/tests -v
```

## Stopping Services
```powershell
# Stop all containers
podman-compose down

# Stop individual containers
podman stop pca_backend pca_postgres pca_redis
podman rm pca_backend pca_postgres pca_redis
```
