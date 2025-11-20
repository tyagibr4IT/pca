"""
This simple module demonstrates how to validate Azure AD tokens.
In production: use MSAL to perform full OIDC flow and token validation, check 'roles' claim.
"""

from fastapi import HTTPException
import requests
from app.config import settings

# A minimal function to validate an id_token via https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration
def get_jwks():
    # fetch JWKS once and cache; omitted for brevity - production: cache & rotate
    well_known = f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}/v2.0/.well-known/openid-configuration"
    r = requests.get(well_known, timeout=5)
    jwks_uri = r.json()["jwks_uri"]
    jwks = requests.get(jwks_uri, timeout=5).json()
    return jwks

def validate_azure_token(id_token: str):
    # For brevity: in tests we will accept a local JWT; production: verify signature using jwks and audience/issuer.
    from app.auth.jwt import decode_token
    payload = decode_token(id_token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload