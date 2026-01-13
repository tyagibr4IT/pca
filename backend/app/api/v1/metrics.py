from fastapi import APIRouter, Depends, HTTPException, Query
from app.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.models.models import CurrentMetric, MetricSnapshot, Tenant
from sqlalchemy import select, desc
from app.auth.jwt import get_current_user
from datetime import datetime, timedelta
import asyncio
from botocore.config import Config
from botocore.exceptions import ClientError
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
                "networking": {"vpc": [], "sg": [], "elb": [], "cloudfront": [], "route53": []},
                "security": {"iam": [], "kms": []},
                "messaging": {"sns": [], "sqs": []},
                "api": {"api_gateway": []},
                "error": "Missing AWS credentials"
            }

        # Configure boto3 with aggressive timeouts to prevent hanging
        config = Config(
            connect_timeout=3,
            read_timeout=5,
            retries={'max_attempts': 1, 'mode': 'standard'}
        )

        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        ec2 = session.client("ec2", config=config)
        rds = session.client("rds", config=config)
        s3 = session.client("s3", config=config)
        autoscaling = session.client("autoscaling", config=config)
        ecs = session.client("ecs", config=config)
        eks = session.client("eks", config=config)
        lambda_client = session.client("lambda", config=config)
        dynamodb = session.client("dynamodb", config=config)
        elasticache = session.client("elasticache", config=config)
        iam = session.client("iam", config=config)
        kms = session.client("kms", config=config)
        cloudfront = session.client("cloudfront", config=config)
        route53 = session.client("route53", config=config)
        apigateway = session.client("apigateway", config=config)
        sns = session.client("sns", config=config)
        sqs = session.client("sqs", config=config)

        result = {
            "compute": {"ec2": [], "asg": [], "lambda": [], "ecs": [], "eks": []},
            "database": {"rds": [], "dynamodb": [], "elasticache": []},
            "storage": {"s3": [], "ebs": []},
            "networking": {"vpc": [], "sg": [], "elb": [], "cloudfront": [], "route53": []},
            "security": {"iam": [], "kms": []},
            "messaging": {"sns": [], "sqs": []},
            "api": {"api_gateway": []},
        }

        # EC2 Instances
        try:
            reservations = ec2.describe_instances().get("Reservations", [])
            for res in reservations:
                for inst in res.get("Instances", []):
                    # Extract OS platform information
                    platform = inst.get("Platform", "Linux/Unix")  # Default to Linux if not specified
                    platform_details = inst.get("PlatformDetails", "")
                    
                    # Get image info for more OS details
                    image_id = inst.get("ImageId")
                    os_info = platform_details if platform_details else platform
                    
                    result["compute"]["ec2"].append({
                        "id": inst.get("InstanceId"),
                        "type": inst.get("InstanceType"),
                        "state": inst.get("State", {}).get("Name"),
                        "os_type": os_info,
                        "platform": platform,
                        "image_id": image_id,
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
                {"id": d.get("Id"), "domain": d.get("DomainName"), "status": d.get("Status")} 
                for d in dist.get("Items", [])
            ]
        except Exception as e:
            print(f"Error fetching AWS CloudFront: {e}")

        # Route53 Hosted Zones
        try:
            zones = route53.list_hosted_zones().get("HostedZones", [])
            for zone in zones:
                result["networking"]["route53"].append({
                    "id": zone.get("Id"),
                    "name": zone.get("Name"),
                    "record_count": zone.get("ResourceRecordSetCount"),
                    "private": zone.get("Config", {}).get("PrivateZone", False)
                })
        except Exception as e:
            print(f"Error fetching AWS Route53: {e}")

        # API Gateway REST APIs
        try:
            apis = apigateway.get_rest_apis().get("items", [])
            for api in apis:
                result["api"]["api_gateway"].append({
                    "id": api.get("id"),
                    "name": api.get("name"),
                    "endpoint": api.get("endpointConfiguration", {}).get("types", [])[0] if api.get("endpointConfiguration", {}).get("types") else "N/A",
                    "created": api.get("createdDate")
                })
        except Exception as e:
            print(f"Error fetching AWS API Gateway: {e}")

        # SNS Topics
        try:
            topics = sns.list_topics().get("Topics", [])
            for topic in topics:
                arn = topic.get("TopicArn")
                attrs = sns.get_topic_attributes(TopicArn=arn).get("Attributes", {})
                result["messaging"]["sns"].append({
                    "name": arn.split(":")[-1],
                    "arn": arn,
                    "subscriptions": attrs.get("SubscriptionsConfirmed", "0")
                })
        except Exception as e:
            print(f"Error fetching AWS SNS: {e}")

        # SQS Queues
        try:
            queues = sqs.list_queues().get("QueueUrls", [])
            for queue_url in queues:
                attrs = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["All"]).get("Attributes", {})
                result["messaging"]["sqs"].append({
                    "name": queue_url.split("/")[-1],
                    "url": queue_url,
                    "messages": attrs.get("ApproximateNumberOfMessages", "0")
                })
        except Exception as e:
            print(f"Error fetching AWS SQS: {e}")

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

                # Extract OS information
                os_type = None
                os_version = None
                computer_name = None
                if vm.storage_profile:
                    if vm.storage_profile.os_disk:
                        os_type = getattr(vm.storage_profile.os_disk, 'os_type', None)
                    if vm.storage_profile.image_reference:
                        img_ref = vm.storage_profile.image_reference
                        publisher = getattr(img_ref, 'publisher', '')
                        offer = getattr(img_ref, 'offer', '')
                        sku = getattr(img_ref, 'sku', '')
                        if publisher or offer or sku:
                            os_version = f"{publisher} {offer} {sku}".strip()
                if vm.os_profile:
                    computer_name = getattr(vm.os_profile, 'computer_name', None)

                result["compute"]["vm"].append({
                    "id": vm.name,
                    "size": getattr(vm.hardware_profile, "vm_size", None),
                    "state": power_state,
                    "os_type": os_type,
                    "os_version": os_version,
                    "computer_name": computer_name,
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
                    # Extract OS information from disks
                    os_type = None
                    os_version = None
                    if hasattr(inst, 'disks') and inst.disks:
                        for disk in inst.disks:
                            if disk.boot:
                                # Try to extract OS from source image
                                if hasattr(disk, 'initialize_params') and disk.initialize_params:
                                    source_image = getattr(disk.initialize_params, 'source_image', '')
                                    if source_image:
                                        # Parse image name for OS info (e.g., "ubuntu-2004-lts", "centos-7")
                                        image_parts = source_image.split('/')
                                        if image_parts:
                                            image_name = image_parts[-1]
                                            os_version = image_name
                                            if 'ubuntu' in image_name.lower():
                                                os_type = 'Linux (Ubuntu)'
                                            elif 'centos' in image_name.lower():
                                                os_type = 'Linux (CentOS)'
                                            elif 'debian' in image_name.lower():
                                                os_type = 'Linux (Debian)'
                                            elif 'rhel' in image_name.lower():
                                                os_type = 'Linux (RHEL)'
                                            elif 'windows' in image_name.lower():
                                                os_type = 'Windows'
                                break
                    
                    result["compute"]["instances"].append({
                        "id": inst.name,
                        "type": inst.machine_type.split('/')[-1] if inst.machine_type else None,
                        "state": inst.status,
                        "zone": zone,
                        "os_type": os_type,
                        "os_version": os_version,
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

@router.get("/resource-details/{client_id}/{resource_type}/{resource_id}")
async def get_resource_details(
    client_id: int,
    resource_type: str,
    resource_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Fetch comprehensive details for a specific resource"""
    result = await db.execute(select(Tenant).where(Tenant.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    meta = client.metadata_json or {}
    provider = (meta.get("provider") or "aws").lower()
    
    # Fetch detailed resource information based on provider
    if provider == "aws":
        details = await fetch_aws_resource_details(meta, resource_type, resource_id)
    elif provider == "azure":
        details = await fetch_azure_resource_details(meta, resource_type, resource_id)
    elif provider == "gcp":
        details = await fetch_gcp_resource_details(meta, resource_type, resource_id)
    else:
        details = {"error": "Unknown provider"}
    
    return {
        "client_id": client_id,
        "provider": provider,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details
    }

async def fetch_aws_resource_details(credentials: dict, resource_type: str, resource_id: str):
    """Fetch comprehensive AWS resource details"""
    import boto3
    try:
        access_key = credentials.get("clientId") or credentials.get("access_key")
        secret_key = credentials.get("clientSecret") or credentials.get("secret_key")
        region = credentials.get("region") or "us-east-1"
        
        if not (access_key and secret_key):
            return {"error": "Missing AWS credentials"}
        
        config = Config(connect_timeout=5, read_timeout=10, retries={'max_attempts': 2})
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        
        details = {}
        
        # EC2 Instance Details
        if "ec2" in resource_type.lower() or "instance" in resource_type.lower():
            ec2 = session.client("ec2", config=config)
            try:
                response = ec2.describe_instances(InstanceIds=[resource_id])
                if response.get("Reservations"):
                    instance = response["Reservations"][0]["Instances"][0]
                    details["instance"] = instance
                    
                    # Get security groups
                    sg_ids = [sg["GroupId"] for sg in instance.get("SecurityGroups", [])]
                    if sg_ids:
                        sg_response = ec2.describe_security_groups(GroupIds=sg_ids)
                        details["security_groups"] = sg_response.get("SecurityGroups", [])
                    
                    # Get volumes
                    volume_ids = [
                        mapping["Ebs"]["VolumeId"] 
                        for mapping in instance.get("BlockDeviceMappings", []) 
                        if "Ebs" in mapping
                    ]
                    if volume_ids:
                        vol_response = ec2.describe_volumes(VolumeIds=volume_ids)
                        details["volumes"] = vol_response.get("Volumes", [])
                    
                    # Get network interfaces
                    details["network_interfaces"] = instance.get("NetworkInterfaces", [])
                    
                    # Get tags
                    details["tags"] = instance.get("Tags", [])
                    
                    # Get monitoring state
                    details["monitoring"] = instance.get("Monitoring", {})
                    
            except ClientError as e:
                details["error"] = str(e)
        
        # RDS Database Details
        elif "rds" in resource_type.lower():
            rds = session.client("rds", config=config)
            try:
                response = rds.describe_db_instances(DBInstanceIdentifier=resource_id)
                if response.get("DBInstances"):
                    db_instance = response["DBInstances"][0]
                    details["database"] = db_instance
                    
                    # Get snapshots
                    snap_response = rds.describe_db_snapshots(DBInstanceIdentifier=resource_id, MaxRecords=20)
                    details["snapshots"] = snap_response.get("DBSnapshots", [])
                    
                    # Get parameter groups
                    details["parameter_groups"] = db_instance.get("DBParameterGroups", [])
                    
                    # Get security groups
                    details["vpc_security_groups"] = db_instance.get("VpcSecurityGroups", [])
                    
            except ClientError as e:
                details["error"] = str(e)
        
        # S3 Bucket Details
        elif "s3" in resource_type.lower():
            s3 = session.client("s3", config=config)
            try:
                # Get bucket location
                location = s3.get_bucket_location(Bucket=resource_id)
                details["location"] = location.get("LocationConstraint", "us-east-1")
                
                # Get versioning
                versioning = s3.get_bucket_versioning(Bucket=resource_id)
                details["versioning"] = versioning.get("Status", "Disabled")
                
                # Get encryption
                try:
                    encryption = s3.get_bucket_encryption(Bucket=resource_id)
                    details["encryption"] = encryption.get("ServerSideEncryptionConfiguration", {})
                except ClientError:
                    details["encryption"] = "None"
                
                # Get lifecycle
                try:
                    lifecycle = s3.get_bucket_lifecycle_configuration(Bucket=resource_id)
                    details["lifecycle_rules"] = lifecycle.get("Rules", [])
                except ClientError:
                    details["lifecycle_rules"] = []
                
                # Get tags
                try:
                    tags = s3.get_bucket_tagging(Bucket=resource_id)
                    details["tags"] = tags.get("TagSet", [])
                except ClientError:
                    details["tags"] = []
                    
            except ClientError as e:
                details["error"] = str(e)
        
        return details
        
    except Exception as e:
        return {"error": str(e)}

async def fetch_azure_resource_details(credentials: dict, resource_type: str, resource_id: str):
    """Fetch comprehensive Azure resource details"""
    try:
        from azure.identity import ClientSecretCredential
        from azure.mgmt.compute import ComputeManagementClient
        from azure.mgmt.network import NetworkManagementClient
        from azure.mgmt.sql import SqlManagementClient
        
        tenant_id = credentials.get("tenantId") or credentials.get("tenant_id")
        client_id = credentials.get("clientId") or credentials.get("client_id")
        client_secret = credentials.get("clientSecret") or credentials.get("client_secret")
        subscription_id = credentials.get("subscriptionId") or credentials.get("subscription_id")
        
        if not all([tenant_id, client_id, client_secret, subscription_id]):
            return {"error": "Missing Azure credentials"}
        
        credential = ClientSecretCredential(tenant_id, client_id, client_secret)
        compute_client = ComputeManagementClient(credential, subscription_id)
        network_client = NetworkManagementClient(credential, subscription_id)
        
        details = {}
        
        # VM Details
        if "vm" in resource_type.lower():
            try:
                # Find the VM across all resource groups
                for vm in compute_client.virtual_machines.list_all():
                    if vm.name == resource_id:
                        resource_group = vm.id.split('/')[4]
                        
                        # Get VM details
                        details["vm"] = {
                            "name": vm.name,
                            "location": vm.location,
                            "size": vm.hardware_profile.vm_size if vm.hardware_profile else None,
                            "os_type": vm.storage_profile.os_disk.os_type if vm.storage_profile and vm.storage_profile.os_disk else None,
                            "id": vm.id,
                            "tags": vm.tags
                        }
                        
                        # Get instance view (power state, diagnostics)
                        instance_view = compute_client.virtual_machines.instance_view(resource_group, vm.name)
                        details["instance_view"] = {
                            "statuses": [{"code": s.code, "display_status": s.display_status} for s in (instance_view.statuses or [])],
                            "vm_agent": instance_view.vm_agent.statuses if instance_view.vm_agent else None
                        }
                        
                        # Get disks
                        if vm.storage_profile:
                            details["os_disk"] = {
                                "name": vm.storage_profile.os_disk.name,
                                "size_gb": vm.storage_profile.os_disk.disk_size_gb,
                                "caching": vm.storage_profile.os_disk.caching
                            } if vm.storage_profile.os_disk else None
                            
                            details["data_disks"] = [
                                {
                                    "name": disk.name,
                                    "size_gb": disk.disk_size_gb,
                                    "lun": disk.lun,
                                    "caching": disk.caching
                                }
                                for disk in (vm.storage_profile.data_disks or [])
                            ]
                        
                        # Get network interfaces
                        nic_refs = vm.network_profile.network_interfaces if vm.network_profile else []
                        details["network_interfaces"] = []
                        for nic_ref in nic_refs:
                            nic_id = nic_ref.id
                            nic_parts = nic_id.split('/')
                            nic_rg = nic_parts[4]
                            nic_name = nic_parts[-1]
                            nic = network_client.network_interfaces.get(nic_rg, nic_name)
                            details["network_interfaces"].append({
                                "name": nic.name,
                                "private_ip": nic.ip_configurations[0].private_ip_address if nic.ip_configurations else None,
                                "primary": nic_ref.primary
                            })
                        
                        # Get extensions
                        extensions = compute_client.virtual_machine_extensions.list(resource_group, vm.name)
                        details["extensions"] = [
                            {"name": ext.name, "publisher": ext.publisher, "type": ext.type_properties_type}
                            for ext in extensions
                        ]
                        
                        break
                        
            except Exception as e:
                details["error"] = str(e)
        
        # SQL Database Details
        elif "sql" in resource_type.lower():
            try:
                sql_client = SqlManagementClient(credential, subscription_id)
                # Parse server/database from resource_id (format: "server/database")
                if "/" in resource_id:
                    server_name, db_name = resource_id.split("/", 1)
                    
                    # Find the server across resource groups
                    for server in sql_client.servers.list():
                        if server.name == server_name:
                            resource_group = server.id.split('/')[4]
                            
                            # Get database details
                            database = sql_client.databases.get(resource_group, server_name, db_name)
                            details["database"] = {
                                "name": database.name,
                                "location": database.location,
                                "sku": database.sku.name if database.sku else None,
                                "max_size_bytes": database.max_size_bytes,
                                "status": database.status,
                                "creation_date": str(database.creation_date) if database.creation_date else None
                            }
                            
                            # Get server details
                            details["server"] = {
                                "name": server.name,
                                "version": server.version,
                                "administrator_login": server.administrator_login,
                                "state": server.state
                            }
                            
                            break
            except Exception as e:
                details["error"] = str(e)
        
        return details
        
    except Exception as e:
        return {"error": str(e)}

async def fetch_gcp_resource_details(credentials: dict, resource_type: str, resource_id: str):
    """Fetch comprehensive GCP resource details"""
    try:
        from google.cloud import compute_v1, storage
        from google.oauth2 import service_account
        import json
        import os
        
        # Support multiple credential key names for compatibility
        sa_json = credentials.get("serviceAccountJson") or credentials.get("serviceAccountKey") or credentials.get("credentials")
        sa_path = credentials.get("serviceAccountPath")
        project = credentials.get("projectId") or credentials.get("project_id") or credentials.get("project")
        
        if not project:
            return {"error": "Missing GCP projectId"}
        
        # Load credentials from JSON or file path
        if sa_json:
            creds_json = json.loads(sa_json) if isinstance(sa_json, str) else sa_json
            creds = service_account.Credentials.from_service_account_info(creds_json)
        elif sa_path and os.path.exists(sa_path):
            creds = service_account.Credentials.from_service_account_file(sa_path)
        else:
            return {"error": "Missing GCP service account credentials"}
        
        creds = creds.with_scopes(['https://www.googleapis.com/auth/cloud-platform'])
        
        details = {}
        
        # Compute Instance Details
        if "instance" in resource_type.lower():
            try:
                compute_client = compute_v1.InstancesClient(credentials=creds)
                
                # Find instance across all zones
                agg_list = compute_client.aggregated_list(project=project)
                for zone_name, scoped_list in agg_list:
                    for inst in scoped_list.instances or []:
                        if inst.name == resource_id:
                            zone = zone_name.split('/')[-1]
                            
                            # Get full instance details
                            instance = compute_client.get(project=project, zone=zone, instance=resource_id)
                            
                            details["instance"] = {
                                "name": instance.name,
                                "status": instance.status,
                                "machine_type": instance.machine_type.split('/')[-1],
                                "zone": zone,
                                "cpu_platform": instance.cpu_platform,
                                "creation_timestamp": instance.creation_timestamp,
                                "description": instance.description
                            }
                            
                            # Get disks
                            details["disks"] = [
                                {
                                    "device_name": disk.device_name,
                                    "boot": disk.boot,
                                    "auto_delete": disk.auto_delete,
                                    "source": disk.source.split('/')[-1] if disk.source else None
                                }
                                for disk in (instance.disks or [])
                            ]
                            
                            # Get network interfaces
                            details["network_interfaces"] = [
                                {
                                    "network": ni.network.split('/')[-1] if ni.network else None,
                                    "subnetwork": ni.subnetwork.split('/')[-1] if ni.subnetwork else None,
                                    "internal_ip": ni.network_i_p,
                                    "external_ips": [ac.nat_i_p for ac in (ni.access_configs or []) if ac.nat_i_p]
                                }
                                for ni in (instance.network_interfaces or [])
                            ]
                            
                            # Get metadata
                            if instance.metadata and instance.metadata.items:
                                details["metadata"] = [
                                    {"key": item.key, "value": item.value}
                                    for item in instance.metadata.items
                                ]
                            
                            # Get tags
                            if instance.tags and instance.tags.items:
                                details["tags"] = list(instance.tags.items)
                            
                            # Get labels
                            if instance.labels:
                                details["labels"] = dict(instance.labels)
                            
                            # Get service accounts
                            details["service_accounts"] = [
                                {"email": sa.email, "scopes": list(sa.scopes)}
                                for sa in (instance.service_accounts or [])
                            ]
                            
                            break
                            
            except Exception as e:
                details["error"] = str(e)
        
        # Storage Bucket Details
        elif "bucket" in resource_type.lower():
            try:
                storage_client = storage.Client(project=project, credentials=creds)
                bucket = storage_client.get_bucket(resource_id)
                
                details["bucket"] = {
                    "name": bucket.name,
                    "location": bucket.location,
                    "storage_class": bucket.storage_class,
                    "time_created": str(bucket.time_created) if bucket.time_created else None,
                    "versioning_enabled": bucket.versioning_enabled,
                    "labels": dict(bucket.labels) if bucket.labels else {}
                }
                
                # Get lifecycle rules
                if bucket.lifecycle_rules:
                    details["lifecycle_rules"] = [
                        {
                            "action": rule.get("action", {}),
                            "condition": rule.get("condition", {})
                        }
                        for rule in bucket.lifecycle_rules
                    ]
                
            except Exception as e:
                details["error"] = str(e)
        
        return details
        
    except Exception as e:
        return {"error": str(e)}

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
    
    meta = client.metadata_json or {}
    provider = (meta.get("provider") or "aws").lower()
    
    # Fetch all resources and analyze
    try:
        if provider == "aws":
            resources = await fetch_aws_resources(client_id, meta)
            recommendations = analyze_aws_resources(resources)
        elif provider == "azure":
            resources = await fetch_azure_resources(client_id, meta)
            recommendations = analyze_azure_resources(resources)
        elif provider == "gcp":
            resources = await fetch_gcp_resources(client_id, meta)
            recommendations = analyze_gcp_resources(resources)
        else:
            recommendations = []
    except Exception as e:
        recommendations = [{"category": "error", "severity": "high", "title": "Analysis Error", "description": str(e), "affected_resources": [], "recommendation": "Check cloud credentials", "estimated_savings": 0}]
    
    # Calculate summary
    summary = {
        "total_recommendations": len(recommendations),
        "by_category": {},
        "by_severity": {},
        "total_potential_savings_monthly": 0
    }
    
    for rec in recommendations:
        cat = rec.get('category', 'other')
        sev = rec.get('severity', 'low')
        summary['by_category'][cat] = summary['by_category'].get(cat, 0) + 1
        summary['by_severity'][sev] = summary['by_severity'].get(sev, 0) + 1
        summary['total_potential_savings_monthly'] += rec.get('estimated_savings', 0)
    
    # Sort by severity priority
    severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    recommendations.sort(key=lambda x: severity_order.get(x.get('severity', 'low'), 3))
    
    return {
        "client_id": client_id,
        "client_name": client.name,
        "provider": provider,
        "recommendations": recommendations,
        "summary": summary
    }


def analyze_aws_resources(resources: dict) -> list:
    """Analyze AWS resources and generate recommendations"""
    recommendations = []
    rec_id = 1
    
    # Cost Optimization: Stopped EC2 Instances
    ec2_instances = resources.get("compute", {}).get("ec2", [])
    stopped_instances = [i for i in ec2_instances if i.get("state", "").lower() in ["stopped", "stopping"]]
    if stopped_instances:
        # Estimate EBS cost (assume 30GB per instance at $0.10/GB/month)
        estimated_cost = len(stopped_instances) * 30 * 0.10
        recommendations.append({
            "id": f"rec_{rec_id}",
            "category": "cost",
            "severity": "high" if estimated_cost > 50 else "medium",
            "title": f"{len(stopped_instances)} Stopped EC2 Instance(s)",
            "description": f"EC2 instances in stopped state still incur EBS storage costs",
            "impact": f"Potential savings: ${estimated_cost:.2f}/month",
            "affected_resources": [{"id": i.get("id"), "name": i.get("name", "N/A"), "type": i.get("type", "N/A")} for i in stopped_instances],
            "recommendation": "Create AMI for backup and terminate instances, or start if still needed",
            "estimated_savings": estimated_cost
        })
        rec_id += 1
    
    # Security: Unencrypted S3 Buckets
    s3_buckets = resources.get("storage", {}).get("s3", [])
    unencrypted_buckets = [b for b in s3_buckets if not b.get("encryption")]
    if unencrypted_buckets:
        recommendations.append({
            "id": f"rec_{rec_id}",
            "category": "security",
            "severity": "high",
            "title": f"{len(unencrypted_buckets)} Unencrypted S3 Bucket(s)",
            "description": "S3 buckets without server-side encryption are vulnerable to data breaches",
            "impact": "Data security risk",
            "affected_resources": [{"bucket": b.get("bucket") or b.get("name"), "region": b.get("region", "N/A")} for b in unencrypted_buckets],
            "recommendation": "Enable AES-256 or AWS KMS encryption on all buckets",
            "estimated_savings": 0
        })
        rec_id += 1
    
    # Security: S3 Buckets without Versioning
    no_versioning = [b for b in s3_buckets if not b.get("versioning")]
    if no_versioning:
        recommendations.append({
            "id": f"rec_{rec_id}",
            "category": "reliability",
            "severity": "medium",
            "title": f"{len(no_versioning)} S3 Bucket(s) Without Versioning",
            "description": "Buckets without versioning cannot recover from accidental deletions or overwrites",
            "impact": "Data loss risk",
            "affected_resources": [{"bucket": b.get("bucket") or b.get("name"), "region": b.get("region", "N/A")} for b in no_versioning],
            "recommendation": "Enable versioning on all critical S3 buckets",
            "estimated_savings": 0
        })
        rec_id += 1
    
    # Reliability: RDS without Multi-AZ
    rds_instances = resources.get("database", {}).get("rds", [])
    single_az_rds = [db for db in rds_instances if not db.get("multi_az")]
    if single_az_rds:
        recommendations.append({
            "id": f"rec_{rec_id}",
            "category": "reliability",
            "severity": "high",
            "title": f"{len(single_az_rds)} RDS Instance(s) Without Multi-AZ",
            "description": "Single-AZ RDS instances have no automatic failover capability",
            "impact": "High availability risk during AZ failures",
            "affected_resources": [{"id": db.get("id") or db.get("identifier"), "engine": db.get("engine", "N/A"), "size": db.get("size") or db.get("type", "N/A")} for db in single_az_rds],
            "recommendation": "Enable Multi-AZ deployment for production databases",
            "estimated_savings": 0
        })
        rec_id += 1
    
    # Security: Security Groups with Wide-Open Access
    security_groups = resources.get("networking", {}).get("security_groups", [])
    open_sgs = []
    for sg in security_groups:
        for rule in sg.get("rules", []):
            if rule.get("cidr") == "0.0.0.0/0" and rule.get("from_port") not in [80, 443]:
                open_sgs.append(sg)
                break
    if open_sgs:
        recommendations.append({
            "id": f"rec_{rec_id}",
            "category": "security",
            "severity": "critical",
            "title": f"{len(open_sgs)} Security Group(s) with Open Access",
            "description": "Security groups allowing 0.0.0.0/0 on non-standard ports expose resources to internet",
            "impact": "Critical security vulnerability",
            "affected_resources": [{"id": sg.get("id"), "name": sg.get("name", "N/A")} for sg in open_sgs],
            "recommendation": "Restrict ingress rules to specific IP ranges or security groups",
            "estimated_savings": 0
        })
        rec_id += 1
    
    # Operational Excellence: Resources without Tags
    all_resources = []
    for category in resources.values():
        if isinstance(category, dict):
            for resource_list in category.values():
                if isinstance(resource_list, list):
                    all_resources.extend(resource_list)
    
    untagged = [r for r in all_resources if not r.get("tags") or len(r.get("tags", [])) == 0]
    if len(untagged) > 5:  # Only report if significant number
        recommendations.append({
            "id": f"rec_{rec_id}",
            "category": "operational",
            "severity": "low",
            "title": f"{len(untagged)} Resource(s) Without Tags",
            "description": "Resources without proper tags are difficult to manage and track costs",
            "impact": "Poor resource management and cost allocation",
            "affected_resources": [{"id": r.get("id") or r.get("name", "unknown"), "type": r.get("type", "unknown")} for r in untagged[:10]],
            "recommendation": "Implement tagging strategy with Environment, Owner, and CostCenter tags",
            "estimated_savings": 0
        })
        rec_id += 1
    
    # Cost: Lambda functions with high error rates (if we have metrics)
    lambda_functions = resources.get("compute", {}).get("lambda", [])
    if lambda_functions:
        recommendations.append({
            "id": f"rec_{rec_id}",
            "category": "operational",
            "severity": "low",
            "title": f"{len(lambda_functions)} Lambda Function(s) Found",
            "description": "Review Lambda functions for optimization opportunities",
            "impact": "Potential cost and performance improvements",
            "affected_resources": [{"name": f.get("name"), "runtime": f.get("runtime", "N/A")} for f in lambda_functions[:5]],
            "recommendation": "Monitor Lambda execution time and memory usage for right-sizing",
            "estimated_savings": 0
        })
        rec_id += 1
    
    return recommendations


def analyze_azure_resources(resources: dict) -> list:
    """Analyze Azure resources and generate recommendations"""
    recommendations = []
    rec_id = 1
    
    # Cost: Stopped VMs still incurring charges
    vms = resources.get("compute", {}).get("vm", [])
    stopped_vms = [v for v in vms if v.get("state", "").lower() in ["stopped", "deallocated"]]
    if stopped_vms:
        estimated_cost = len(stopped_vms) * 25  # Average Azure VM disk cost
        recommendations.append({
            "id": f"rec_{rec_id}",
            "category": "cost",
            "severity": "high" if estimated_cost > 50 else "medium",
            "title": f"{len(stopped_vms)} Stopped Virtual Machine(s)",
            "description": "Deallocated VMs still incur managed disk storage costs",
            "impact": f"Potential savings: ${estimated_cost:.2f}/month",
            "affected_resources": [{"name": v.get("id"), "size": v.get("size", "N/A"), "location": v.get("location", "N/A")} for v in stopped_vms],
            "recommendation": "Delete VMs and create snapshots if no longer needed, or start if still required",
            "estimated_savings": estimated_cost
        })
        rec_id += 1
    
    # Security: Unencrypted Storage Accounts
    storage_accounts = resources.get("storage", {}).get("storage_account", [])
    # Note: Azure storage accounts have encryption enabled by default
    # This check is for awareness - all accounts should exist
    unencrypted = []  # Placeholder - would need detailed encryption config check
    if unencrypted:
        recommendations.append({
            "id": f"rec_{rec_id}",
            "category": "security",
            "severity": "high",
            "title": f"{len(unencrypted)} Unencrypted Storage Account(s)",
            "description": "Storage accounts without encryption expose data to security risks",
            "impact": "Data security vulnerability",
            "affected_resources": [{"name": s.get("account"), "location": s.get("location", "N/A"), "sku": s.get("sku", "N/A")} for s in unencrypted],
            "recommendation": "Enable Azure Storage Service Encryption (SSE) for all storage accounts",
            "estimated_savings": 0
        })
        rec_id += 1
    
    # Reliability: SQL Databases without Geo-Replication
    sql_databases = resources.get("database", {}).get("sql", [])
    # Note: Geo-replication check would need additional API call
    no_geo_replication = []  # Placeholder
    if no_geo_replication:
        recommendations.append({
            "id": f"rec_{rec_id}",
            "category": "reliability",
            "severity": "high",
            "title": f"{len(no_geo_replication)} SQL Database(s) Without Geo-Replication",
            "description": "Databases without geo-replication have no automatic failover to secondary region",
            "impact": "Data loss risk during regional outages",
            "affected_resources": [{"name": db.get("id"), "engine": db.get("engine", "N/A"), "sku": db.get("sku", "N/A")} for db in no_geo_replication],
            "recommendation": "Enable active geo-replication for production databases",
            "estimated_savings": 0
        })
        rec_id += 1
    
    # Security: Public Blob Containers
    blob_containers = []
    for sa in storage_accounts:
        containers = sa.get("containers", [])
        for container in containers:
            if container.get("public_access") not in [None, "off", "None"]:
                blob_containers.append({"storage_account": sa.get("name"), "container": container.get("name")})
    
    if blob_containers:
        recommendations.append({
            "id": f"rec_{rec_id}",
            "category": "security",
            "severity": "critical",
            "title": f"{len(blob_containers)} Blob Container(s) with Public Access",
            "description": "Containers allowing public access can lead to data exposure",
            "impact": "Critical data security risk",
            "affected_resources": blob_containers,
            "recommendation": "Disable public access and use Shared Access Signatures (SAS) or Azure AD authentication",
            "estimated_savings": 0
        })
        rec_id += 1
    
    # Operational: Resources without Tags
    all_resources = []
    for category in resources.values():
        if isinstance(category, dict):
            for resource_list in category.values():
                if isinstance(resource_list, list):
                    all_resources.extend(resource_list)
    
    untagged = [r for r in all_resources if not r.get("tags") or len(r.get("tags", {})) == 0]
    if len(untagged) > 5:
        recommendations.append({
            "id": f"rec_{rec_id}",
            "category": "operational",
            "severity": "low",
            "title": f"{len(untagged)} Resource(s) Without Tags",
            "description": "Resources without tags are difficult to manage, track costs, and organize",
            "impact": "Poor resource governance and cost allocation",
            "affected_resources": [{"name": r.get("name", "unknown"), "type": r.get("type", "unknown")} for r in untagged[:10]],
            "recommendation": "Implement tagging policy with Environment, Owner, CostCenter, and Project tags",
            "estimated_savings": 0
        })
        rec_id += 1
    
    # Cost: Unattached Managed Disks
    disks = resources.get("storage", {}).get("disks", [])
    unattached = [d for d in disks if d.get("unused") or not d.get("managed_by")]
    if unattached:
        total_gb = sum(d.get("size_gb", 50) for d in unattached)
        estimated_cost = total_gb * 0.05  # ~$0.05/GB/month for standard SSD
        recommendations.append({
            "id": f"rec_{rec_id}",
            "category": "cost",
            "severity": "medium",
            "title": f"{len(unattached)} Unattached Managed Disk(s)",
            "description": "Unattached disks continue to incur storage costs",
            "impact": f"Potential savings: ${estimated_cost:.2f}/month",
            "affected_resources": [{"name": d.get("id"), "size_gb": d.get("size_gb", "N/A"), "location": d.get("location", "N/A")} for d in unattached],
            "recommendation": "Delete unused disks or create snapshots and delete the disks",
            "estimated_savings": estimated_cost
        })
        rec_id += 1
    
    # Cost: Old Snapshots
    snapshots = resources.get("storage", {}).get("snapshots", [])
    if snapshots:
        from datetime import datetime, timedelta
        old_snapshots = []
        for snap in snapshots:
            created = snap.get("time_created")
            if created:
                try:
                    created_date = datetime.fromisoformat(str(created).replace('Z', '+00:00'))
                    if (datetime.now(created_date.tzinfo) - created_date).days > 90:
                        old_snapshots.append(snap)
                except:
                    pass
        
        if old_snapshots:
            estimated_cost = len(old_snapshots) * 5  # Rough estimate for snapshot storage
            recommendations.append({
                "id": f"rec_{rec_id}",
                "category": "cost",
                "severity": "medium",
                "title": f"{len(old_snapshots)} Old Snapshot(s) (>90 days)",
                "description": "Old snapshots continue to incur storage costs",
                "impact": f"Potential savings: ${estimated_cost:.2f}/month",
                "affected_resources": [{"name": s.get("name"), "created": s.get("time_created", "N/A")} for s in old_snapshots[:10]],
                "recommendation": "Review and delete snapshots older than 90 days if no longer needed",
                "estimated_savings": estimated_cost
            })
            rec_id += 1
    
    # Performance: VMs with High CPU Usage (placeholder - would need metrics)
    running_vms = [v for v in vms if v.get("state", "").lower() == "running"]
    if running_vms:
        recommendations.append({
            "id": f"rec_{rec_id}",
            "category": "operational",
            "severity": "low",
            "title": f"{len(running_vms)} Running Virtual Machine(s)",
            "description": "Monitor VM performance metrics for optimization opportunities",
            "impact": "Potential cost and performance improvements",
            "affected_resources": [{"name": v.get("id"), "size": v.get("size", "N/A")} for v in running_vms[:5]],
            "recommendation": "Review Azure Monitor metrics for CPU, memory, and disk usage to right-size VMs",
            "estimated_savings": 0
        })
        rec_id += 1
    
    return recommendations


def analyze_gcp_resources(resources: dict) -> list:
    """Analyze GCP resources and generate recommendations"""
    recommendations = []
    rec_id = 1
    
    # Cost: Stopped Compute Instances
    instances = resources.get("compute", {}).get("instances", [])
    stopped = [i for i in instances if i.get("status", "").lower() in ["stopped", "terminated", "suspended"]]
    if stopped:
        estimated_cost = len(stopped) * 20  # Average persistent disk cost
        recommendations.append({
            "id": f"rec_{rec_id}",
            "category": "cost",
            "severity": "high" if estimated_cost > 50 else "medium",
            "title": f"{len(stopped)} Stopped Compute Instance(s)",
            "description": "Stopped instances still incur persistent disk costs",
            "impact": f"Potential savings: ${estimated_cost:.2f}/month",
            "affected_resources": [{"name": i.get("name"), "zone": i.get("zone", "N/A"), "machine_type": i.get("machine_type", "N/A")} for i in stopped],
            "recommendation": "Delete instances and create snapshots if needed, or start if still required",
            "estimated_savings": estimated_cost
        })
        rec_id += 1
    
    # Security: Public GCS Buckets
    buckets = resources.get("storage", {}).get("buckets", [])
    public_buckets = [b for b in buckets if b.get("public", False) or b.get("iam_configuration", {}).get("uniform_bucket_level_access", {}).get("enabled") == False]
    if public_buckets:
        recommendations.append({
            "id": f"rec_{rec_id}",
            "category": "security",
            "severity": "critical",
            "title": f"{len(public_buckets)} Public Cloud Storage Bucket(s)",
            "description": "Publicly accessible buckets can lead to data exposure and unauthorized access",
            "impact": "Critical data security risk",
            "affected_resources": [{"name": b.get("name"), "location": b.get("location", "N/A"), "storage_class": b.get("storage_class", "N/A")} for b in public_buckets],
            "recommendation": "Remove public access, enable uniform bucket-level access, and use IAM for controlled access",
            "estimated_savings": 0
        })
        rec_id += 1
    
    # Security: Buckets without Encryption
    unencrypted_buckets = [b for b in buckets if not b.get("encryption")]
    if unencrypted_buckets:
        recommendations.append({
            "id": f"rec_{rec_id}",
            "category": "security",
            "severity": "high",
            "title": f"{len(unencrypted_buckets)} Unencrypted Cloud Storage Bucket(s)",
            "description": "Buckets without customer-managed encryption keys (CMEK) use default encryption only",
            "impact": "Data security best practice violation",
            "affected_resources": [{"name": b.get("name"), "location": b.get("location", "N/A")} for b in unencrypted_buckets],
            "recommendation": "Enable customer-managed encryption keys (CMEK) for sensitive data",
            "estimated_savings": 0
        })
        rec_id += 1
    
    # Reliability: Cloud SQL without High Availability
    sql_instances = resources.get("database", {}).get("sql", [])
    no_ha = [db for db in sql_instances if not db.get("settings", {}).get("availability_type") == "REGIONAL"]
    if no_ha:
        recommendations.append({
            "id": f"rec_{rec_id}",
            "category": "reliability",
            "severity": "high",
            "title": f"{len(no_ha)} Cloud SQL Instance(s) Without High Availability",
            "description": "Instances without regional availability have no automatic failover capability",
            "impact": "Downtime risk during zone failures",
            "affected_resources": [{"name": db.get("name"), "region": db.get("region", "N/A"), "tier": db.get("tier", "N/A")} for db in no_ha],
            "recommendation": "Enable high availability (regional) configuration for production databases",
            "estimated_savings": 0
        })
        rec_id += 1
    
    # Security: Firewall Rules with Open Access
    firewall_rules = resources.get("networking", {}).get("firewall_rules", [])
    open_rules = []
    for rule in firewall_rules:
        source_ranges = rule.get("source_ranges", [])
        if "0.0.0.0/0" in source_ranges:
            # Check if it's not just HTTP/HTTPS
            allowed = rule.get("allowed", [])
            for allow in allowed:
                ports = allow.get("ports", [])
                if ports and not all(p in ["80", "443"] for p in ports):
                    open_rules.append(rule)
                    break
    
    if open_rules:
        recommendations.append({
            "id": f"rec_{rec_id}",
            "category": "security",
            "severity": "critical",
            "title": f"{len(open_rules)} Firewall Rule(s) with Wide-Open Access",
            "description": "Firewall rules allowing 0.0.0.0/0 on non-standard ports expose resources to internet",
            "impact": "Critical security vulnerability",
            "affected_resources": [{"name": r.get("name"), "network": r.get("network", "N/A")} for r in open_rules],
            "recommendation": "Restrict source IP ranges to specific CIDR blocks or use Identity-Aware Proxy",
            "estimated_savings": 0
        })
        rec_id += 1
    
    # Operational: Resources without Labels
    all_resources = []
    for category in resources.values():
        if isinstance(category, dict):
            for resource_list in category.values():
                if isinstance(resource_list, list):
                    all_resources.extend(resource_list)
    
    unlabeled = [r for r in all_resources if not r.get("labels") or len(r.get("labels", {})) == 0]
    if len(unlabeled) > 5:
        recommendations.append({
            "id": f"rec_{rec_id}",
            "category": "operational",
            "severity": "low",
            "title": f"{len(unlabeled)} Resource(s) Without Labels",
            "description": "Resources without labels are difficult to organize and track costs",
            "impact": "Poor resource management and cost attribution",
            "affected_resources": [{"name": r.get("name", "unknown"), "type": r.get("type", "unknown")} for r in unlabeled[:10]],
            "recommendation": "Implement labeling strategy with environment, owner, cost-center, and project labels",
            "estimated_savings": 0
        })
        rec_id += 1
    
    # Cost: Unattached Persistent Disks
    disks = resources.get("storage", {}).get("disks", [])
    unattached = [d for d in disks if not d.get("users") or len(d.get("users", [])) == 0]
    if unattached:
        total_gb = sum(d.get("size_gb", 50) for d in unattached)
        estimated_cost = total_gb * 0.04  # $0.04/GB/month for standard persistent disks
        recommendations.append({
            "id": f"rec_{rec_id}",
            "category": "cost",
            "severity": "medium",
            "title": f"{len(unattached)} Unattached Persistent Disk(s)",
            "description": "Unattached disks continue to incur storage costs",
            "impact": f"Potential savings: ${estimated_cost:.2f}/month",
            "affected_resources": [{"name": d.get("name"), "size_gb": d.get("size_gb", "N/A"), "zone": d.get("zone", "N/A")} for d in unattached],
            "recommendation": "Delete unused disks or create snapshots and delete the disks",
            "estimated_savings": estimated_cost
        })
        rec_id += 1
    
    # Cost: Old Snapshots
    snapshots = resources.get("storage", {}).get("snapshots", [])
    if snapshots:
        from datetime import datetime, timedelta
        old_snapshots = []
        for snap in snapshots:
            created = snap.get("creation_timestamp")
            if created:
                try:
                    created_date = datetime.fromisoformat(str(created).replace('Z', '+00:00'))
                    if (datetime.now(created_date.tzinfo) - created_date).days > 90:
                        old_snapshots.append(snap)
                except:
                    pass
        
        if old_snapshots:
            total_gb = sum(s.get("storage_bytes", 0) / (1024**3) for s in old_snapshots)
            estimated_cost = total_gb * 0.026  # $0.026/GB/month for snapshots
            recommendations.append({
                "id": f"rec_{rec_id}",
                "category": "cost",
                "severity": "medium",
                "title": f"{len(old_snapshots)} Old Snapshot(s) (>90 days)",
                "description": "Old snapshots continue to incur storage costs",
                "impact": f"Potential savings: ${estimated_cost:.2f}/month",
                "affected_resources": [{"name": s.get("name"), "created": s.get("creation_timestamp", "N/A")} for s in old_snapshots[:10]],
                "recommendation": "Review and delete snapshots older than 90 days if no longer needed",
                "estimated_savings": estimated_cost
            })
            rec_id += 1
    
    # Performance: Monitor running instances
    running_instances = [i for i in instances if i.get("status", "").lower() == "running"]
    if running_instances:
        recommendations.append({
            "id": f"rec_{rec_id}",
            "category": "operational",
            "severity": "low",
            "title": f"{len(running_instances)} Running Compute Instance(s)",
            "description": "Review Cloud Monitoring metrics for optimization opportunities",
            "impact": "Potential cost and performance improvements",
            "affected_resources": [{"name": i.get("name"), "machine_type": i.get("machine_type", "N/A")} for i in running_instances[:5]],
            "recommendation": "Use Cloud Monitoring to analyze CPU, memory, and disk metrics for right-sizing",
            "estimated_savings": 0
        })
        rec_id += 1
    
    return recommendations

