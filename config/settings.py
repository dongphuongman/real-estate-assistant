"""
Application settings and configuration.

This module provides centralized configuration management for the application.
"""

import os
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, root_validator


def _parse_csv_list(value: Optional[str]) -> list[str]:
    if not value:
        return []
    items = [item.strip() for item in value.split(",")]
    return [item for item in items if item]


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        deduped.append(value)
        seen.add(value)
    return deduped


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
    openai_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    anthropic_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    google_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GOOGLE_API_KEY"))
    grok_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("XAI_API_KEY"))
    deepseek_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY"))
    # API Access Control
    api_access_key: Optional[str] = Field(default_factory=lambda: os.getenv("API_ACCESS_KEY"))
    api_access_keys: list[str] = Field(
        default_factory=lambda: _parse_csv_list(os.getenv("API_ACCESS_KEYS"))
    )
    api_access_key_secondary: Optional[str] = Field(
        default_factory=lambda: os.getenv("API_ACCESS_KEY_SECONDARY")
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
    session_ttl_days: int = Field(default_factory=lambda: int(os.getenv("SESSION_TTL_DAYS", "30")))
    auth_storage_dir: str = Field(default_factory=lambda: os.getenv("AUTH_STORAGE_DIR", ".auth"))

    # Model Defaults
    default_provider: str = Field(
        default_factory=lambda: os.getenv("DEFAULT_PROVIDER", "openai").strip() or "openai",
        description="Default LLM provider",
    )
    default_model: Optional[str] = Field(
        default_factory=lambda: (os.getenv("DEFAULT_MODEL") or None),
        description="Default model ID (overrides provider default)",
    )
    default_temperature: float = 0.0
    default_max_tokens: int = 4096
    default_k_results: int = 5
    ollama_default_model: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.2:3b")
    )

    # Internet tools (optional, for demo/research)
    internet_enabled: bool = Field(
        default_factory=lambda: os.getenv("INTERNET_ENABLED", "false").strip().lower()
        in {"1", "true", "yes", "on"}
    )
    searxng_url: Optional[str] = Field(default_factory=lambda: os.getenv("SEARXNG_URL"))
    web_search_max_results: int = Field(
        default_factory=lambda: int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5"))
    )
    web_fetch_timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("WEB_FETCH_TIMEOUT_SECONDS", "10"))
    )
    web_fetch_max_bytes: int = Field(
        default_factory=lambda: int(os.getenv("WEB_FETCH_MAX_BYTES", str(300_000)))
    )
    web_allowlist_domains: list[str] = Field(
        default_factory=lambda: _parse_csv_list(os.getenv("WEB_ALLOWLIST_DOMAINS"))
    )

    # Chat (SSE sources payload safety)
    chat_sources_max_items: int = Field(
        default_factory=lambda: int(os.getenv("CHAT_SOURCES_MAX_ITEMS", "5"))
    )
    chat_source_content_max_chars: int = Field(
        default_factory=lambda: int(os.getenv("CHAT_SOURCE_CONTENT_MAX_CHARS", "2000"))
    )
    chat_sources_max_total_bytes: int = Field(
        default_factory=lambda: int(os.getenv("CHAT_SOURCES_MAX_TOTAL_BYTES", "20000"))
    )

    # Vector Store
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # RAG (Local Knowledge)
    rag_max_files: int = Field(default_factory=lambda: int(os.getenv("RAG_MAX_FILES", "10")))
    rag_max_file_bytes: int = Field(
        default_factory=lambda: int(os.getenv("RAG_MAX_FILE_BYTES", str(10 * 1024 * 1024)))
    )
    rag_max_total_bytes: int = Field(
        default_factory=lambda: int(os.getenv("RAG_MAX_TOTAL_BYTES", str(25 * 1024 * 1024)))
    )

    # Request Size Limits
    request_max_body_size_mb: int = Field(
        default_factory=lambda: int(os.getenv("REQUEST_MAX_BODY_SIZE_MB", "10"))
    )
    request_max_upload_size_mb: int = Field(
        default_factory=lambda: int(os.getenv("REQUEST_MAX_UPLOAD_SIZE_MB", "25"))
    )

    # Data Loading
    max_properties: int = 2000
    batch_size: int = 100
    autoload_default_datasets: bool = False
    vector_persist_enabled: bool = False
    crm_webhook_url: Optional[str] = Field(default_factory=lambda: os.getenv("CRM_WEBHOOK_URL"))
    valuation_mode: str = Field(default_factory=lambda: os.getenv("VALUATION_MODE", "simple"))
    legal_check_mode: str = Field(default_factory=lambda: os.getenv("LEGAL_CHECK_MODE", "basic"))
    data_enrichment_enabled: bool = Field(
        default_factory=lambda: os.getenv("DATA_ENRICHMENT_ENABLED", "false").strip().lower()
        in {"1", "true", "yes", "on"}
    )

    # UI Settings
    page_layout: str = "wide"
    initial_sidebar_state: str = "expanded"

    # Dataset URLs
    default_datasets: list[str] = Field(
        default_factory=lambda: _parse_csv_list(os.getenv("DEFAULT_DATASETS"))
    )

    class Config:
        """Pydantic config."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @root_validator(skip_on_failure=True)
    def _normalize_api_access_keys(
        cls: type["AppSettings"], values: dict[str, Any]
    ) -> dict[str, Any]:
        raw_primary = values.get("api_access_key")
        primary = raw_primary.strip() if isinstance(raw_primary, str) else None
        if not primary:
            primary = None

        normalized_keys: list[str] = []
        for raw_key in values.get("api_access_keys") or []:
            if not isinstance(raw_key, str):
                continue
            key = raw_key.strip()
            if not key:
                continue
            normalized_keys.append(key)

        # Include secondary key for rotation support
        raw_secondary = values.get("api_access_key_secondary")
        secondary = raw_secondary.strip() if isinstance(raw_secondary, str) else None
        if secondary:
            normalized_keys.append(secondary)

        keys = _dedupe_preserve_order(normalized_keys)

        # If no keys from api_access_keys list, use primary as first key
        if not keys and primary:
            keys = [primary]
        # If we only have secondary key but also have primary, prepend primary
        if keys and primary and primary not in keys:
            keys = [primary] + keys

        keys = _dedupe_preserve_order(keys)

        # SECURITY: No default API key fallback. All environments require explicit key.
        # This prevents accidental deployment without proper authentication.
        values["api_access_keys"] = keys
        values["api_access_key"] = keys[0] if keys else None
        return values

    @root_validator(skip_on_failure=True)
    def _validate_cors_production_safety(
        cls: type["AppSettings"], values: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Validate CORS configuration for production safety.

        In production, this validator:
        - Rejects wildcard '*' origins (too permissive)
        - Rejects empty origins list (must specify allowed domains)

        This prevents accidental deployment with overly permissive CORS configuration.
        """
        environment = (values.get("environment") or "development").strip().lower()
        cors_origins = values.get("cors_allow_origins") or []

        if environment == "production":
            # Reject wildcard in production
            if "*" in cors_origins:
                raise ValueError(
                    "CORS_ALLOW_ORIGINS cannot contain wildcard '*' in production. "
                    "Set specific origins (e.g., 'https://yourapp.com')."
                )
            # Reject empty origins in production
            if not cors_origins:
                raise ValueError(
                    "CORS_ALLOW_ORIGINS must be set in production. "
                    "Set specific origins (e.g., 'CORS_ALLOW_ORIGINS=https://yourapp.com')."
                )

        return values


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
