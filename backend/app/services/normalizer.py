"""
Cloud provider response normalization to common schema.

This module transforms provider-specific resource data into a standardized format,
allowing the application to work with resources from AWS, Azure, and GCP using
a unified data structure.

Common Schema:
    {
        "provider": "aws|azure|gcp",
        "resources": [
            {
                "resource_type": "vm|storage|database|...",
                "id": "unique-resource-id",
                "name": "human-readable-name",
                "region": "geographic-location",
                "size": "instance-size-or-tier",
                "metadata": { ... }  # Original provider response
            }
        ]
    }

Benefits:
    1. Unified Interface: Frontend doesn't need provider-specific logic
    2. Cross-Cloud Analysis: Compare resources across AWS/Azure/GCP
    3. Simplified Recommendations: Single rule engine for all providers
    4. Easy Provider Addition: Just add normalization function

Provider-Specific Mappings:
    AWS:
        - instances → EC2 instances
        - id: InstanceId
        - type: InstanceType
        - region: Region from credentials
    
    Azure:
        - vms → Virtual Machines
        - id: Resource ID (long ARM path)
        - size: vm_size (e.g., Standard_B2s)
        - region: location
    
    GCP:
        - instances → Compute Engine instances
        - id: instance name
        - type: machine_type
        - region: zone

Usage:
    raw_aws = await aws_list_instances(credentials)
    normalized = normalize_provider_response("aws", raw_aws)
    
    # Now all resources have consistent structure
    for resource in normalized["resources"]:
        print(f"{resource['id']} ({resource['size']}) in {resource['region']}")

Extension:
    To add support for new resource types:
    1. Add resource_type to schema (e.g., "database", "network")
    2. Update provider-specific mapping in normalize_provider_response()
    3. Ensure metadata field preserves original provider data

Author: Cloud Optimizer Team
Version: 2.0.0
Last Modified: 2026-01-25
"""

def normalize_provider_response(provider: str, payload: dict) -> dict:
    """
    Transform provider-specific response into common schema.
    
    Takes raw API responses from cloud providers and converts them to a
    standardized format for uniform processing across the application.
    
    Args:
        provider (str): Cloud provider identifier ("aws", "azure", or "gcp")
        payload (dict): Raw provider response containing resource data
    
    Returns:
        dict: Normalized response with structure:
            {
                "provider": "aws|azure|gcp",
                "resources": [
                    {
                        "resource_type": "vm",
                        "id": "resource-identifier",
                        "name": "resource-name",
                        "region": "location",
                        "size": "size-or-tier",
                        "metadata": { ... }  # Original data
                    }
                ]
            }
    
    Provider-Specific Transformations:
        AWS:
            - Extracts from payload["instances"]
            - Maps: id → i-xxx, size → InstanceType, region → Region
        
        Azure:
            - Extracts from payload["vms"]
            - Maps: id → ARM path, size → vm_size, region → location
        
        GCP:
            - Extracts from payload["instances"]
            - Maps: id → instance name, size → machine_type, region → zone
    
    Metadata Preservation:
        The "metadata" field contains the complete original provider response,
        allowing access to provider-specific fields not in the common schema.
    
    Example Input (AWS):
        {
            "provider": "aws",
            "instances": [
                {"id": "i-123", "type": "t3.medium", "region": "us-east-1"}
            ]
        }
    
    Example Output:
        {
            "provider": "aws",
            "resources": [
                {
                    "resource_type": "vm",
                    "id": "i-123",
                    "name": "i-123",
                    "region": "us-east-1",
                    "size": "t3.medium",
                    "metadata": {"id": "i-123", "type": "t3.medium", ...}
                }
            ]
        }
    """
    # Initialize normalized output structure
    out = {"provider": provider, "resources": []}
    
    # AWS-specific normalization
    if provider == "aws":
        for i in payload.get("instances", []):
            out["resources"].append({
                "resource_type":"vm",
                "id": i.get("id"),
                "name": i.get("id"),  # AWS instances use ID as name
                "region": i.get("region"),
                "size": i.get("type"),
                "metadata": i  # Preserve original AWS data
            })
    
    # Azure-specific normalization
    if provider == "azure":
        for i in payload.get("vms", []):
            out["resources"].append({
                "resource_type":"vm",
                "id": i.get("id"),
                "name": i.get("id"),  # Azure uses ARM path as ID
                "region": i.get("region"),
                "size": i.get("size"),
                "metadata": i  # Preserve original Azure data
            })
    
    # GCP-specific normalization
    if provider == "gcp":
        for i in payload.get("instances", []):
            out["resources"].append({
                "resource_type":"vm",
                "id": i.get("id"),
                "name": i.get("id"),  # GCP uses instance name
                "region": i.get("zone"),  # GCP uses zones, not regions
                "size": i.get("type"),
                "metadata": i  # Preserve original GCP data
            })
    
    return out