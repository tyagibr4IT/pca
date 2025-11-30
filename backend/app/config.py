# Reasonable assumption: Using env vars in .env for local dev, Key Vault in prod.
import os
from functools import lru_cache
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: str = "8000"
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    KEYVAULT_NAME: str = None
    OPENAI_API_TYPE: str = "openai"
    OPENAI_API_KEY: str = None
    AZURE_OPENAI_ENDPOINT: str = None
    AZURE_OPENAI_KEY: str = None
    AZURE_SEARCH_ENDPOINT: str = None
    AZURE_SEARCH_KEY: str = None

    AZURE_AD_TENANT_ID: str = None
    AZURE_AD_CLIENT_ID: str = None
    AZURE_AD_CLIENT_SECRET: str = None

    JWT_SECRET: str = Field(default="change-me", env="JWT_SECRET")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()