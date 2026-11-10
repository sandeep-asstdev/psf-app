"""
================================================================================
FILE PURPOSE: Application Configuration & Environment Settings.
This file reads environment variables from your system and the .env file,
validates them using Pydantic Settings, and provides a single global 'settings'
object used everywhere in the backend (DB URLs, Redis, MinIO keys, JWT secrets).

KEY RESPONSIBILITIES:
- Loads database connection strings (Postgres asyncpg & sync psycopg2).
- Configures Redis URL and worker concurrency limits.
- Stores security keys: SECRET_KEY for JWT tokens and FIELD_ENCRYPTION_KEY for phone numbers.
- Defines CORS allowed origins so the frontend at localhost:5173 can call the API.
- Sets storage bucket names for MinIO S3 document storage.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: ValidationError: 1 validation error for Settings -> FIELD_ENCRYPTION_KEY / SECRET_KEY
  -> Cause: Required security keys are missing or not 32 URL-safe base64 characters in your .env file.
  -> What should you do: Open .env and ensure SECRET_KEY and FIELD_ENCRYPTION_KEY are set properly. You can generate a 32-byte key using `python -c 'import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())'`.
- Error: ValidationError: DATABASE_URL not found or invalid format
  -> Cause: Database connection URL is missing in environment variables.
  -> What should you do: Check your .env file and ensure POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, and DATABASE_URL are present.
================================================================================
"""
import os
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "PSF SaaS Platform"
    APP_ENV: str = "development"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = "psf-super-secret-jwt-and-crypto-signing-key-change-in-production-min32chars"
    # 32-byte url-safe base64 key for Fernet / AES-256 PII encryption
    ENCRYPTION_KEY: str = "tU43o8_W12nEa9Q_bJv8hWvQ6k5Fz4pL3y8K1_bE7wQ="
    API_V1_STR: str = "/api/v1"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return []

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://psf_admin:psf_secure_password_dev@localhost:5432/psf_db"
    SYNC_DATABASE_URL: str = "postgresql://psf_admin:psf_secure_password_dev@localhost:5432/psf_db"

    @field_validator("DATABASE_URL", mode="before")
    def assemble_async_db_url(cls, v: str) -> str:
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Authentication
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: str = ""

    # Storage (MinIO / S3)
    STORAGE_BACKEND: str = "minio"
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_DOCUMENTS: str = "psf-documents"
    S3_BUCKET_EXPORTS: str = "psf-exports"
    S3_REGION: str = "us-east-1"
    S3_SECURE: bool = False

    # Worker
    WORKER_CONCURRENCY: int = 4
    MAX_BULK_IMPORT_ROWS: int = 50000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
