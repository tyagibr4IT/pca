from fastapi import APIRouter, Depends
from app.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.models.models import CurrentMetric
from sqlalchemy import select
from app.auth.jwt import get_current_user

router = APIRouter(prefix="/metrics", tags=["metrics"])

@router.get("/current")
async def get_current_metrics(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    q = await db.execute(select(CurrentMetric))
    items = q.scalars().all()
    return {"count": len(items), "items": [ {"provider":i.provider, "resource": i.resource_id, "data":i.data} for i in items]}