"""
Take provider-specific responses and normalize into common schema.
Example output:
{
  "provider": "aws",
  "resources": [
    {"resource_type":"vm", "id":"i-0123", "name":null, "region":"us-east-1", "size":"t3.medium", "metadata": {...}}
  ]
}
"""

def normalize_provider_response(provider: str, payload: dict) -> dict:
    out = {"provider": provider, "resources": []}
    if provider == "aws":
        for i in payload.get("instances", []):
            out["resources"].append({
                "resource_type":"vm", "id": i.get("id"), "name": i.get("id"),
                "region": i.get("region"), "size": i.get("type"), "metadata": i
            })
    if provider == "azure":
        for i in payload.get("vms", []):
            out["resources"].append({
                "resource_type":"vm", "id": i.get("id"), "name": i.get("id"),
                "region": i.get("region"), "size": i.get("size"), "metadata": i
            })
    if provider == "gcp":
        for i in payload.get("instances", []):
            out["resources"].append({
                "resource_type":"vm", "id": i.get("id"), "name": i.get("id"),
                "region": i.get("zone"), "size": i.get("type"), "metadata": i
            })
    return out