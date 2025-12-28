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
    """Fetch comprehensive AWS resource inventory using boto3"""
    import boto3
    try:
        access_key = credentials.get("clientId") or credentials.get("access_key")
        secret_key = credentials.get("clientSecret") or credentials.get("secret_key")
        region = credentials.get("region") or "us-east-1"
        if not (access_key and secret_key):
            return {
                "compute": {"ec2": [], "asg": [], "lambda": [], "ecs": [], "eks": []},
                "database": {"rds": [], "dynamodb": [], "elasticache": []},
                "storage": {"s3": [], "ebs": []},
                "networking": {"vpc": [], "sg": [], "elb": [], "cloudfront": []},
                "security": {"iam": [], "kms": []},
                "error": "Missing AWS credentials"
            }

        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        ec2 = session.client("ec2")
        rds = session.client("rds")
        s3 = session.client("s3")
        autoscaling = session.client("autoscaling")
        ecs = session.client("ecs")
        eks = session.client("eks")
        lambda_client = session.client("lambda")
        dynamodb = session.client("dynamodb")
        elasticache = session.client("elasticache")
        iam = session.client("iam")
        kms = session.client("kms")
        cloudfront = session.client("cloudfront")

        result = {
            "compute": {"ec2": [], "asg": [], "lambda": [], "ecs": [], "eks": []},
            "database": {"rds": [], "dynamodb": [], "elasticache": []},
            "storage": {"s3": [], "ebs": []},
            "networking": {"vpc": [], "sg": [], "elb": [], "cloudfront": []},
            "security": {"iam": [], "kms": []},
        }

        # EC2 Instances
        try:
            reservations = ec2.describe_instances().get("Reservations", [])
            for res in reservations:
                for inst in res.get("Instances", []):
                    result["compute"]["ec2"].append({
                        "id": inst.get("InstanceId"),
                        "type": inst.get("InstanceType"),
                        "state": inst.get("State", {}).get("Name"),
                        "region": region,
                        "launch_time": inst.get("LaunchTime").isoformat() if inst.get("LaunchTime") else None
                    })
        except Exception as e:
            print(f"Error fetching AWS EC2: {e}")

        # Auto Scaling Groups
        try:
            asgs = autoscaling.describe_auto_scaling_groups().get("AutoScalingGroups", [])
            for asg in asgs:
                result["compute"]["asg"].append({
                    "name": asg.get("AutoScalingGroupName"),
                    "desired_capacity": asg.get("DesiredCapacity"),
                    "current_size": len(asg.get("Instances", [])),
                    "min_size": asg.get("MinSize"),
                    "max_size": asg.get("MaxSize")
                })
        except Exception as e:
            print(f"Error fetching AWS ASG: {e}")

        # Lambda Functions
        try:
            functions = lambda_client.list_functions().get("Functions", [])
            for func in functions:
                result["compute"]["lambda"].append({
                    "name": func.get("FunctionName"),
                    "runtime": func.get("Runtime"),
                    "memory_mb": func.get("MemorySize"),
                    "timeout_s": func.get("Timeout"),
                    "last_modified": func.get("LastModified")
                })
        except Exception as e:
            print(f"Error fetching AWS Lambda: {e}")

        # ECS Clusters
        try:
            clusters = ecs.list_clusters().get("clusterArns", [])
            for cluster_arn in clusters:
                cluster_name = cluster_arn.split("/")[-1]
                services = ecs.list_services(cluster=cluster_name).get("serviceArns", [])
                result["compute"]["ecs"].append({
                    "cluster": cluster_name,
                    "services": len(services)
                })
        except Exception as e:
            print(f"Error fetching AWS ECS: {e}")

        # EKS Clusters
        try:
            clusters = eks.list_clusters().get("clusters", [])
            for cluster in clusters:
                result["compute"]["eks"].append({"cluster": cluster})
        except Exception as e:
            print(f"Error fetching AWS EKS: {e}")

        # RDS Instances
        try:
            dbs = rds.describe_db_instances().get("DBInstances", [])
            for db in dbs:
                result["database"]["rds"].append({
                    "id": db.get("DBInstanceIdentifier"),
                    "engine": db.get("Engine"),
                    "size": db.get("DBInstanceClass"),
                    "storage_gb": db.get("AllocatedStorage"),
                    "region": region,
                    "status": db.get("DBInstanceStatus")
                })
        except Exception as e:
            print(f"Error fetching AWS RDS: {e}")

        # DynamoDB Tables
        try:
            tables = dynamodb.list_tables().get("TableNames", [])
            for table in tables:
                details = dynamodb.describe_table(TableName=table).get("Table", {})
                result["database"]["dynamodb"].append({
                    "name": table,
                    "status": details.get("TableStatus"),
                    "item_count": details.get("ItemCount"),
                    "size_bytes": details.get("TableSizeBytes")
                })
        except Exception as e:
            print(f"Error fetching AWS DynamoDB: {e}")

        # ElastiCache Clusters
        try:
            clusters = elasticache.describe_cache_clusters().get("CacheClusters", [])
            for cluster in clusters:
                result["database"]["elasticache"].append({
                    "id": cluster.get("CacheClusterId"),
                    "engine": cluster.get("Engine"),
                    "node_type": cluster.get("CacheNodeType"),
                    "status": cluster.get("CacheClusterStatus")
                })
        except Exception as e:
            print(f"Error fetching AWS ElastiCache: {e}")

        # S3 Buckets
        try:
            buckets = s3.list_buckets().get("Buckets", [])
            for b in buckets:
                result["storage"]["s3"].append({"bucket": b.get("Name"), "region": region})
        except Exception as e:
            print(f"Error fetching AWS S3: {e}")

        # EBS Volumes
        try:
            volumes = ec2.describe_volumes().get("Volumes", [])
            for vol in volumes:
                attachments = vol.get("Attachments", [])
                result["storage"]["ebs"].append({
                    "id": vol.get("VolumeId"),
                    "size_gb": vol.get("Size"),
                    "type": vol.get("VolumeType"),
                    "state": vol.get("State"),
                    "region": region,
                    "unused": len(attachments) == 0
                })
        except Exception as e:
            print(f"Error fetching AWS EBS: {e}")

        # VPCs
        try:
            vpcs = ec2.describe_vpcs().get("Vpcs", [])
            result["networking"]["vpc"] = [{"id": v.get("VpcId"), "cidr": v.get("CidrBlock")} for v in vpcs]
        except Exception as e:
            print(f"Error fetching AWS VPC: {e}")

        # Security Groups
        try:
            sgs = ec2.describe_security_groups().get("SecurityGroups", [])
            result["networking"]["sg"] = [{"id": sg.get("GroupId"), "name": sg.get("GroupName")} for sg in sgs]
        except Exception as e:
            print(f"Error fetching AWS SGs: {e}")

        # Load Balancers
        try:
            elb = session.client("elb")
            lbs = elb.describe_load_balancers().get("LoadBalancerDescriptions", [])
            result["networking"]["elb"] = [{"name": lb.get("LoadBalancerName"), "dns": lb.get("DNSName")} for lb in lbs]
        except Exception as e:
            print(f"Error fetching AWS ELB: {e}")

        # CloudFront Distributions
        try:
            dist = cloudfront.list_distributions().get("DistributionList", {})
            result["networking"]["cloudfront"] = [
                {"id": d.get("Id"), "domain": d.get("DomainName")} 
                for d in dist.get("Items", [])
            ]
        except Exception as e:
            print(f"Error fetching AWS CloudFront: {e}")

        # IAM Users & Roles
        try:
            users = iam.list_users().get("Users", [])
            roles = iam.list_roles().get("Roles", [])
            result["security"]["iam"] = {
                "users": [{"name": u.get("UserName")} for u in users],
                "roles": [{"name": r.get("RoleName")} for r in roles]
            }
        except Exception as e:
            print(f"Error fetching AWS IAM: {e}")

        # KMS Keys
        try:
            keys = kms.list_keys().get("Keys", [])
            result["security"]["kms"] = [{"key_id": k.get("KeyId")} for k in keys]
        except Exception as e:
            print(f"Error fetching AWS KMS: {e}")

        return result
    except Exception as e:
        print(f"Error in fetch_aws_resources: {e}")
        return {
            "compute": {"ec2": [], "asg": [], "lambda": [], "ecs": [], "eks": []},
            "database": {"rds": [], "dynamodb": [], "elasticache": []},
            "storage": {"s3": [], "ebs": []},
            "networking": {"vpc": [], "sg": [], "elb": [], "cloudfront": []},
            "security": {"iam": [], "kms": []},
            "error": str(e)
        }

async def fetch_azure_resources(client_id: int, credentials: dict):
    """Fetch comprehensive Azure resource inventory using Azure SDK"""
    try:
        # Extract Azure credentials
        tenant_id = credentials.get("tenantId") or credentials.get("tenant_id")
        client_id_azure = credentials.get("clientId") or credentials.get("client_id")
        client_secret = credentials.get("clientSecret") or credentials.get("client_secret")
        subscription_id = credentials.get("subscriptionId") or credentials.get("subscription_id")
        
        if not all([tenant_id, client_id_azure, client_secret, subscription_id]):
            return {
                "compute": {"vm": [], "app_service": [], "aks": []},
                "database": {"sql": [], "cosmos": [], "mysql": []},
                "storage": {"storage_account": [], "blob": []},
                "networking": {"vnet": [], "nsg": [], "lb": []},
                "security": {"key_vault": [], "managed_identity": []},
                "error": "Incomplete Azure credentials"
            }
        
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

        # Import additional clients (optional) and handle missing SDK packages gracefully
        network_client = keyvault_client = aks_client = appservice_client = None
        missing_sdk = []
        try:
            from azure.mgmt.network import NetworkManagementClient
            network_client = NetworkManagementClient(credential, subscription_id)
        except Exception as e:
            missing_sdk.append('azure.mgmt.network')
        try:
            from azure.mgmt.keyvault import KeyVaultManagementClient
            keyvault_client = KeyVaultManagementClient(credential, subscription_id)
        except Exception as e:
            missing_sdk.append('azure.mgmt.keyvault')
        try:
            from azure.mgmt.containerservice import ContainerServiceClient
            aks_client = ContainerServiceClient(credential, subscription_id)
        except Exception as e:
            missing_sdk.append('azure.mgmt.containerservice')
        try:
            from azure.mgmt.web import WebSiteManagementClient
            appservice_client = WebSiteManagementClient(credential, subscription_id)
        except Exception as e:
            missing_sdk.append('azure.mgmt.web')

        result = {
            "compute": {"vm": [], "app_service": [], "aks": []},
            "database": {"sql": [], "cosmos": [], "mysql": []},
            "storage": {"storage_account": [], "blob": []},
            "networking": {"vnet": [], "nsg": [], "lb": []},
            "security": {"key_vault": [], "managed_identity": []},
        }
        errors = []

        # VMs
        try:
            vm_iter = compute_client.virtual_machines.list_all()
            for vm in vm_iter:
                resource_group = vm.id.split('/')[4]
                power_state = "unknown"
                try:
                    instance_view = compute_client.virtual_machines.instance_view(resource_group, vm.name)
                    if instance_view and getattr(instance_view, "statuses", None):
                        for status in instance_view.statuses:
                            if getattr(status, "code", "").startswith('PowerState/'):
                                power_state = status.code.split('/')[-1]
                except Exception as iv_err:
                    print(f"Azure VM instance_view failed for {vm.name}: {iv_err}")

                result["compute"]["vm"].append({
                    "id": vm.name,
                    "size": getattr(vm.hardware_profile, "vm_size", None),
                    "state": power_state,
                    "location": vm.location,
                    "resource_group": resource_group
                })
        except HttpResponseError as e:
            errors.append({"service": "vm", "code": getattr(e, "status_code", "HttpResponseError")})
        except Exception as e:
            print(f"Error fetching Azure VMs: {e}")

        # Storage Accounts
        try:
            storage_iter = storage_client.storage_accounts.list()
            for account in storage_iter:
                result["storage"]["storage_account"].append({
                    "id": account.id,
                    "account": account.name,
                    "location": account.location,
                    "sku": getattr(account.sku, 'name', None),
                    "resource_group": account.id.split('/')[4]
                })
        except Exception as e:
            print(f"Error fetching Azure storage accounts: {e}")

        # Managed Disks (include unattached disks)
        try:
            for disk in compute_client.disks.list():
                result["storage"].setdefault("disks", [])
                managed_by = getattr(disk, "managed_by", None)
                result["storage"]["disks"].append({
                    "id": disk.name,
                    "size_gb": getattr(disk, "disk_size_gb", None) or getattr(disk, "disk_size_gb", None),
                    "location": getattr(disk, "location", None),
                    "managed_by": managed_by,
                    "unused": not bool(managed_by)
                })
        except Exception as e:
            print(f"Error fetching Azure disks: {e}")

        # SQL Servers and Databases
        try:
            sql_servers_iter = sql_client.servers.list()
            for server in sql_servers_iter:
                resource_group = server.id.split('/')[4]
                try:
                    db_list = sql_client.databases.list_by_server(resource_group, server.name)
                    for db in db_list:
                        if db.name != "master":
                            result["database"]["sql"].append({
                                "id": f"{server.name}/{db.name}",
                                "engine": "mssql",
                                "storage_gb": (db.max_size_bytes or 0) / (1024**3),
                                "sku": db.sku.name if db.sku else "unknown",
                                "location": db.location,
                                "resource_group": resource_group
                            })
                except Exception as e:
                    print(f"Error fetching databases for server {server.name}: {e}")
        except Exception as e:
            print(f"Error fetching Azure SQL servers: {e}")

        # Virtual Networks
        try:
            for rg in resource_client.resource_groups.list():
                try:
                    if network_client:
                        vnets = network_client.virtual_networks.list(rg.name)
                        for vnet in vnets:
                            result["networking"]["vnet"].append({
                                "id": vnet.name,
                                "address_space": getattr(vnet.address_space, "address_prefixes", []),
                                "location": vnet.location,
                                "resource_group": rg.name
                            })
                    else:
                        # network SDK missing; skip but record error
                        errors.append({"service": "vnet", "error": "missing azure.mgmt.network"})
                except Exception:
                    pass
        except Exception as e:
            print(f"Error fetching Azure VNets: {e}")

        # Network Security Groups
        try:
            for rg in resource_client.resource_groups.list():
                try:
                    if network_client:
                        nsgs = network_client.network_security_groups.list(rg.name)
                        for nsg in nsgs:
                            result["networking"]["nsg"].append({
                                "id": nsg.name,
                                "location": nsg.location,
                                "resource_group": rg.name
                            })
                    else:
                        errors.append({"service": "nsg", "error": "missing azure.mgmt.network"})
                except Exception as e:
                    pass
        except Exception as e:
            print(f"Error fetching Azure NSGs: {e}")

        # Load Balancers
        try:
            for rg in resource_client.resource_groups.list():
                try:
                    if network_client:
                        lbs = network_client.load_balancers.list(rg.name)
                        for lb in lbs:
                            result["networking"]["lb"].append({
                                "id": lb.name,
                                "location": lb.location,
                                "resource_group": rg.name
                            })
                    else:
                        errors.append({"service": "lb", "error": "missing azure.mgmt.network"})
                except Exception as e:
                    pass
        except Exception as e:
            print(f"Error fetching Azure Load Balancers: {e}")

        # Key Vaults
        try:
            for rg in resource_client.resource_groups.list():
                try:
                    if keyvault_client:
                        vaults = keyvault_client.vaults.list_by_resource_group(rg.name)
                        for vault in vaults:
                            result["security"]["key_vault"].append({
                                "id": vault.name,
                                "location": vault.location,
                                "resource_group": rg.name
                            })
                    else:
                        errors.append({"service": "key_vault", "error": "missing azure.mgmt.keyvault"})
                except Exception as e:
                    pass
        except Exception as e:
            print(f"Error fetching Azure Key Vaults: {e}")

        # AKS Clusters
        try:
            for rg in resource_client.resource_groups.list():
                try:
                    clusters = aks_client.managed_clusters.list_by_resource_group(rg.name)
                    for cluster in clusters:
                        result["compute"]["aks"].append({
                            "id": cluster.name,
                            "location": cluster.location,
                            "resource_group": rg.name,
                            "kubernetes_version": getattr(cluster, "kubernetes_version", None)
                        })
                except Exception as e:
                    pass
        except Exception as e:
            print(f"Error fetching Azure AKS: {e}")

        # App Service Plans & Web Apps
        try:
            for rg in resource_client.resource_groups.list():
                try:
                    webapps = appservice_client.web_apps.list_by_resource_group(rg.name)
                    for app in webapps:
                        result["compute"]["app_service"].append({
                            "id": app.name,
                            "location": app.location,
                            "resource_group": rg.name,
                            "state": getattr(app, "state", None)
                        })
                except Exception as e:
                    pass
        except Exception as e:
            print(f"Error fetching Azure App Services: {e}")

        return result
    
    except Exception as e:
        print(f"Error in fetch_azure_resources: {e}")
        return {
            "compute": {"vm": [], "app_service": [], "aks": []},
            "database": {"sql": [], "cosmos": [], "mysql": []},
            "storage": {"storage_account": [], "blob": []},
            "networking": {"vnet": [], "nsg": [], "lb": []},
            "security": {"key_vault": [], "managed_identity": []},
            "error": str(e)
        }

async def fetch_gcp_resources(client_id: int, credentials: dict):
    """Fetch comprehensive GCP resource inventory using Google Cloud SDK"""
    import json
    import os
    from google.oauth2 import service_account
    from google.cloud import compute_v1, storage
    
    try:
        sa_json = credentials.get("serviceAccountJson")
        sa_path = credentials.get("serviceAccountPath")
        project = credentials.get("projectId") or credentials.get("project")
        if not project:
            return {
                "compute": {"instances": [], "images": []},
                "database": {"cloud_sql": [], "firestore": [], "bigtable": []},
                "storage": {"buckets": []},
                "networking": {"networks": [], "firewalls": []},
                "analytics": {"bigquery": []},
                "messaging": {"pubsub": []},
                "error": "Missing GCP projectId"
            }

        if sa_json:
            info = json.loads(sa_json) if isinstance(sa_json, str) else sa_json
            creds = service_account.Credentials.from_service_account_info(info)
        elif sa_path and os.path.exists(sa_path):
            creds = service_account.Credentials.from_service_account_file(sa_path)
        else:
            creds = None

        # Ensure credentials include cloud-platform scope for REST/API access
        if creds is not None:
            try:
                creds = creds.with_scopes(["https://www.googleapis.com/auth/cloud-platform"])
            except Exception:
                # Some credential types may not support with_scopes; ignore
                pass
        else:
            return {
                "compute": {"instances": [], "images": []},
                "database": {"cloud_sql": [], "firestore": [], "bigtable": []},
                "storage": {"buckets": []},
                "networking": {"networks": [], "firewalls": []},
                "analytics": {"bigquery": []},
                "messaging": {"pubsub": []},
                "error": "Missing GCP service account credentials"
            }

        result = {
            "compute": {"instances": [], "images": []},
            "database": {"cloud_sql": [], "firestore": [], "bigtable": []},
            "storage": {"buckets": []},
            "networking": {"networks": [], "firewalls": []},
            "analytics": {"bigquery": []},
            "messaging": {"pubsub": []},
        }

        # Compute Engine Instances
        try:
            compute_client = compute_v1.InstancesClient(credentials=creds)
            agg_list = compute_client.aggregated_list(project=project)
            for zone, scoped_list in agg_list:
                for inst in scoped_list.instances or []:
                    result["compute"]["instances"].append({
                        "id": inst.name,
                        "type": inst.machine_type.split('/')[-1] if inst.machine_type else None,
                        "state": inst.status,
                        "zone": zone,
                        "cpu_platform": getattr(inst, "cpu_platform", None)
                    })
        except Exception as e:
            print(f"Error fetching GCP Compute instances: {e}")

        # Compute Engine Images
        try:
            images_client = compute_v1.ImagesClient(credentials=creds)
            for img in images_client.list(project=project):
                result["compute"]["images"].append({
                    "name": img.name,
                    "source_disk": getattr(img, "source_disk", None),
                    "status": getattr(img, "status", None)
                })
        except Exception as e:
            print(f"Error fetching GCP Images: {e}")

        # Storage Buckets
        try:
            storage_client = storage.Client(project=project, credentials=creds)
            for b in storage_client.list_buckets(project=project):
                result["storage"]["buckets"].append({
                    "bucket": b.name,
                    "location": getattr(b, "location", None),
                    "storage_class": getattr(b, "storage_class", None)
                })
        except Exception as e:
            print(f"Error fetching GCP Storage buckets: {e}")

        # Persistent disks (include unattached)
        try:
            disks_client = compute_v1.DisksClient(credentials=creds)
            agg_disks = disks_client.aggregated_list(project=project)
            for zone, scoped in agg_disks:
                for d in scoped.disks or []:
                    result["storage"].setdefault("disks", []).append({
                        "id": d.name,
                        "size_gb": getattr(d, "size_gb", None) or getattr(d, "disk_size_gb", None),
                        "zone": zone,
                        "unused": not getattr(d, "users", None)
                    })
        except Exception as e:
            print(f"Error fetching GCP disks: {e}")

        # Cloud SQL Instances (use REST via AuthorizedSession to avoid requiring google-cloud-sql)
        try:
            try:
                from google.auth.transport.requests import AuthorizedSession
                import json as _json
                asess = AuthorizedSession(creds)
                url = f"https://sqladmin.googleapis.com/sql/v1beta4/projects/{project}/instances"
                r = asess.get(url)
                if r.status_code == 200:
                    data = r.json()
                    for inst in data.get("items", []) or []:
                        result["database"]["cloud_sql"].append({
                            "id": inst.get("name"),
                            "engine": inst.get("databaseVersion"),
                            "tier": inst.get("settings", {}).get("tier"),
                            "region": inst.get("region"),
                            "state": inst.get("state"),
                            "storage_gb": inst.get("settings", {}).get("dataDiskSizeGb"),
                        })
                else:
                    print(f"Cloud SQL REST fetch returned {r.status_code}: {r.text}")
            except ImportError:
                # google-auth transport not available; skip Cloud SQL fetch
                pass
            except Exception as e:
                print(f"Error fetching GCP Cloud SQL (REST): {e}")
        except Exception:
            pass

        # BigQuery Datasets
        try:
            try:
                from google.cloud import bigquery
                bq_client = bigquery.Client(project=project, credentials=creds)
                for dataset in bq_client.list_datasets():
                    result["analytics"]["bigquery"].append({
                        "id": getattr(dataset, "dataset_id", None) or (dataset.dataset_id if hasattr(dataset, "dataset_id") else None),
                        "location": getattr(dataset, "location", None),
                        "created": str(getattr(dataset, "created", None)) if getattr(dataset, "created", None) else None
                    })
            except ImportError:
                # google-cloud-bigquery not installed, skip BigQuery fetch
                pass
            except Exception as e:
                print(f"Error fetching GCP BigQuery: {e}")
        except Exception:
            pass

        # Pub/Sub Topics
        try:
            try:
                from google.cloud import pubsub_v1
                publisher = pubsub_v1.PublisherClient(credentials=creds)
                # use explicit project path
                project_path = f"projects/{project}"
                for topic in publisher.list_topics(request={"project": project_path}):
                    name = getattr(topic, "name", None) or (topic.get("name") if isinstance(topic, dict) else None)
                    if name:
                        result["messaging"]["pubsub"].append({
                            "name": name.split('/')[-1],
                            "path": name
                        })
            except ImportError:
                # google-cloud-pubsub not installed, skip Pub/Sub fetch
                pass
            except Exception as e:
                print(f"Error fetching GCP Pub/Sub: {e}")
        except Exception:
            pass

        # VPC Networks
        try:
            networks_client = compute_v1.NetworksClient(credentials=creds)
            for network in networks_client.list(project=project):
                result["networking"]["networks"].append({
                    "id": network.name,
                    "auto_create_subnetworks": network.auto_create_subnetworks,
                    "ipv4_range": getattr(network, "ipv4_range", None)
                })
        except Exception as e:
            print(f"Error fetching GCP Networks: {e}")

        # Firewall Rules
        try:
            firewalls_client = compute_v1.FirewallsClient(credentials=creds)
            for fw in firewalls_client.list(project=project):
                result["networking"]["firewalls"].append({
                    "name": fw.name,
                    "direction": fw.direction,
                    "priority": fw.priority
                })
        except Exception as e:
            print(f"Error fetching GCP Firewalls: {e}")

        return result
    
    except Exception as e:
        print(f"Error in fetch_gcp_resources: {e}")
        return {
            "compute": {"instances": [], "images": []},
            "database": {"cloud_sql": [], "firestore": [], "bigtable": []},
            "storage": {"buckets": []},
            "networking": {"networks": [], "firewalls": []},
            "analytics": {"bigquery": []},
            "messaging": {"pubsub": []},
            "error": str(e)
        }

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
        resources = {
            "compute": {}, "database": {}, "storage": {}, 
            "networking": {}, "security": {}, "analytics": {}, "messaging": {}
        }
    
    # Build summary from nested structure
    summary = {}
    for category, items in resources.items():
        if isinstance(items, dict):
            for resource_type, resources_list in items.items():
                if isinstance(resources_list, list):
                    key = f"{category}_{resource_type}"
                    summary[key] = len(resources_list)
    
    return {
        "client_id": client_id,
        "client_name": client.name,
        "provider": provider,
        "resources": resources,
        "summary": summary
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