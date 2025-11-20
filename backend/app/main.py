import uvicorn
from fastapi import FastAPI
from app.api.v1 import auth as auth_routes, metrics as metrics_routes
from app.config import settings
from app.workers import fetcher
import asyncio

app = FastAPI(title="Cloud Optimizer API")

app.include_router(auth_routes.router, prefix="/api")
app.include_router(metrics_routes.router, prefix="/api")

# Example in-app scheduler start for dev
@app.on_event("startup")
async def startup_event():
    # For demo: use a static get_tenant_configs; in prod, query DB
    def get_tenant_configs():
        return [{"tenant_id":1,"config":{"aws":True,"azure":True,"gcp":True}}]
    loop = asyncio.get_event_loop()
    loop.create_task(fetcher.scheduler_loop(get_tenant_configs))

if __name__ == "__main__":
    uvicorn.run(app, host=settings.APP_HOST, port=int(settings.APP_PORT))