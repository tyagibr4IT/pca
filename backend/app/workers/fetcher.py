import asyncio
import logging
from datetime import datetime
from app.services.connectors import collect_all
from app.db.database import AsyncSessionLocal
from app.models.models import MetricSnapshot, CurrentMetric
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

async def run_collector(tenant_config, tenant_id):
    results = await collect_all(tenant_config)
    async with AsyncSessionLocal() as session:  # simple pattern
        for res in results:
            # store current metrics
            for r in res["resources"]:
                cm = CurrentMetric(tenant_id=tenant_id, provider=res["provider"], resource_type=r["resource_type"], resource_id=r["id"], data=r)
                session.add(cm)
            # store a snapshot
            snap = MetricSnapshot(tenant_id=tenant_id, provider=res["provider"], data=res)
            session.add(snap)
        await session.commit()

async def scheduler_loop(get_tenant_configs):
    while True:
        try:
            tenant_configs = get_tenant_configs()
            tasks = []
            for t in tenant_configs:
                tasks.append(run_collector(t["config"], t["tenant_id"]))
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.exception("collector error: %s", e)
        await asyncio.sleep(60 * 5)  # run every 5 minutes