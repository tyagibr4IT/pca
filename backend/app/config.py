"""Application configuration management using Pydantic Settings.

This module defines the centralized configuration for the Cloud Optimizer API.
It loads settings from environment variables and .env files, with support for
local development and production deployments using Azure Key Vault.

Configuration sources (in priority order):
1. Environment variables (highest priority)
2. .env file in project root
3. Default values defined in Settings class

Security:
- JWT_SECRET MUST be changed in production (generate with secrets.token_urlsafe(64))
- Database credentials should never be committed to source control
- Use Azure Key Vault for production secrets management

Usage:
    from app.config import settings
    
    database_url = settings.DATABASE_URL
    jwt_secret = settings.JWT_SECRET

Attributes:
    settings: Global Settings instance (cached singleton)

Author: Cloud Optimizer Team
Version: 2.0.0
Last Modified: 2026-01-25
"""

import os
from functools import lru_cache
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    """
    Application configuration schema.
    
    This class defines all configuration parameters for the application using
    Pydantic BaseSettings. Values are automatically loaded from environment
    variables or .env file, with type validation and default values.
    
    Environment Variables:
        ENV (str): Deployment environment (development/staging/production)
        APP_HOST (str): Host IP address for FastAPI server
        APP_PORT (str): Port number for FastAPI server
        DATABASE_URL (str): PostgreSQL connection string (REQUIRED)
        REDIS_URL (str): Redis connection string for caching
        KEYVAULT_NAME (str): Azure Key Vault name for production secrets
        
        OpenAI Provider Configuration:
        OPENAI_PROVIDER (str): Provider type ('openai' or 'azure')
        
        Standard OpenAI Configuration:
        OPENAI_API_KEY (str): Standard OpenAI API key
        OPENAI_MODEL (str): Model name for chat completions
        OPENAI_EMBEDDING_MODEL (str): Model name for embeddings
        
        Azure OpenAI Configuration:
        AZURE_MODEL_ENDPOINT (str): Azure OpenAI endpoint URL
        AZURE_API_VERSION (str): Azure OpenAI API version
        AZURE_EMBEDDINGS_MODEL_NAME (str): Azure embeddings model name
        AZURE_CHAT_MODEL_NAME (str): Azure chat model name
        AZURE_PROJECT_ID (str): Azure project ID
        AZURE_EMBEDDINGS_DEPLOYMENT_NAME (str): Azure embeddings deployment name
        AZURE_CLIENT_ID (str): Azure AD client ID for OAuth
        AZURE_CLIENT_SECRET (str): Azure AD client secret for OAuth
        AZURE_TELEMETRY (bool): Enable/disable Azure telemetry
        
        Azure AD Authentication (for OIDC user login):
        AZURE_AD_TENANT_ID (str): Azure AD tenant ID for OIDC
        AZURE_AD_CLIENT_ID (str): Azure AD application/client ID
        AZURE_AD_CLIENT_SECRET (str): Azure AD client secret
        
        JWT Configuration:
        JWT_SECRET (str): Secret key for signing JWT tokens (MUST CHANGE IN PRODUCTION)
        JWT_ALGORITHM (str): JWT signing algorithm (HS256/RS256)
        JWT_EXPIRE_MINUTES (int): Token expiration time in minutes
    
    Security Notes:
        - JWT_SECRET default is INSECURE and must be changed in production
        - Generate production secret: python -c "import secrets; print(secrets.token_urlsafe(64))"
        - Store sensitive values in Azure Key Vault, not in .env file
        - Never commit .env file to version control
    
    Example .env file:
        ENV=production
        DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/cloudopt
        JWT_SECRET=your-secure-random-secret-here
        OPENAI_API_KEY=sk-...
    """
    ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: str = "8000"
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # OpenAI Provider Selection
    OPENAI_PROVIDER: str = Field(default="openai")
    
    # Standard OpenAI Configuration
    OPENAI_API_KEY: str = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Azure OpenAI Configuration
    AZURE_MODEL_ENDPOINT: str = None
    AZURE_API_VERSION: str = "2024-02-01"
    AZURE_EMBEDDINGS_MODEL_NAME: str = None
    AZURE_CHAT_MODEL_NAME: str = None
    AZURE_PROJECT_ID: str = None
    AZURE_EMBEDDINGS_DEPLOYMENT_NAME: str = None
    AZURE_CLIENT_ID: str = None
    AZURE_CLIENT_SECRET: str = None
    AZURE_TELEMETRY: bool = False

    # Azure AD Authentication (for OIDC user login)
    AZURE_AD_TENANT_ID: str = None
    AZURE_AD_CLIENT_ID: str = None
    AZURE_AD_CLIENT_SECRET: str = None

    # SECURITY WARNING: Set a strong random JWT_SECRET in production .env file!
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(64))"
    JWT_SECRET: str = Field(default="change-me-insecure-default", env="JWT_SECRET")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings():
    """
    Get cached Settings instance (singleton pattern).
    
    This function creates and caches the Settings object using LRU cache,
    ensuring only one Settings instance exists throughout the application
    lifecycle. This improves performance by avoiding repeated .env file
    parsing and environment variable lookups.
    
    The cache is cleared on application restart, allowing configuration
    changes to take effect on the next deployment.
    
    Returns:
        Settings: Cached application configuration instance
    
    Thread Safety:
        functools.lru_cache is thread-safe in Python 3.x
    
    Usage:
        # Import pre-initialized settings (recommended)
        from app.config import settings
        
        # Or call function directly (less common)
        from app.config import get_settings
        config = get_settings()
    """
    return Settings()

# Global settings instance - use this throughout the application
settings = get_settings()