from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = Field(default="mysql+pymysql://root:@localhost:3306")
    DATABASE_API: str = Field(default="project_api_quangdev")
    DATABASE_PROJECT: str = Field(default="project_quangdev")
    DATABASE_API_URL: str | None = Field(default=None)
    DATABASE_PROJECT_URL: str | None = Field(default=None)
    API_KEY_HEADER_NAME: str = Field(default="x-api-key")
    LOG_LEVEL: str = Field(default="INFO")
    ENVIRONMENT: str = Field(default="development")
    API_PUBLIC: int = Field(default=3000)
    API_ADMIN: int = Field(default=8080)
    ADMIN_USERNAME: str = Field(...)
    ADMIN_PASSWORD: str = Field(...)
    ADMIN_SECRET_KEY: str = Field(...)
    FLASK_SESSION_SECRET: str = Field(...)
    JWT_SIGNING_SECRET: str = Field(...)
    LOG_FILE_PATH: str = Field(default="api_gateway.log")

    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    API_KEY_CACHE_TTL_SECONDS: int = Field(default=300)

    CORS_ALLOW_ORIGINS: str = Field(default="")
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    CORS_ALLOW_HEADERS: str = Field(default="Content-Type,Authorization,X-API-Key,X-Requested-With")
    SESSION_COOKIE_SECURE: bool = Field(default=False)
    SESSION_COOKIE_SAMESITE: str = Field(default="Lax")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def cors_allow_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ALLOW_ORIGINS.split(",") if origin.strip()]

    @property
    def cors_allow_headers(self) -> list[str]:
        return [header.strip() for header in self.CORS_ALLOW_HEADERS.split(",") if header.strip()]

    @property
    def database_api_url(self) -> str:
        if self.DATABASE_API_URL:
            return self.DATABASE_API_URL.strip()
        return f"{self.DATABASE_URL}/{self.DATABASE_API}"

    @property
    def database_project_url(self) -> str:
        if self.DATABASE_PROJECT_URL:
            return self.DATABASE_PROJECT_URL.strip()
        return f"{self.DATABASE_URL}/{self.DATABASE_PROJECT}"

    @property
    def jwt_issuer(self) -> str:
        return "api-gateway"

    @property
    def jwt_audience(self) -> str:
        return "user-api"

    @property
    def jwt_algorithm(self) -> str:
        return "HS256"

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"development", "staging", "production", "test"}:
            raise ValueError("ENVIRONMENT must be one of: development, staging, production, test")
        return normalized

    @field_validator("SESSION_COOKIE_SAMESITE")
    @classmethod
    def validate_samesite(cls, value: str) -> str:
        normalized = value.strip().capitalize()
        if normalized not in {"Lax", "Strict", "None"}:
            raise ValueError("SESSION_COOKIE_SAMESITE must be Lax, Strict, or None")
        return normalized

    @field_validator("ADMIN_USERNAME", "ADMIN_PASSWORD", "ADMIN_SECRET_KEY", "FLASK_SESSION_SECRET", "JWT_SIGNING_SECRET")
    @classmethod
    def validate_required_admin_settings(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Admin settings cannot be empty")
        return normalized

    @field_validator("ADMIN_SECRET_KEY", "FLASK_SESSION_SECRET", "JWT_SIGNING_SECRET")
    @classmethod
    def validate_admin_secret_key(cls, value: str) -> str:
        if value in {"change-me-admin-secret", "change-me", "secret", "dev", "default"}:
            raise ValueError("Secret settings cannot use insecure default values")
        return value

    @field_validator("API_KEY_CACHE_TTL_SECONDS")
    @classmethod
    def validate_cache_ttl(cls, value: int) -> int:
        if value < 1:
            raise ValueError("API_KEY_CACHE_TTL_SECONDS must be greater than 0")
        return value


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.is_production and not settings.SESSION_COOKIE_SECURE:
        raise ValueError("SESSION_COOKIE_SECURE must be true in production")
    if settings.is_production and not settings.cors_allow_origins:
        raise ValueError("CORS_ALLOW_ORIGINS must be configured in production")
    return settings


settings = get_settings()
