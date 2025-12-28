"""
Periodic scheduler for fetching cloud resources and storing snapshots.
Uses APScheduler to run jobs at regular intervals.
"""
import asyncio
import logging
import json
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import AsyncSessionLocal
from app.models.models import Tenant, MetricSnapshot
from app.api.v1.metrics import fetch_aws_resources, fetch_azure_resources, fetch_gcp_resources

logger = logging.getLogger(__name__)

async def fetch_and_store_snapshot(tenant_id: int):
    """Fetch resources for a tenant and store a snapshot in the DB."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
            tenant = result.scalar_one_or_none()
            if not tenant:
                logger.warning(f"Tenant {tenant_id} not found")
                return
            
            meta = tenant.metadata_json or {}
            provider = (meta.get("provider") or "aws").lower()
            
            # Fetch resources based on provider
            if provider == "aws":
                resources = await fetch_aws_resources(tenant_id, meta)
            elif provider == "azure":
                resources = await fetch_azure_resources(tenant_id, meta)
            elif provider == "gcp":
                resources = await fetch_gcp_resources(tenant_id, meta)
            else:
                logger.warning(f"Unknown provider: {provider} for tenant {tenant_id}")
                return
            
            # Build summary
            summary = {}
            for category, items in resources.items():
                if isinstance(items, dict):
                    for resource_type, resources_list in items.items():
                        if isinstance(resources_list, list):
                            key = f"{category}_{resource_type}"
                            summary[key] = len(resources_list)
            
            # Create snapshot payload
            snapshot_data = {
                "client_id": tenant_id,
                "client_name": tenant.name,
                "provider": provider,
                "resources": resources,
                "summary": summary,
                "fetched_at": datetime.utcnow().isoformat()
            }
            
            # Store snapshot in DB
            snapshot = MetricSnapshot(
                tenant_id=tenant_id,
                provider=provider,
                data=snapshot_data
            )
            db.add(snapshot)
            await db.commit()
            logger.info(f"Stored snapshot for tenant {tenant_id} ({tenant.name}) with provider {provider}")
    except Exception as e:
        logger.exception(f"Error storing snapshot for tenant {tenant_id}: {e}")

async def periodic_snapshot_job():
    """Fetch snapshots for all tenants periodically (every 1 hour)."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Tenant))
            tenants = result.scalars().all()
            
            logger.info(f"Starting periodic snapshot job for {len(tenants)} tenants")
            tasks = [fetch_and_store_snapshot(tenant.id) for tenant in tenants]
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("Periodic snapshot job completed")
    except Exception as e:
        logger.exception(f"Error in periodic snapshot job: {e}")

async def start_snapshot_scheduler():
    """Start the background scheduler loop."""
    while True:
        try:
            await periodic_snapshot_job()
        except Exception as e:
            logger.exception(f"Snapshot scheduler loop error: {e}")
        
        # Sleep for 1 hour (3600 seconds) before next run
        await asyncio.sleep(60 * 60)
