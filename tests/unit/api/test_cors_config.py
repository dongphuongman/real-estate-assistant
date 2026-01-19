import os

from config.settings import AppSettings


def test_dev_env_allows_all_origins():
    old_env = os.environ.get("ENVIRONMENT")
    try:
        os.environ["ENVIRONMENT"] = "development"
        if "CORS_ALLOW_ORIGINS" in os.environ:
            del os.environ["CORS_ALLOW_ORIGINS"]
        settings = AppSettings()
        assert settings.cors_allow_origins == ["*"]
    finally:
        if old_env is None:
            os.environ.pop("ENVIRONMENT", None)
        else:
            os.environ["ENVIRONMENT"] = old_env


def test_prod_env_pins_origins():
    old_env = os.environ.get("ENVIRONMENT")
    old_cors = os.environ.get("CORS_ALLOW_ORIGINS")
    try:
        os.environ["ENVIRONMENT"] = "production"
        os.environ["CORS_ALLOW_ORIGINS"] = "https://example.com, https://app.local"
        settings = AppSettings()
        assert settings.cors_allow_origins == ["https://example.com", "https://app.local"]
    finally:
        if old_env is None:
            os.environ.pop("ENVIRONMENT", None)
        else:
            os.environ["ENVIRONMENT"] = old_env
        if old_cors is None:
            os.environ.pop("CORS_ALLOW_ORIGINS", None)
        else:
            os.environ["CORS_ALLOW_ORIGINS"] = old_cors
