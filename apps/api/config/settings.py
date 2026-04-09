"""
Application settings and configuration.

This module provides centralized configuration management for the application.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from config.port_config import get_frontend_url_for_settings


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
    version: str = "4.0.0"
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
    zai_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("ZAI_API_KEY"),
        description="ZAI (Zhipu AI) API key - Chinese LLM provider with free tier",
    )
    moonshot_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("MOONSHOT_API_KEY"),
        description="Moonshot AI (Kimi) API key - Chinese LLM provider with long context",
    )
    # Google Routes API for commute time analysis (TASK-021)
    google_routes_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("GOOGLE_ROUTES_API_KEY"),
        description="API key for Google Routes API (commute time calculations)",
    )
    google_routes_enabled: bool = Field(
        default_factory=lambda: (
            os.getenv("GOOGLE_ROUTES_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
        ),
        description="Enable Google Routes API for commute time analysis",
    )

    # VAPID keys for Web Push notifications (Task #63)
    vapid_public_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("VAPID_PUBLIC_KEY"),
        description="VAPID public key for web push (base64url encoded)",
    )
    vapid_private_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("VAPID_PRIVATE_KEY"),
        description="VAPID private key for web push",
    )
    vapid_subject: str = Field(
        default_factory=lambda: os.getenv("VAPID_SUBJECT", "mailto:noreply@example.com"),
        description="VAPID subject (contact email or URL)",
    )
    push_enabled: bool = Field(
        default_factory=lambda: (
            os.getenv("PUSH_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
        ),
        description="Enable push notifications",
    )

    # API Access Control
    api_access_key: Optional[str] = Field(default_factory=lambda: os.getenv("API_ACCESS_KEY"))
    api_access_keys: list[str] = Field(
        default_factory=lambda: _parse_csv_list(os.getenv("API_ACCESS_KEYS"))
    )
    api_access_key_secondary: Optional[str] = Field(
        default_factory=lambda: os.getenv("API_ACCESS_KEY_SECONDARY")
    )
    api_rate_limit_enabled: bool = Field(
        default_factory=lambda: (
            os.getenv("API_RATE_LIMIT_ENABLED", "true").strip().lower()
            in {"1", "true", "yes", "on"}
        )
    )
    api_rate_limit_rpm: int = Field(
        default_factory=lambda: int(os.getenv("API_RATE_LIMIT_RPM", "600"))
    )

    # Filter preset limits (Task #75)
    max_filter_presets_per_user: int = Field(
        default=20,
        description="Maximum number of filter presets per user",
    )

    cors_allow_origins: list[str] = Field(
        default_factory=lambda: (
            [o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "").split(",") if o.strip()]
            if os.getenv("ENVIRONMENT", "development").strip().lower() == "production"
            else ["*"]
        )
    )

    # Auth (Legacy - Email Code Auth)
    auth_email_enabled: bool = Field(
        default_factory=lambda: (
            os.getenv("AUTH_EMAIL_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
        )
    )
    auth_code_ttl_minutes: int = Field(
        default_factory=lambda: int(os.getenv("AUTH_CODE_TTL_MINUTES", "10"))
    )
    session_ttl_days: int = Field(default_factory=lambda: int(os.getenv("SESSION_TTL_DAYS", "30")))
    auth_storage_dir: str = Field(default_factory=lambda: os.getenv("AUTH_STORAGE_DIR", ".auth"))

    # JWT Authentication
    jwt_secret_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("JWT_SECRET_KEY"),
        description="Secret key for JWT token signing (required in production)",
    )
    jwt_algorithm: str = Field(
        default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"),
        description="JWT signing algorithm",
    )
    jwt_access_token_expire_minutes: int = Field(
        default_factory=lambda: int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15")),
        description="Access token expiration time in minutes",
    )
    jwt_refresh_token_expire_days: int = Field(
        default_factory=lambda: int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")),
        description="Refresh token expiration time in days",
    )

    # Account Lockout (Task #47: Auth Security Hardening)
    auth_lockout_max_attempts: int = Field(
        default_factory=lambda: int(os.getenv("AUTH_LOCKOUT_MAX_ATTEMPTS", "5")),
        description="Maximum failed login attempts before account lockout",
    )
    auth_lockout_duration_minutes: int = Field(
        default_factory=lambda: int(os.getenv("AUTH_LOCKOUT_DURATION_MINUTES", "15")),
        description="Account lockout duration in minutes",
    )

    # Database
    database_url: Optional[str] = Field(
        default_factory=lambda: os.getenv("DATABASE_URL"),
        description="Database connection URL (defaults to SQLite if not set)",
    )

    # OAuth - Google
    google_client_id: Optional[str] = Field(
        default_factory=lambda: os.getenv("GOOGLE_CLIENT_ID"),
        description="Google OAuth client ID",
    )
    google_client_secret: Optional[str] = Field(
        default_factory=lambda: os.getenv("GOOGLE_CLIENT_SECRET"),
        description="Google OAuth client secret",
    )
    google_redirect_uri: Optional[str] = Field(
        default_factory=lambda: os.getenv("GOOGLE_REDIRECT_URI"),
        description="Google OAuth redirect URI",
    )

    # OAuth - Apple (optional)
    apple_client_id: Optional[str] = Field(
        default_factory=lambda: os.getenv("APPLE_CLIENT_ID"),
        description="Apple Sign-In client ID (services identifier)",
    )
    apple_team_id: Optional[str] = Field(
        default_factory=lambda: os.getenv("APPLE_TEAM_ID"),
        description="Apple Developer Team ID",
    )
    apple_key_id: Optional[str] = Field(
        default_factory=lambda: os.getenv("APPLE_KEY_ID"),
        description="Apple Sign-In key ID",
    )
    apple_private_key_path: Optional[str] = Field(
        default_factory=lambda: os.getenv("APPLE_PRIVATE_KEY_PATH"),
        description="Path to Apple Sign-In private key file (.p8)",
    )

    # Email Settings
    email_provider: str = Field(
        default_factory=lambda: os.getenv("EMAIL_PROVIDER", "console"),
        description="Email provider: console (dev) or smtp (production)",
    )
    email_from_address: str = Field(
        default_factory=lambda: os.getenv("EMAIL_FROM_ADDRESS", "noreply@example.com"),
        description="Default sender email address",
    )
    smtp_host: Optional[str] = Field(
        default_factory=lambda: os.getenv("SMTP_HOST"),
        description="SMTP server hostname",
    )
    smtp_port: int = Field(
        default_factory=lambda: int(os.getenv("SMTP_PORT", "587")),
        description="SMTP server port",
    )
    smtp_username: Optional[str] = Field(
        default_factory=lambda: os.getenv("SMTP_USERNAME"),
        description="SMTP authentication username",
    )
    smtp_password: Optional[str] = Field(
        default_factory=lambda: os.getenv("SMTP_PASSWORD"),
        description="SMTP authentication password",
    )
    smtp_use_tls: bool = Field(
        default_factory=lambda: (
            os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "on"}
        ),
        description="Use TLS for SMTP connection",
    )

    # Frontend URL (for email links)
    # Uses port_config for dynamic port allocation support
    frontend_url: str = Field(
        default_factory=lambda: os.getenv("FRONTEND_URL") or get_frontend_url_for_settings(),
        description="Frontend URL for email links (verification, password reset)",
    )

    # Feature Flags
    auth_jwt_enabled: bool = Field(
        default_factory=lambda: (
            os.getenv("AUTH_JWT_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
        ),
        description="Enable JWT-based authentication",
    )
    auth_registration_enabled: bool = Field(
        default_factory=lambda: (
            os.getenv("AUTH_REGISTRATION_ENABLED", "true").strip().lower()
            in {"1", "true", "yes", "on"}
        ),
        description="Allow new user registration",
    )
    auth_email_verification_required: bool = Field(
        default_factory=lambda: (
            os.getenv("AUTH_EMAIL_VERIFICATION_REQUIRED", "true").strip().lower()
            in {"1", "true", "yes", "on"}
        ),
        description="Require email verification before account activation",
    )
    auth_oauth_google_enabled: bool = Field(
        default_factory=lambda: (
            os.getenv("AUTH_OAUTH_GOOGLE_ENABLED", "false").strip().lower()
            in {"1", "true", "yes", "on"}
        ),
        description="Enable Google OAuth login",
    )
    auth_oauth_apple_enabled: bool = Field(
        default_factory=lambda: (
            os.getenv("AUTH_OAUTH_APPLE_ENABLED", "false").strip().lower()
            in {"1", "true", "yes", "on"}
        ),
        description="Enable Apple Sign-In",
    )

    # Model Defaults
    default_provider: str = Field(
        default_factory=lambda: os.getenv("DEFAULT_PROVIDER", "openai").strip() or "openai",
        description="Default LLM provider",
    )
    default_model: Optional[str] = Field(
        default_factory=lambda: os.getenv("DEFAULT_MODEL") or None,
        description="Default model ID (overrides provider default)",
    )
    default_temperature: float = 0.0
    default_max_tokens: int = 4096
    default_k_results: int = 5

    # LLM Request Timeouts
    llm_request_timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "120")),
        description="Timeout in seconds for LLM API requests (default: 120s)",
    )
    llm_connect_timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("LLM_CONNECT_TIMEOUT_SECONDS", "30")),
        description="Timeout in seconds for connecting to LLM APIs (default: 30s)",
    )
    ollama_default_model: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.2:3b")
    )

    # Internet tools (optional, for demo/research)
    internet_enabled: bool = Field(
        default_factory=lambda: (
            os.getenv("INTERNET_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
        )
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

    # Response Caching (TASK-017: Production Deployment Optimization)
    cache_enabled: bool = Field(
        default_factory=lambda: (
            os.getenv("CACHE_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
        )
    )
    cache_ttl_seconds: int = Field(
        default_factory=lambda: int(os.getenv("CACHE_TTL_SECONDS", "300"))
    )
    cache_redis_url: Optional[str] = Field(
        default_factory=lambda: os.getenv("CACHE_REDIS_URL") or os.getenv("REDIS_URL")
    )
    cache_prefix: str = Field(default_factory=lambda: os.getenv("CACHE_PREFIX", "api_cache"))
    cache_max_memory_mb: int = Field(
        default_factory=lambda: int(os.getenv("CACHE_MAX_MEMORY_MB", "100"))
    )
    cache_stale_while_revalidate: bool = Field(
        default_factory=lambda: (
            os.getenv("CACHE_STALE_WHILE_REVALIDATE", "false").strip().lower()
            in {"1", "true", "yes", "on"}
        )
    )

    # Performance Monitoring (TASK-017: Production Deployment Optimization)
    metrics_enabled: bool = Field(
        default_factory=lambda: (
            os.getenv("METRICS_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
        )
    )
    metrics_path: str = Field(default_factory=lambda: os.getenv("METRICS_PATH", "/metrics"))
    prometheus_enabled: bool = Field(
        default_factory=lambda: (
            os.getenv("PROMETHEUS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
        )
    )

    # Database Connection Pooling (TASK-017: Production Deployment Optimization)
    db_pool_size: int = Field(default_factory=lambda: int(os.getenv("DB_POOL_SIZE", "10")))
    db_max_overflow: int = Field(default_factory=lambda: int(os.getenv("DB_MAX_OVERFLOW", "20")))
    db_pool_timeout_seconds: int = Field(
        default_factory=lambda: int(os.getenv("DB_POOL_TIMEOUT_SECONDS", "30"))
    )
    db_pool_recycle_seconds: int = Field(
        default_factory=lambda: int(os.getenv("DB_POOL_RECYCLE_SECONDS", "3600"))
    )

    # Sentry Error Tracking & APM (Task #56)
    sentry_dsn: Optional[str] = Field(default_factory=lambda: os.getenv("SENTRY_DSN"))
    sentry_traces_sample_rate: float = Field(
        default_factory=lambda: float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.2"))
    )
    sentry_environment: str = Field(
        default_factory=lambda: os.getenv(
            "SENTRY_ENVIRONMENT", os.getenv("ENVIRONMENT", "development")
        )
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
        default_factory=lambda: (
            os.getenv("DATA_ENRICHMENT_ENABLED", "false").strip().lower()
            in {"1", "true", "yes", "on"}
        )
    )

    # UI Settings
    page_layout: str = "wide"
    initial_sidebar_state: str = "expanded"

    # Dataset URLs
    default_datasets: list[str] = Field(
        default_factory=lambda: _parse_csv_list(os.getenv("DEFAULT_DATASETS"))
    )

    # =============================================================================
    # E-Signature Integration (Task #57)
    # =============================================================================
    hellosign_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("HELLOSIGN_API_KEY"),
        description="HelloSign (Dropbox Sign) API key",
    )
    hellosign_client_id: Optional[str] = Field(
        default_factory=lambda: os.getenv("HELLOSIGN_CLIENT_ID"),
        description="HelloSign OAuth client ID (for embedded signing)",
    )
    hellosign_webhook_secret: Optional[str] = Field(
        default_factory=lambda: os.getenv("HELLOSIGN_WEBHOOK_SECRET"),
        description="Secret for verifying HelloSign webhook signatures",
    )
    esignature_provider: str = Field(
        default_factory=lambda: os.getenv("ESIGNATURE_PROVIDER", "hellosign"),
        description="E-signature provider (hellosign, docusign)",
    )
    esignature_enabled: bool = Field(
        default_factory=lambda: (
            os.getenv("ESIGNATURE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
        ),
        description="Enable e-signature functionality",
    )
    esignature_default_expiry_days: int = Field(
        default_factory=lambda: int(os.getenv("ESIGNATURE_DEFAULT_EXPIRY_DAYS", "30")),
        description="Default days until signature request expires",
    )
    esignature_reminder_enabled: bool = Field(
        default_factory=lambda: (
            os.getenv("ESIGNATURE_REMINDER_ENABLED", "true").strip().lower()
            in {"1", "true", "yes", "on"}
        ),
        description="Enable automatic reminders for pending signatures",
    )

    # =============================================================================
    # MCP Connector Settings (Task #64)
    # =============================================================================
    mcp_edition: str = Field(
        default_factory=lambda: os.getenv("MCP_EDITION", "community"),
        description="MCP edition: community, pro, or enterprise",
    )
    mcp_allowlist: list[str] = Field(
        default_factory=lambda: _parse_csv_list(os.getenv("MCP_ALLOWLIST")),
        description="Comma-separated list of allowlisted connectors for CE",
    )
    mcp_enabled: bool = Field(
        default_factory=lambda: (
            os.getenv("MCP_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
        ),
        description="Enable MCP connector functionality",
    )
    mcp_default_timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("MCP_DEFAULT_TIMEOUT_SECONDS", "30")),
        description="Default timeout for MCP operations",
    )
    mcp_pool_max_connections: int = Field(
        default_factory=lambda: int(os.getenv("MCP_POOL_MAX_CONNECTIONS", "10")),
        description="Maximum connections per connector pool",
    )
    mcp_data_minimization_enabled: bool = Field(
        default_factory=lambda: (
            os.getenv("MCP_DATA_MINIMIZATION_ENABLED", "true").strip().lower()
            in {"1", "true", "yes", "on"}
        ),
        description="Enable PII stripping for MCP requests",
    )

    # =============================================================================
    # =============================================================================
    # Property Enrichment Settings (Task #78)
    # =============================================================================
    enrichment_enabled: bool = Field(
        default_factory=lambda: (
            os.getenv("ENRICHMENT_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
        ),
        description="Enable property data enrichment from external sources",
    )
    enrichment_default_ttl: int = Field(
        default_factory=lambda: int(os.getenv("ENRICHMENT_DEFAULT_TTL", "3600")),
        description="Default TTL for enrichment cache in seconds",
    )
    enrichment_parallel_execution: bool = Field(
        default_factory=lambda: (
            os.getenv("ENRICHMENT_PARALLEL_EXECUTION", "true").strip().lower()
            in {"1", "true", "yes", "on"}
        ),
        description="Run enrichers in parallel",
    )
    enrichment_max_concurrent: int = Field(
        default_factory=lambda: int(os.getenv("ENRICHMENT_MAX_CONCURRENT", "5")),
        description="Maximum concurrent enrichers",
    )
    enrichment_timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("ENRICHMENT_TIMEOUT_SECONDS", "30")),
        description="Default timeout for enrichment operations",
    )
    enrichment_sources: list[str] = Field(
        default_factory=lambda: _parse_csv_list(os.getenv("ENRICHMENT_SOURCES")),
        description="Comma-separated list of enabled enrichment sources (empty = all)",
    )
    enrichment_cache_enabled: bool = Field(
        default_factory=lambda: (
            os.getenv("ENRICHMENT_CACHE_ENABLED", "true").strip().lower()
            in {"1", "true", "yes", "on"}
        ),
        description="Enable caching for enrichment results",
    )
    enrichment_fallback_on_error: bool = Field(
        default_factory=lambda: (
            os.getenv("ENRICHMENT_FALLBACK_ON_ERROR", "true").strip().lower()
            in {"1", "true", "yes", "on"}
        ),
        description="Use fallback values when enrichment fails",
    )

    # =============================================================================
    # Context Window Management (Task #73)
    # =============================================================================
    context_max_utilization_percent: int = Field(
        default_factory=lambda: int(os.getenv("CONTEXT_MAX_UTILIZATION_PERCENT", "75")),
        description="Max context window utilization before optimization (default 75%)",
    )
    context_sliding_window_messages: int = Field(
        default_factory=lambda: int(os.getenv("CONTEXT_SLIDING_WINDOW_MESSAGES", "50")),
        description="Number of recent messages to keep in sliding window",
    )
    context_summarization_threshold_percent: int = Field(
        default_factory=lambda: int(os.getenv("CONTEXT_SUMMARIZATION_THRESHOLD_PERCENT", "80")),
        description="Trigger summarization when context exceeds this percentage",
    )
    context_compression_enabled: bool = Field(
        default_factory=lambda: (
            os.getenv("CONTEXT_COMPRESSION_ENABLED", "true").strip().lower()
            in {"1", "true", "yes", "on"}
        ),
        description="Enable compression of repeated content in context",
    )
    context_metrics_enabled: bool = Field(
        default_factory=lambda: (
            os.getenv("CONTEXT_METRICS_ENABLED", "true").strip().lower()
            in {"1", "true", "yes", "on"}
        ),
        description="Enable context usage metrics logging",
    )
    context_priority_system_weight: float = Field(
        default_factory=lambda: float(os.getenv("CONTEXT_PRIORITY_SYSTEM_WEIGHT", "1.0")),
        description="Weight for system messages in priority selection (0.0-1.0)",
    )
    context_priority_recent_weight: float = Field(
        default_factory=lambda: float(os.getenv("CONTEXT_PRIORITY_RECENT_WEIGHT", "0.8")),
        description="Weight decay factor for older messages in priority selection",
    )

    # =============================================================================
    # Streaming Settings (Task #74: Response Streaming Improvements)
    # =============================================================================
    stream_heartbeat_interval_seconds: int = Field(
        default_factory=lambda: int(os.getenv("STREAM_HEARTBEAT_INTERVAL_SECONDS", "15")),
        description="Interval in seconds between SSE heartbeat comments",
    )
    stream_timeout_seconds: int = Field(
        default_factory=lambda: int(os.getenv("STREAM_TIMEOUT_SECONDS", "300")),
        description="Maximum duration in seconds for streaming responses",
    )
    stream_backoff_initial_ms: int = Field(
        default_factory=lambda: int(os.getenv("STREAM_BACKOFF_INITIAL_MS", "1000")),
        description="Initial backoff delay in milliseconds for reconnection",
    )
    stream_backoff_max_ms: int = Field(
        default_factory=lambda: int(os.getenv("STREAM_BACKOFF_MAX_MS", "30000")),
        description="Maximum backoff delay in milliseconds for reconnection",
    )
    stream_backoff_multiplier: float = Field(
        default_factory=lambda: float(os.getenv("STREAM_BACKOFF_MULTIPLIER", "2.0")),
        description="Exponential backoff multiplier for reconnection",
    )
    stream_max_retries: int = Field(
        default_factory=lambda: int(os.getenv("STREAM_MAX_RETRIES", "10")),
        description="Maximum reconnection attempts before giving up",
    )
    stream_metrics_enabled: bool = Field(
        default_factory=lambda: (
            os.getenv("STREAM_METRICS_ENABLED", "true").strip().lower()
            in {"1", "true", "yes", "on"}
        ),
        description="Enable streaming metrics collection",
    )
    stream_degradation_threshold: int = Field(
        default_factory=lambda: int(os.getenv("STREAM_DEGRADATION_THRESHOLD", "3")),
        description="Consecutive failures before degrading to non-streaming mode",
    )

    class Config:
        """Pydantic config."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @model_validator(mode="after")
    def _normalize_api_access_keys(self) -> "AppSettings":
        raw_primary = self.api_access_key
        primary = raw_primary.strip() if isinstance(raw_primary, str) else None
        if not primary:
            primary = None

        normalized_keys: list[str] = []
        for raw_key in self.api_access_keys or []:
            if not isinstance(raw_key, str):
                continue
            key = raw_key.strip()
            if not key:
                continue
            normalized_keys.append(key)

        # Include secondary key for rotation support
        raw_secondary = self.api_access_key_secondary
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
        self.api_access_keys = keys
        self.api_access_key = keys[0] if keys else None
        return self

    @model_validator(mode="after")
    def _validate_cors_production_safety(self) -> "AppSettings":
        """
        Validate CORS configuration for production safety.

        In production, this validator:
        - Rejects wildcard '*' origins (too permissive)
        - Rejects empty origins list (must specify allowed domains)

        This prevents accidental deployment with overly permissive CORS configuration.
        """
        environment = (self.environment or "development").strip().lower()
        cors_origins = self.cors_allow_origins or []

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

        return self


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
        provider: Provider name ('openai', 'anthropic', 'google', 'grok', 'deepseek', 'zai', 'moonshot')
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
    elif provider == "zai":
        settings.zai_api_key = api_key
        os.environ["ZAI_API_KEY"] = api_key
    elif provider == "moonshot":
        settings.moonshot_api_key = api_key
        os.environ["MOONSHOT_API_KEY"] = api_key

    # Clear provider cache to pick up new API key
    from models.provider_factory import ModelProviderFactory

    ModelProviderFactory.clear_cache()

    # Clear LLM instance cache so new keys take effect
    from api.dependencies import _create_llm_with_resolved_model_id

    _create_llm_with_resolved_model_id.cache_clear()
    return None
