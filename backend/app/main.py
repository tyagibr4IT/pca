import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import auth as auth_routes, metrics as metrics_routes, clients as clients_routes, users as users_routes, chat as chat_routes
from app.config import settings
from app.workers import fetcher
from app.workers.snapshot_scheduler import start_snapshot_scheduler
import asyncio
from app.db.run_migrations import run_migrations
from app.middleware.jwt_middleware import JWTAuthMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Cloud Optimizer API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Global JWT authentication middleware - MUST be added before CORS
app.add_middleware(JWTAuthMiddleware)

# CORS configuration for frontend - MUST be after JWT middleware
# Security: Restrict to known origins in production
allowed_origins = [
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]
if settings.ENV == "development":
    allowed_origins.append("*")  # Allow all in dev only

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    # Strict-Transport-Security: Force HTTPS in production
    if settings.ENV != "development":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    # Content-Security-Policy: Prevent XSS and injection attacks
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    # X-Frame-Options: Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    # X-Content-Type-Options: Prevent MIME sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Referrer-Policy: Control referrer information
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Permissions-Policy: Restrict browser features
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response

app.include_router(auth_routes.router, prefix="/api")
app.include_router(metrics_routes.router, prefix="/api")
app.include_router(clients_routes.router, prefix="/api")
app.include_router(users_routes.router, prefix="/api")
app.include_router(chat_routes.router, prefix="/api")

# Example in-app scheduler start for dev
@app.on_event("startup")
async def startup_event():
    # Run minimal SQL migrations (safe idempotent scripts)
    await run_migrations()
    # For demo: use a static get_tenant_configs; in prod, query DB
    def get_tenant_configs():
        return [{"tenant_id":1,"config":{"aws":True,"azure":True,"gcp":True}}]
    loop = asyncio.get_event_loop()
    loop.create_task(fetcher.scheduler_loop(get_tenant_configs))
    # Start periodic snapshot scheduler (every 1 hour)
    loop.create_task(start_snapshot_scheduler())

if __name__ == "__main__":
    uvicorn.run(app, host=settings.APP_HOST, port=int(settings.APP_PORT))