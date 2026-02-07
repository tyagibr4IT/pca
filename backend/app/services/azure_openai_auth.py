"""
Azure OpenAI Authentication Module

This module handles OAuth token retrieval for Azure OpenAI API authentication.
Uses Azure AD client credentials flow to obtain access tokens for API requests.
"""

import httpx
from typing import Optional
from app.config import settings


async def get_azure_openai_token() -> Optional[str]:
    """
    Retrieve Azure OpenAI OAuth token using client credentials flow.
    
    This function authenticates with Azure AD using CLIENT_ID and CLIENT_SECRET
    to obtain an access token for Azure OpenAI API requests. The token is used
    for all Azure OpenAI operations when OPENAI_PROVIDER='azure'.
    
    Returns:
        Optional[str]: Bearer token string if successful, None if authentication fails
    
    Raises:
        httpx.HTTPError: If token request fails
        
    Environment Variables:
        AZURE_CLIENT_ID: Azure AD application (client) ID
        AZURE_CLIENT_SECRET: Azure AD client secret
    
    Usage:
        token = await get_azure_openai_token()
        if token:
            headers = {"Authorization": f"Bearer {token}"}
    """
    if not settings.AZURE_CLIENT_ID or not settings.AZURE_CLIENT_SECRET:
        raise ValueError("Azure client credentials not configured")
    
    url = f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}/oauth2/v2.0/token"
    
    data = {
        "client_id": settings.AZURE_CLIENT_ID,
        "scope": "https://cognitiveservices.azure.com/.default",
        "client_secret": settings.AZURE_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=data)
        response.raise_for_status()
        token_data = response.json()
        return token_data.get("access_token")
