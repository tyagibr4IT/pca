"""
OpenAI Client Factory

This module provides a factory function to create the appropriate OpenAI client
based on the configured provider (standard OpenAI or Azure OpenAI).

The factory pattern allows seamless switching between providers using the
OPENAI_PROVIDER environment variable without changing application code.
"""

from openai import OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI
from typing import Union
from app.config import settings
from app.services.azure_openai_auth import get_azure_openai_token


def get_openai_client() -> Union[OpenAI, AzureOpenAI]:
    """
    Get synchronous OpenAI client based on configured provider.
    
    Returns standard OpenAI client or Azure OpenAI client depending on
    OPENAI_PROVIDER setting. Handles authentication automatically.
    
    Returns:
        Union[OpenAI, AzureOpenAI]: Configured OpenAI client instance
    
    Raises:
        ValueError: If provider is invalid or required configuration is missing
        
    Usage:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=get_model_name(),
            messages=[{"role": "user", "content": "Hello"}]
        )
    """
    if settings.OPENAI_PROVIDER == "azure":
        if not settings.AZURE_MODEL_ENDPOINT:
            raise ValueError("Azure OpenAI endpoint not configured")
        
        # Azure OpenAI requires token-based authentication
        # Note: For sync client, you may need to handle token refresh differently
        # This is a simplified version - consider using azure-identity for production
        return AzureOpenAI(
            azure_endpoint=settings.AZURE_MODEL_ENDPOINT,
            api_version=settings.AZURE_API_VERSION,
            azure_ad_token_provider=None,  # Will need token provider for sync
        )
    
    elif settings.OPENAI_PROVIDER == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")
        
        return OpenAI(api_key=settings.OPENAI_API_KEY)
    
    else:
        raise ValueError(f"Invalid OPENAI_PROVIDER: {settings.OPENAI_PROVIDER}")


async def get_async_openai_client() -> Union[AsyncOpenAI, AsyncAzureOpenAI]:
    """
    Get asynchronous OpenAI client based on configured provider.
    
    Returns async-capable OpenAI client for use with FastAPI async endpoints.
    Handles Azure OAuth token retrieval automatically.
    
    Returns:
        Union[AsyncOpenAI, AsyncAzureOpenAI]: Configured async OpenAI client
    
    Raises:
        ValueError: If provider is invalid or required configuration is missing
        
    Usage:
        client = await get_async_openai_client()
        response = await client.chat.completions.create(
            model=get_model_name(),
            messages=[{"role": "user", "content": "Hello"}]
        )
    """
    if settings.OPENAI_PROVIDER == "azure":
        if not settings.AZURE_MODEL_ENDPOINT:
            raise ValueError("Azure OpenAI endpoint not configured")
        
        # Get Azure OAuth token
        token = await get_azure_openai_token()
        
        return AsyncAzureOpenAI(
            azure_endpoint=settings.AZURE_MODEL_ENDPOINT,
            api_version=settings.AZURE_API_VERSION,
            api_key=token,  # Use token as API key for Azure
        )
    
    elif settings.OPENAI_PROVIDER == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")
        
        return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    else:
        raise ValueError(f"Invalid OPENAI_PROVIDER: {settings.OPENAI_PROVIDER}")


def get_model_name(model_type: str = "chat") -> str:
    """
    Get the appropriate model name based on provider and type.
    
    Args:
        model_type: Type of model ('chat' or 'embedding')
    
    Returns:
        str: Model name/deployment name for the configured provider
    
    Usage:
        chat_model = get_model_name("chat")
        embedding_model = get_model_name("embedding")
    """
    if settings.OPENAI_PROVIDER == "azure":
        if model_type == "chat":
            return settings.AZURE_CHAT_MODEL_NAME or "gpt-4o-mini"
        elif model_type == "embedding":
            return settings.AZURE_EMBEDDINGS_DEPLOYMENT_NAME or "text-embedding-3-small"
        else:
            raise ValueError(f"Invalid model_type: {model_type}")
    
    elif settings.OPENAI_PROVIDER == "openai":
        if model_type == "chat":
            return settings.OPENAI_MODEL
        elif model_type == "embedding":
            return settings.OPENAI_EMBEDDING_MODEL
        else:
            raise ValueError(f"Invalid model_type: {model_type}")
    
    else:
        raise ValueError(f"Invalid OPENAI_PROVIDER: {settings.OPENAI_PROVIDER}")
