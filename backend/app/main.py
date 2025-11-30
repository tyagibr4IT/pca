import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import auth as auth_routes, metrics as metrics_routes, clients as clients_routes, users as users_routes, chat as chat_routes
from app.config import settings
from app.workers import fetcher
import asyncio
from app.db.run_migrations import run_migrations
from app.middleware.jwt_middleware import JWTAuthMiddleware

app = FastAPI(title="Cloud Optimizer API")

# Global JWT authentication middleware - MUST be added before CORS
app.add_middleware(JWTAuthMiddleware)

# CORS configuration for frontend - MUST be after JWT middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

if __name__ == "__main__":
    uvicorn.run(app, host=settings.APP_HOST, port=int(settings.APP_PORT))