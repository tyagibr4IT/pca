"""
Cloud connectors adapter pattern. Replace stub functions with real SDK calls and proper credentials.
AWS: boto3 (list EC2, s3 usage, costexplorer) - requires AWS creds.
Azure: azure-mgmt-compute, consumption usage APIs.
GCP: google-cloud-compute, cloudbilling.
"""

import asyncio
from typing import Dict, Any

# ---- Provider stubs ----
async def aws_list_instances(aws_credentials) -> Dict[str, Any]:
    # STUB: Replace with boto3 async wrapper or run in executor (boto3 is sync)
    # Example: boto3.client('ec2').describe_instances()
    await asyncio.sleep(0.1)
    return {"provider":"aws","instances":[{"id":"i-0123","type":"t3.medium","region":"us-east-1"}]}

async def aws_get_s3_usage(aws_credentials) -> Dict[str, Any]:
    await asyncio.sleep(0.1)
    return {"buckets":[{"name":"my-bucket","size_bytes":12345678}]}

async def azure_list_vms(az_credentials) -> Dict[str, Any]:
    await asyncio.sleep(0.1)
    return {"provider":"azure","vms":[{"id":"/subscriptions/.../vm1","size":"Standard_B2s","region":"eastus"}]}

async def gcp_list_instances(gcp_credentials) -> Dict[str, Any]:
    await asyncio.sleep(0.1)
    return {"provider":"gcp","instances":[{"id":"gcp-vm-1","type":"e2-medium","zone":"us-central1-a"}]}

# Normalizer import
from app.services.normalizer import normalize_provider_response

async def collect_all(tenant_config):
    # tenant_config contains provider credentials for that tenant
    results = []
    if tenant_config.get("aws"):
        r = await aws_list_instances(tenant_config["aws"])
        results.append(normalize_provider_response("aws", r))
    if tenant_config.get("azure"):
        r = await azure_list_vms(tenant_config["azure"])
        results.append(normalize_provider_response("azure", r))
    if tenant_config.get("gcp"):
        r = await gcp_list_instances(tenant_config["gcp"])
        results.append(normalize_provider_response("gcp", r))
    return results