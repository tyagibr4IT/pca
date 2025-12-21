from fastapi import APIRouter, Depends, HTTPException, Query
from app.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.models.models import CurrentMetric, MetricSnapshot, Tenant
from sqlalchemy import select, desc
from app.auth.jwt import get_current_user
from datetime import datetime, timedelta
import asyncio
from azure.identity import ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.sql import SqlManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.core.exceptions import HttpResponseError

router = APIRouter(prefix="/metrics", tags=["metrics"])

@router.get("/current")
async def get_current_metrics(
    client_id: Optional[int] = Query(None, description="Filter by client ID"),
    db: AsyncSession = Depends(get_db), 
    current_user: dict = Depends(get_current_user)
):
    """Get current metrics, optionally filtered by client"""
    query = select(CurrentMetric)
    if client_id:
        query = query.where(CurrentMetric.tenant_id == client_id)
    q = await db.execute(query)
    items = q.scalars().all()
    return {
        "count": len(items), 
        "items": [
            {
                "provider": i.provider, 
                "resource_type": i.resource_type,
                "resource_id": i.resource_id, 
                "data": i.data,
                "updated_at": i.updated_at.isoformat() if i.updated_at else None
            } 
            for i in items
        ]
    }

@router.get("/history")
async def get_metric_history(
    client_id: Optional[int] = Query(None),
    hours: int = Query(24, description="Hours of history to fetch"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get historical metric snapshots"""
    since = datetime.utcnow() - timedelta(hours=hours)
    query = select(MetricSnapshot).where(MetricSnapshot.snapshot_time >= since)
    if client_id:
        query = query.where(MetricSnapshot.tenant_id == client_id)
    query = query.order_by(desc(MetricSnapshot.snapshot_time)).limit(100)
    result = await db.execute(query)
    snapshots = result.scalars().all()
    return {
        "count": len(snapshots),
        "snapshots": [
            {
                "tenant_id": s.tenant_id,
                "provider": s.provider,
                "snapshot_time": s.snapshot_time.isoformat(),
                "data": s.data
            }
            for s in snapshots
        ]
    }

async def fetch_aws_resources(client_id: int, credentials: dict):
    """Fetch AWS resource inventory using boto3"""
    import boto3
    try:
        access_key = credentials.get("clientId") or credentials.get("access_key")
        secret_key = credentials.get("clientSecret") or credentials.get("secret_key")
        region = credentials.get("region") or "us-east-1"
        if not (access_key and secret_key):
            return {"vms": [], "databases": [], "storage": [], "error": "Missing AWS credentials"}

        ec2 = boto3.client("ec2", region_name=region, aws_access_key_id=access_key, aws_secret_access_key=secret_key)
        rds = boto3.client("rds", region_name=region, aws_access_key_id=access_key, aws_secret_access_key=secret_key)
        s3 = boto3.client("s3", region_name=region, aws_access_key_id=access_key, aws_secret_access_key=secret_key)

        vms = []
        try:
            reservations = ec2.describe_instances()["Reservations"]
            for res in reservations:
                for inst in res.get("Instances", []):
                    vms.append({
                        "id": inst.get("InstanceId"),
                        "type": inst.get("InstanceType"),
                        "state": inst.get("State", {}).get("Name"),
                        "region": region
                    })
        except Exception as e:
            print(f"Error fetching AWS EC2: {e}")

        databases = []
        try:
            dbs = rds.describe_db_instances().get("DBInstances", [])
            for db in dbs:
                databases.append({
                    "id": db.get("DBInstanceIdentifier"),
                    "engine": db.get("Engine"),
                    "size": db.get("DBInstanceClass"),
                    "storage_gb": db.get("AllocatedStorage"),
                    "region": region
                })
        except Exception as e:
            print(f"Error fetching AWS RDS: {e}")

        storage = []
        try:
            buckets = s3.list_buckets().get("Buckets", [])
            for b in buckets:
                storage.append({
                    "bucket": b.get("Name"),
                    "region": region
                })
        except Exception as e:
            print(f"Error fetching AWS S3: {e}")

        return {"vms": vms, "databases": databases, "storage": storage}
    except Exception as e:
        print(f"Error in fetch_aws_resources: {e}")
        return {"vms": [], "databases": [], "storage": [], "error": str(e)}

async def fetch_azure_resources(client_id: int, credentials: dict):
    """Fetch Azure resource inventory using Azure SDK"""
    try:
        # Extract Azure credentials
        tenant_id = credentials.get("tenantId") or credentials.get("tenant_id")
        client_id_azure = credentials.get("clientId") or credentials.get("client_id")
        client_secret = credentials.get("clientSecret") or credentials.get("client_secret")
        subscription_id = credentials.get("subscriptionId") or credentials.get("subscription_id")
        resource_group_filter = credentials.get("resourceGroup") or credentials.get("resource_group")
        
        if not all([tenant_id, client_id_azure, client_secret, subscription_id]):
            # Return placeholder if credentials incomplete
            return {
                "vms": [],
                "databases": [],
                "storage": [],
                "error": "Incomplete Azure credentials"
            }
        
        # Create credential object
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id_azure,
            client_secret=client_secret
        )
        
        # Initialize Azure management clients
        compute_client = ComputeManagementClient(credential, subscription_id)
        storage_client = StorageManagementClient(credential, subscription_id)
        sql_client = SqlManagementClient(credential, subscription_id)
        resource_client = ResourceManagementClient(credential, subscription_id)

        # Collect non-fatal errors for diagnostics
        errors = []
        
        # Fetch VMs (tolerate per-VM failures to get instance view)
        vms = []
        try:
            if resource_group_filter:
                vm_iter = compute_client.virtual_machines.list(resource_group_filter)
            else:
                vm_iter = compute_client.virtual_machines.list_all()
            for vm in vm_iter:
                resource_group = vm.id.split('/')[4]
                power_state = "unknown"
                try:
                    instance_view = compute_client.virtual_machines.instance_view(
                        resource_group,
                        vm.name
                    )
                    if instance_view and getattr(instance_view, "statuses", None):
                        for status in instance_view.statuses:
                            if getattr(status, "code", "").startswith('PowerState/'):
                                power_state = status.code.split('/')[-1]
                except HttpResponseError as iv_err:
                    # Proceed without instance view
                    print(f"Azure VM instance_view failed for {vm.name}: {iv_err}")
                except Exception as iv_err:
                    print(f"Azure VM instance_view unexpected error for {vm.name}: {iv_err}")

                vms.append({
                    "id": vm.name,
                    "size": getattr(vm.hardware_profile, "vm_size", None),
                    "state": power_state,
                    "location": vm.location,
                    "resource_group": resource_group
                })
        except HttpResponseError as e:
            print(f"Error fetching Azure VMs (HTTP): {e}")
            errors.append({"service": "compute", "code": getattr(e, "status_code", "HttpResponseError"), "message": str(e)})
        except Exception as e:
            print(f"Error fetching Azure VMs: {e}")
            errors.append({"service": "compute", "code": "Exception", "message": str(e)})
        
        # Fetch Storage Accounts
        storage = []
        try:
            if resource_group_filter:
                storage_iter = storage_client.storage_accounts.list_by_resource_group(resource_group_filter)
            else:
                storage_iter = storage_client.storage_accounts.list()
            for account in storage_iter:
                storage.append({
                    "id": account.id,
                    "account": account.name,
                    "size_gb": 0,
                    "location": account.location,
                    "sku": getattr(account.sku, 'name', None),
                    "resource_group": account.id.split('/')[4]
                })
        except HttpResponseError as e:
            print(f"Error fetching Azure storage (HTTP): {e}")
            errors.append({"service": "storage", "code": getattr(e, "status_code", "HttpResponseError"), "message": str(e)})
        except Exception as e:
            print(f"Error fetching Azure storage: {e}")
            errors.append({"service": "storage", "code": "Exception", "message": str(e)})
        
        # Fetch SQL Databases
        databases = []
        try:
            if resource_group_filter:
                sql_servers_iter = sql_client.servers.list_by_resource_group(resource_group_filter)
            else:
                sql_servers_iter = sql_client.servers.list()
            for server in sql_servers_iter:
                resource_group = server.id.split('/')[4]
                try:
                    db_list = sql_client.databases.list_by_server(resource_group, server.name)
                    for db in db_list:
                        if db.name != "master":
                            databases.append({
                                "id": f"{server.name}/{db.name}",
                                "engine": "mssql",
                                "storage_gb": (db.max_size_bytes or 0) / (1024**3),
                                "sku": db.sku.name if db.sku else "unknown",
                                "location": db.location,
                                "resource_group": resource_group
                            })
                except HttpResponseError as e:
                    print(f"Error fetching databases for server {server.name} (HTTP): {e}")
                    errors.append({"service": "sql_databases", "server": server.name, "code": getattr(e, "status_code", "HttpResponseError"), "message": str(e)})
                except Exception as e:
                    print(f"Error fetching databases for server {server.name}: {e}")
                    errors.append({"service": "sql_databases", "server": server.name, "code": "Exception", "message": str(e)})
        except HttpResponseError as e:
            print(f"Error fetching Azure SQL servers (HTTP): {e}")
            errors.append({"service": "sql_servers", "code": getattr(e, "status_code", "HttpResponseError"), "message": str(e)})
        except Exception as e:
            print(f"Error fetching Azure SQL servers: {e}")
            errors.append({"service": "sql_servers", "code": "Exception", "message": str(e)})
        
        # Diagnostics
        print(f"Azure fetch summary: subscription={subscription_id} rg={resource_group_filter or '*'} vms={len(vms)} storage={len(storage)} dbs={len(databases)}")
        return {
            "vms": vms,
            "databases": databases,
            "storage": storage,
            "diagnostics": {
                "subscriptionId": subscription_id,
                "resourceGroup": resource_group_filter,
                "vm_count": len(vms),
                "storage_count": len(storage),
                "database_count": len(databases),
                "errors": errors
            }
        }
    
    except Exception as e:
        print(f"Error in fetch_azure_resources: {e}")
        return {
            "vms": [],
            "databases": [],
            "storage": [],
            "error": str(e)
        }

async def fetch_gcp_resources(client_id: int, credentials: dict):
    """Fetch GCP resource inventory using Google Cloud SDK"""
    # Expect service account JSON content in credentials.serviceAccountJson or path in credentials.serviceAccountPath
    import json
    import os
    from google.oauth2 import service_account
    from google.cloud import compute_v1, storage
    try:
        sa_json = credentials.get("serviceAccountJson")
        sa_path = credentials.get("serviceAccountPath")
        project = credentials.get("projectId") or credentials.get("project")
        if not project:
            return {"vms": [], "databases": [], "storage": [], "error": "Missing GCP projectId"}

        if sa_json:
            info = json.loads(sa_json) if isinstance(sa_json, str) else sa_json
            creds = service_account.Credentials.from_service_account_info(info)
        elif sa_path and os.path.exists(sa_path):
            creds = service_account.Credentials.from_service_account_file(sa_path)
        else:
            return {"vms": [], "databases": [], "storage": [], "error": "Missing GCP service account credentials"}

        # Compute Engine instances
        vms = []
        try:
            compute_client = compute_v1.InstancesClient(credentials=creds)
            agg_list = compute_client.aggregated_list(project=project)
            for zone, scoped_list in agg_list:
                for inst in scoped_list.instances or []:
                    vms.append({
                        "id": inst.name,
                        "type": inst.machine_type.split('/')[-1] if inst.machine_type else None,
                        "state": inst.status,
                        "zone": zone
                    })
        except Exception as e:
            print(f"Error fetching GCP Compute instances: {e}")

        # Storage buckets
        storage_items = []
        try:
            storage_client = storage.Client(project=project, credentials=creds)
            for b in storage_client.list_buckets(project=project):
                storage_items.append({
                    "bucket": b.name,
                    "location": getattr(b, "location", None)
                })
        except Exception as e:
            print(f"Error fetching GCP Storage buckets: {e}")

        # Cloud SQL instances
        databases = []
        try:
            # Prefer built-in sqladmin client if available; fall back to discovery
            try:
                from google.cloud import sql_v1
                sql_client = sql_v1.SqlInstancesServiceClient(credentials=creds)
                request = sql_v1.SqlInstancesListRequest(project=project)
                resp = sql_client.list(request=request)
                instances = getattr(resp, "items", []) or []
            except ImportError:
                from googleapiclient.discovery import build  # type: ignore
                sql_client = build("sqladmin", "v1beta4", credentials=creds, cache_discovery=False)
                req = sql_client.instances().list(project=project)
                resp = req.execute()
                instances = resp.get("items", []) if resp else []

            for inst in instances:
                databases.append({
                    "id": inst.get("name"),
                    "engine": inst.get("databaseVersion"),
                    "tier": inst.get("settings", {}).get("tier"),
                    "region": inst.get("region"),
                    "state": inst.get("state"),
                    "storage_gb": inst.get("settings", {}).get("dataDiskSizeGb"),
                })
        except Exception as e:
            print(f"Error fetching GCP Cloud SQL: {e}")

        return {"vms": vms, "databases": databases, "storage": storage_items}
    except Exception as e:
        print(f"Error in fetch_gcp_resources: {e}")
        return {"vms": [], "databases": [], "storage": [], "error": str(e)}

@router.get("/resources/{client_id}")
async def get_resource_inventory(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Fetch real-time resource inventory from cloud provider"""
    # Get client credentials
    result = await db.execute(select(Tenant).where(Tenant.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    meta = client.metadata_json or {}
    provider = (meta.get("provider") or "aws").lower()
    
    # Fetch resources based on provider
    if provider == "aws":
        resources = await fetch_aws_resources(client_id, meta)
    elif provider == "azure":
        resources = await fetch_azure_resources(client_id, meta)
    elif provider == "gcp":
        resources = await fetch_gcp_resources(client_id, meta)
    else:
        resources = {"vms": [], "databases": [], "storage": []}
    
    return {
        "client_id": client_id,
        "client_name": client.name,
        "provider": provider,
        "resources": resources,
        "summary": {
            "total_vms": len(resources.get("vms", [])),
            "total_databases": len(resources.get("databases", [])),
            "total_storage_buckets": len(resources.get("storage", []))
        }
    }

@router.get("/costs/{client_id}")
async def get_cost_analysis(
    client_id: int,
    days: int = Query(30, description="Days to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Calculate estimated costs for client resources"""
    result = await db.execute(select(Tenant).where(Tenant.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    meta = client.metadata_json or {}
    provider = (meta.get("provider") or "aws").lower()
    
    # Placeholder cost estimates (TODO: integrate actual cloud billing APIs)
    if provider == "aws":
        costs = {
            "compute": 245.50,
            "storage": 89.20,
            "network": 34.10,
            "database": 125.00,
            "total": 493.80
        }
    elif provider == "azure":
        costs = {
            "compute": 189.00,
            "storage": 67.50,
            "network": 28.30,
            "database": 0,
            "total": 284.80
        }
    else:
        costs = {"total": 0}
    
    return {
        "client_id": client_id,
        "client_name": client.name,
        "provider": provider,
        "period_days": days,
        "costs_usd": costs,
        "projected_monthly": round(costs.get("total", 0) * (30 / days), 2)
    }

@router.get("/recommendations/{client_id}")
async def get_optimization_recommendations(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Generate cost optimization and performance recommendations"""
    result = await db.execute(select(Tenant).where(Tenant.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Placeholder recommendations (TODO: implement ML-based analysis)
    recommendations = [
        {
            "type": "cost_savings",
            "severity": "high",
            "title": "Underutilized EC2 Instances",
            "description": "2 instances running at <10% CPU for past 7 days",
            "estimated_savings_monthly": 85.00,
            "action": "Consider downsizing to t3.small or terminating"
        },
        {
            "type": "performance",
            "severity": "medium",
            "title": "High Memory Usage on VM",
            "description": "Instance i-abc123 consistently at 95% memory",
            "estimated_savings_monthly": 0,
            "action": "Upgrade to larger instance type"
        },
        {
            "type": "cost_savings",
            "severity": "low",
            "title": "Unused Storage Volumes",
            "description": "3 EBS volumes detached for >30 days",
            "estimated_savings_monthly": 12.50,
            "action": "Review and delete unused volumes"
        }
    ]
    
    total_potential_savings = sum(r["estimated_savings_monthly"] for r in recommendations if r["type"] == "cost_savings")
    
    return {
        "client_id": client_id,
        "client_name": client.name,
        "recommendations": recommendations,
        "summary": {
            "total_recommendations": len(recommendations),
            "high_severity": sum(1 for r in recommendations if r["severity"] == "high"),
            "total_potential_savings_monthly": total_potential_savings
        }
    }