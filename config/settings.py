"""
Application settings and configuration.

This module provides centralized configuration management for the application.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    """Application settings."""

    # Application
    app_title: str = "AI Real Estate Assistant - Modern"
    app_icon: str = "🏠"
    version: str = "3.0.0"
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))

    # Paths
    data_dir: Path = Field(default_factory=lambda: Path("./data"))
    chroma_dir: Path = Field(default_factory=lambda: Path("./chroma_db"))
    assets_dir: Path = Field(default_factory=lambda: Path("./assets"))

    # API Keys (loaded from environment)
    openai_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY")
    )
    anthropic_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY")
    )
    google_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("GOOGLE_API_KEY")
    )
    grok_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("XAI_API_KEY")
    )
    deepseek_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("DEEPSEEK_API_KEY")
    )
    # API Access Control
    api_access_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("API_ACCESS_KEY", "dev-secret-key")
    )
    api_rate_limit_enabled: bool = Field(
        default_factory=lambda: os.getenv("API_RATE_LIMIT_ENABLED", "true").strip().lower()
        in {"1", "true", "yes", "on"}
    )
    api_rate_limit_rpm: int = Field(
        default_factory=lambda: int(os.getenv("API_RATE_LIMIT_RPM", "600"))
    )
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: (
            [o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "").split(",") if o.strip()]
            if os.getenv("ENVIRONMENT", "development").strip().lower() == "production"
            else ["*"]
        )
    )

    # Auth
    auth_email_enabled: bool = Field(
        default_factory=lambda: os.getenv("AUTH_EMAIL_ENABLED", "false").strip().lower()
        in {"1", "true", "yes", "on"}
    )
    auth_code_ttl_minutes: int = Field(
        default_factory=lambda: int(os.getenv("AUTH_CODE_TTL_MINUTES", "10"))
    )
    session_ttl_days: int = Field(
        default_factory=lambda: int(os.getenv("SESSION_TTL_DAYS", "30"))
    )
    auth_storage_dir: str = Field(
        default_factory=lambda: os.getenv("AUTH_STORAGE_DIR", ".auth")
    )

    # Model Defaults
    default_provider: str = Field(default="openai", description="Default LLM provider")
    default_model: Optional[str] = Field(default=None, description="Default model ID (overrides provider default)")
    default_temperature: float = 0.0
    default_max_tokens: int = 4096
    default_k_results: int = 5

    # Vector Store
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # RAG (Local Knowledge)
    rag_max_files: int = Field(default_factory=lambda: int(os.getenv("RAG_MAX_FILES", "10")))
    rag_max_file_bytes: int = Field(default_factory=lambda: int(os.getenv("RAG_MAX_FILE_BYTES", str(10 * 1024 * 1024))))
    rag_max_total_bytes: int = Field(default_factory=lambda: int(os.getenv("RAG_MAX_TOTAL_BYTES", str(25 * 1024 * 1024))))

    # Data Loading
    max_properties: int = 2000
    batch_size: int = 100
    autoload_default_datasets: bool = False
    vector_persist_enabled: bool = False
    crm_webhook_url: Optional[str] = Field(default_factory=lambda: os.getenv("CRM_WEBHOOK_URL"))
    valuation_mode: str = Field(default_factory=lambda: os.getenv("VALUATION_MODE", "simple"))
    legal_check_mode: str = Field(default_factory=lambda: os.getenv("LEGAL_CHECK_MODE", "basic"))
    data_enrichment_enabled: bool = Field(
        default_factory=lambda: os.getenv("DATA_ENRICHMENT_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    )

    # UI Settings
    page_layout: str = "wide"
    initial_sidebar_state: str = "expanded"

    # Dataset URLs
    default_datasets: list[str] = Field(
        default_factory=lambda: [
            "dataset/pl/apartments_rent_pl_2024_01.csv",
            "dataset/pl/apartments_rent_pl_2024_02.csv",
            "dataset/pl/apartments_rent_pl_2024_03.csv",
            "dataset/pl/apartments_rent_pl_2024_04.csv",
            "dataset/pl/apartments_rent_pl_2024_05.csv",
        ]
    )

    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = AppSettings()


def get_settings() -> AppSettings:
    """
    Get application settings.

    Returns:
        AppSettings instance
    """
    return settings


def update_api_key(provider: str, api_key: str) -> None:
    """
    Update API key for a provider.

    Args:
        provider: Provider name ('openai', 'anthropic', 'google', 'grok', 'deepseek')
        api_key: API key value
    """
    global settings

    if provider == "openai":
        settings.openai_api_key = api_key
        os.environ["OPENAI_API_KEY"] = api_key
    elif provider == "anthropic":
        settings.anthropic_api_key = api_key
        os.environ["ANTHROPIC_API_KEY"] = api_key
    elif provider == "google":
        settings.google_api_key = api_key
        os.environ["GOOGLE_API_KEY"] = api_key
    elif provider == "grok":
        settings.grok_api_key = api_key
        os.environ["XAI_API_KEY"] = api_key
    elif provider == "deepseek":
        settings.deepseek_api_key = api_key
        os.environ["DEEPSEEK_API_KEY"] = api_key

    # Clear provider cache to pick up new API key
    from models.provider_factory import ModelProviderFactory
    ModelProviderFactory.clear_cache()
    return None
