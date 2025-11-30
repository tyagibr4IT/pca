from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.db.database import get_db
from app.models.models import Tenant
from app.auth.jwt import get_current_user, require_role
from pydantic import BaseModel, Field
from typing import Optional, List

router = APIRouter(prefix="/clients", tags=["clients"])

class ClientCreate(BaseModel):
    name: str
    metadata_json: Optional[dict] = Field(None, alias="metadata")

    class Config:
        allow_population_by_field_name = True

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    metadata_json: Optional[dict] = Field(None, alias="metadata")

    class Config:
        allow_population_by_field_name = True

class ClientResponse(BaseModel):
    id: int
    name: str
    metadata_json: Optional[dict] = None
    created_at: str

    class Config:
        orm_mode = True

@router.get("/", response_model=List[ClientResponse])
async def list_clients(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """List all clients (tenants)"""
    result = await db.execute(select(Tenant))
    clients = result.scalars().all()
    return [
        ClientResponse(
            id=c.id,
            name=c.name,
            metadata_json=c.metadata_json,
            created_at=c.created_at.isoformat() if c.created_at else ""
        )
        for c in clients
    ]

@router.post("/", response_model=ClientResponse)
async def create_client(payload: ClientCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_role(["admin"]))):
    """Create a new client (tenant)"""
    client = Tenant(name=payload.name, metadata_json=payload.metadata_json)
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return ClientResponse(
        id=client.id,
        name=client.name,
        metadata_json=client.metadata_json,
        created_at=client.created_at.isoformat() if client.created_at else ""
    )

@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(client_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Get a specific client by ID"""
    result = await db.execute(select(Tenant).where(Tenant.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return ClientResponse(
        id=client.id,
        name=client.name,
        metadata_json=client.metadata_json,
        created_at=client.created_at.isoformat() if client.created_at else ""
    )

@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(client_id: int, payload: ClientUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_role(["admin"]))):
    """Update a client"""
    result = await db.execute(select(Tenant).where(Tenant.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if payload.name is not None:
        client.name = payload.name
    if payload.metadata_json is not None:
        client.metadata_json = payload.metadata_json
    
    await db.commit()
    await db.refresh(client)
    return ClientResponse(
        id=client.id,
        name=client.name,
        metadata_json=client.metadata_json,
        created_at=client.created_at.isoformat() if client.created_at else ""
    )

@router.delete("/{client_id}")
async def delete_client(client_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_role(["admin"]))):
    """Delete a client"""
    result = await db.execute(select(Tenant).where(Tenant.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    await db.delete(client)
    await db.commit()
    return {"message": "Client deleted successfully"}

class ConnectionTestResponse(BaseModel):
    ok: bool
    provider: Optional[str] = None
    details: Optional[str] = None

@router.post("/{client_id}/test", response_model=ConnectionTestResponse)
async def test_client_connection(client_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Test connection for a client by validating required credentials.
    This is a lightweight validation (no external API calls)."""
    result = await db.execute(select(Tenant).where(Tenant.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    meta = client.metadata_json or {}
    provider = (meta.get("provider") or "").lower()

    # Basic field validation per provider
    if provider == "aws":
        if meta.get("clientId") and meta.get("clientSecret"):
            return ConnectionTestResponse(ok=True, provider=provider, details="AWS credentials present")
        return ConnectionTestResponse(ok=False, provider=provider, details="Missing clientId/clientSecret for AWS")
    elif provider == "azure":
        if not (meta.get("tenantId") and meta.get("clientId") and meta.get("clientSecret")):
            return ConnectionTestResponse(ok=False, provider=provider, details="Missing tenantId/clientId/clientSecret for Azure")
        # Attempt an actual client credentials token acquisition against Azure AD
        try:
            import msal
        except ImportError:
            return ConnectionTestResponse(ok=False, provider=provider, details="msal not installed on server")

        tenant_id = meta.get("tenantId")
        client_id = meta.get("clientId")
        client_secret = meta.get("clientSecret")
        authority = f"https://login.microsoftonline.com/{tenant_id}"
        # Using Microsoft Graph default scope for client credentials
        app = msal.ConfidentialClientApplication(
            client_id,
            authority=authority,
            client_credential=client_secret,
        )
        # Acquire token for client using .default scope
        result_token = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])  # type: ignore
        if result_token and result_token.get("access_token"):
            return ConnectionTestResponse(ok=True, provider=provider, details="Azure token acquisition succeeded")
        err = result_token.get("error_description") if isinstance(result_token, dict) else "Unknown error"
        return ConnectionTestResponse(ok=False, provider=provider, details=f"Azure token acquisition failed: {err}")
    elif provider == "gcp":
        if meta.get("clientId") and meta.get("clientSecret"):
            return ConnectionTestResponse(ok=True, provider=provider, details="GCP credentials present")
        return ConnectionTestResponse(ok=False, provider=provider, details="Missing clientId/clientSecret for GCP")
    else:
        return ConnectionTestResponse(ok=False, provider=provider, details="Unknown or unset provider")
