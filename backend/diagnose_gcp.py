import asyncio, json
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.models.models import Tenant
from app.api.v1.metrics import fetch_gcp_resources

async def main():
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Tenant).where(Tenant.id==13))
        t = res.scalar_one_or_none()
        if not t:
            print('tenant not found')
            return
        meta = t.metadata_json or {}
        print('tenant metadata projectId:', meta.get('projectId') or meta.get('project') or meta.get('projectId'))
        r = await fetch_gcp_resources(13, meta)
        print(json.dumps(r, indent=2))

if __name__ == '__main__':
    asyncio.run(main())
