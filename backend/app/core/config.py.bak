import os
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "SchemeSahayak"
    API_V1_STR: str = "/api"

    # SECURITY: SECRET_KEY must be set via environment in production
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))  # 7 days default
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Optional AI / LLM Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    AI_MODEL_NAME: str = os.getenv("AI_MODEL_NAME", "gemini-1.5-flash")

    # CORS: Restrict to specific origins, never use wildcard in production
    CORS_ORIGINS_STR: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:5174,http://localhost:3000,http://localhost:8000"
    )
    BACKEND_CORS_ORIGINS: List[str] = [origin.strip() for origin in CORS_ORIGINS_STR.split(",")]

    ADMIN_EMAIL: str = "admin@schemesahayak.gov.in"
    ADMIN_PASSWORD: str = "AdminPassword@123"
    DEFAULT_ADMIN_EMAIL: str = "admin@schemesahayak.gov.in"
    DEFAULT_ADMIN_PASSWORD: str = "AdminPassword@123"

    # Debug mode
    DEBUG: bool = True

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=(".env", "backend/.env"),
        extra="ignore",
        env_file_encoding="utf-8",
    )
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.DATABASE_URL or self.DATABASE_URL == "sqlite:///./schemesahayak.db":
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            candidate_1 = os.path.join(os.path.dirname(backend_dir), "schemesahayak.db")
            candidate_2 = os.path.join(backend_dir, "schemesahayak.db")
            if os.path.exists(candidate_1) and os.path.getsize(candidate_1) > 100000:
                self.DATABASE_URL = f"sqlite:///{candidate_1.replace(os.sep, '/')}"
            elif os.path.exists(candidate_2) and os.path.getsize(candidate_2) > 100000:
                self.DATABASE_URL = f"sqlite:///{candidate_2.replace(os.sep, '/')}"
            elif os.path.exists(candidate_1):
                self.DATABASE_URL = f"sqlite:///{candidate_1.replace(os.sep, '/')}"
            else:
                self.DATABASE_URL = f"sqlite:///{candidate_2.replace(os.sep, '/')}"

        # Validate critical security variables in production
        if not self.DEBUG:
            if not self.SECRET_KEY:
                raise ValueError("SECRET_KEY environment variable is required for production")
            if not self.DEFAULT_ADMIN_EMAIL or not self.DEFAULT_ADMIN_PASSWORD:
                raise ValueError("ADMIN_EMAIL and ADMIN_PASSWORD environment variables are required for production")

settings = Settings()
