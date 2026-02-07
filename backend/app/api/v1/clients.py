from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.db.database import get_db
from app.models.models import Tenant, User, UserClientPermission
from app.auth.jwt import get_current_user
from app.auth.rbac import require_permission
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
    """
    List clients based on user role and assignments.
    - superadmin: sees all clients
    - admin/member: sees only assigned clients
    """
    from sqlalchemy.orm import selectinload
    
    # Get current user with role information
    user_result = await db.execute(
        select(User)
        .options(selectinload(User.role_obj))
        .where(User.id == current_user["user_id"])
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Superadmin sees all clients
    if user.role_obj and user.role_obj.name == "superadmin":
        result = await db.execute(select(Tenant))
        clients = result.scalars().all()
    else:
        # Admin/member users see only their assigned clients
        result = await db.execute(
            select(Tenant)
            .join(UserClientPermission, UserClientPermission.client_id == Tenant.id)
            .where(UserClientPermission.user_id == current_user["user_id"])
        )
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
async def create_client(payload: ClientCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_permission("clients.create"))):
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
async def update_client(client_id: int, payload: ClientUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_permission("clients.edit"))):
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
async def delete_client(client_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_permission("clients.delete"))):
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
        tenant_id = meta.get("tenantId")
        client_id = meta.get("clientId")
        client_secret = meta.get("clientSecret")
        subscription_id = meta.get("subscriptionId")
        resource_group = meta.get("resourceGroup")
        
        if not (tenant_id and client_id and client_secret and subscription_id):
            return ConnectionTestResponse(ok=False, provider=provider, details="Missing tenantId/clientId/clientSecret/subscriptionId for Azure")
        
        # Attempt token acquisition and optional resource group validation
        try:
            import msal
            from azure.identity import ClientSecretCredential
            from azure.mgmt.resource import ResourceManagementClient
            from azure.core.exceptions import HttpResponseError
        except ImportError as e:
            return ConnectionTestResponse(ok=False, provider=provider, details=f"Azure SDK not installed: {e}")

        authority = f"https://login.microsoftonline.com/{tenant_id}"
        # First, verify MSAL token acquisition
        app = msal.ConfidentialClientApplication(
            client_id,
            authority=authority,
            client_credential=client_secret,
        )
        result_token = app.acquire_token_for_client(scopes=["https://management.azure.com/.default"])  # type: ignore
        if not result_token or not result_token.get("access_token"):
            err = result_token.get("error_description") if isinstance(result_token, dict) else "Unknown error"
            return ConnectionTestResponse(ok=False, provider=provider, details=f"Azure token acquisition failed: {err}")
        
        # Verify subscription access
        try:
            credential = ClientSecretCredential(tenant_id, client_id, client_secret)
            resource_client = ResourceManagementClient(credential, subscription_id)
            # Try to get subscription to confirm access
            sub = resource_client.subscriptions.get(subscription_id)
            details = f"Azure validated: subscription {sub.display_name}"
            
            # If resource group provided, verify it exists
            if resource_group:
                try:
                    rg = resource_client.resource_groups.get(resource_group)
                    details += f", resource group {rg.name} found"
                except HttpResponseError:
                    return ConnectionTestResponse(ok=False, provider=provider, details=f"Resource group '{resource_group}' not found in subscription")
            
            return ConnectionTestResponse(ok=True, provider=provider, details=details)
        except HttpResponseError as e:
            return ConnectionTestResponse(ok=False, provider=provider, details=f"Azure subscription/RG check failed: {e.message}")
        except Exception as e:
            return ConnectionTestResponse(ok=False, provider=provider, details=f"Azure validation error: {str(e)}")
    elif provider == "gcp":
        # GCP can either have serviceAccountJson or clientId/clientSecret
        service_account_json = meta.get("serviceAccountJson")
        project_id = meta.get("projectId")
        
        if service_account_json:
            # Validate service account JSON
            try:
                import json
                from google.oauth2 import service_account
                
                if isinstance(service_account_json, str):
                    sa_data = json.loads(service_account_json)
                else:
                    sa_data = service_account_json
                
                # Verify required fields
                required_fields = ["type", "project_id", "private_key", "client_email"]
                if not all(f in sa_data for f in required_fields):
                    return ConnectionTestResponse(ok=False, provider=provider, details="Invalid GCP service account JSON: missing required fields")
                
                # Try to create credentials to validate the key
                credentials = service_account.Credentials.from_service_account_info(sa_data)
                return ConnectionTestResponse(ok=True, provider=provider, details=f"GCP service account validated: {sa_data.get('client_email')}")
            except json.JSONDecodeError:
                return ConnectionTestResponse(ok=False, provider=provider, details="Invalid GCP service account JSON format")
            except Exception as e:
                return ConnectionTestResponse(ok=False, provider=provider, details=f"GCP validation error: {str(e)}")
        elif meta.get("clientId") and meta.get("clientSecret"):
            return ConnectionTestResponse(ok=True, provider=provider, details="GCP credentials present")
        else:
            return ConnectionTestResponse(ok=False, provider=provider, details="Missing GCP serviceAccountJson or clientId/clientSecret")
    else:
        return ConnectionTestResponse(ok=False, provider=provider, details="Unknown or unset provider")
