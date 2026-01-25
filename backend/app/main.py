"""
FastAPI application initialization and middleware configuration.

This is the main entry point for the Cloud Optimizer API. It configures:
- FastAPI application with OpenAPI documentation
- CORS middleware for frontend communication
- JWT authentication middleware (global)
- Security headers middleware
- Rate limiting for API endpoints
- API route registration
- Background workers (snapshot scheduler)

Middleware Order (CRITICAL):
1. JWT Authentication (validates all requests except /auth/*)
2. CORS (allows frontend cross-origin requests)
3. Security Headers (adds HTTP security headers)
4. Rate Limiting (prevents abuse)

Security Features:
- Global JWT authentication on all endpoints
- CORS restricted to known origins (production)
- Strict-Transport-Security (HSTS) header in production
- Content-Security-Policy (CSP) to prevent XSS
- X-Frame-Options to prevent clickjacking
- X-Content-Type-Options to prevent MIME sniffing

Configuration:
    Environment variables control behavior (see app.config)
    
Startup:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

Author: Cloud Optimizer Team
Version: 2.0.0
Last Modified: 2026-01-25
"""

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

# Initialize rate limiter (keyed by client IP address)
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI application instance
app = FastAPI(title="Cloud Optimizer API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CRITICAL: JWT authentication middleware MUST be added before CORS
# This ensures authentication runs first on all requests
app.add_middleware(JWTAuthMiddleware)

# CORS configuration for frontend communication
# Security: Restrict to known origins in production (never use "*" in prod)
allowed_origins = [
    "http://localhost:3001",  # Local frontend development
    "http://127.0.0.1:3001",  # Alternative localhost
]
# In development, allow all origins for testing (INSECURE, dev only)
if settings.ENV == "development":
    allowed_origins.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers middleware - adds HTTP security headers to all responses
@app.middleware("http")
async def add_security_headers(request, call_next):
    """
    Add security-focused HTTP headers to all API responses.
    
    This middleware enforces security best practices by adding headers that
    protect against common web vulnerabilities:
    
    Headers Added:
        1. Strict-Transport-Security (HSTS):
           - Forces HTTPS connections (production only)
           - Prevents SSL stripping attacks
           - Valid for 1 year (31536000 seconds)
           
        2. Content-Security-Policy (CSP):
           - Prevents XSS (Cross-Site Scripting) attacks
           - Restricts resource loading to same origin
           - Allows inline scripts/styles (can be tightened)
           
        3. X-Frame-Options:
           - Prevents clickjacking attacks
           - DENY = page cannot be embedded in frames
           
        4. X-Content-Type-Options:
           - Prevents MIME type sniffing
           - Forces browser to respect Content-Type header
           
        5. Referrer-Policy:
           - Controls referrer information leakage
           - Balances privacy and functionality
           
        6. Permissions-Policy:
           - Restricts browser features (geolocation, camera, etc.)
           - Prevents unauthorized feature access
    
    Args:
        request: FastAPI Request object
        call_next: Next middleware/endpoint in chain
    
    Returns:
        Response: Original response with added security headers
    
    Production Recommendations:
        - Enable HSTS preloading: add "preload" directive
        - Tighten CSP: remove 'unsafe-inline' when possible
        - Add Subresource Integrity (SRI) for external scripts
        - Consider using security scanner (e.g., OWASP ZAP)
    """
    response = await call_next(request)
    
    # HSTS: Force HTTPS in production (prevents SSL stripping)
    if settings.ENV != "development":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # CSP: Prevent XSS and injection attacks
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    
    # X-Frame-Options: Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    
    # X-Content-Type-Options: Prevent MIME sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # Referrer-Policy: Control referrer information leakage
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