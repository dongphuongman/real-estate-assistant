"""
Unit tests for Moonshot AI (Kimi) model provider.
"""

import os
from unittest.mock import patch

import pytest

from models.providers.base import ModelCapability
from models.providers.moonshot import MOONSHOT_BASE_URL, MoonshotProvider


class TestMoonshotProvider:
    """Tests for MoonshotProvider class."""

    def test_provider_has_correct_name(self):
        """Test that provider name is 'moonshot'."""
        provider = MoonshotProvider()
        assert provider.name == "moonshot"

    def test_provider_has_correct_display_name(self):
        """Test that display name is 'Moonshot AI (Kimi)'."""
        provider = MoonshotProvider()
        assert provider.display_name == "Moonshot AI (Kimi)"

    def test_provider_requires_api_key(self):
        """Test that provider requires an API key."""
        provider = MoonshotProvider()
        assert provider.requires_api_key is True

    def test_provider_is_not_local(self):
        """Test that provider is not local."""
        provider = MoonshotProvider()
        assert provider.is_local is False

    def test_provider_lists_models(self):
        """Test that provider lists available models."""
        provider = MoonshotProvider()
        models = provider.list_models()

        assert len(models) >= 3
        model_ids = [m.id for m in models]
        assert "moonshot-v1-8k" in model_ids
        assert "moonshot-v1-32k" in model_ids
        assert "moonshot-v1-128k" in model_ids

    def test_models_have_correct_context_windows(self):
        """Test that models have correct context windows."""
        provider = MoonshotProvider()

        model_8k = provider.get_model_info("moonshot-v1-8k")
        model_32k = provider.get_model_info("moonshot-v1-32k")
        model_128k = provider.get_model_info("moonshot-v1-128k")

        assert model_8k is not None
        assert model_8k.context_window == 8_000

        assert model_32k is not None
        assert model_32k.context_window == 32_000

        assert model_128k is not None
        assert model_128k.context_window == 128_000

    def test_models_have_capabilities(self):
        """Test that all models have required capabilities."""
        provider = MoonshotProvider()
        models = provider.list_models()

        for model in models:
            assert ModelCapability.STREAMING in model.capabilities
            assert ModelCapability.FUNCTION_CALLING in model.capabilities
            assert ModelCapability.JSON_MODE in model.capabilities
            assert ModelCapability.SYSTEM_MESSAGES in model.capabilities

    def test_models_have_pricing(self):
        """Test that all models have pricing information."""
        provider = MoonshotProvider()
        models = provider.list_models()

        for model in models:
            assert model.pricing is not None
            assert model.pricing.input_price_per_1m > 0
            assert model.pricing.output_price_per_1m > 0

    def test_pricing_scales_with_context(self):
        """Test that pricing scales with context window size."""
        provider = MoonshotProvider()

        model_8k = provider.get_model_info("moonshot-v1-8k")
        model_32k = provider.get_model_info("moonshot-v1-32k")
        model_128k = provider.get_model_info("moonshot-v1-128k")

        # 8K should be cheapest, 128K should be most expensive
        assert model_8k.pricing.input_price_per_1m < model_32k.pricing.input_price_per_1m
        assert model_32k.pricing.input_price_per_1m < model_128k.pricing.input_price_per_1m

    def test_models_have_recommendations(self):
        """Test that models have recommended use cases."""
        provider = MoonshotProvider()
        models = provider.list_models()

        for model in models:
            assert len(model.recommended_for) > 0

    def test_get_model_info_returns_none_for_invalid_model(self):
        """Test that get_model_info returns None for invalid model ID."""
        provider = MoonshotProvider()
        model = provider.get_model_info("invalid-model-id")
        assert model is None

    def test_create_model_raises_error_without_api_key(self):
        """Test that create_model raises error without API key."""
        provider = MoonshotProvider(config={})

        with pytest.raises(RuntimeError) as exc_info:
            provider.create_model("moonshot-v1-8k")

        assert "API key" in str(exc_info.value)

    def test_create_model_raises_error_for_invalid_model(self):
        """Test that create_model raises error for invalid model ID."""
        provider = MoonshotProvider(config={"api_key": "test-key"})

        with pytest.raises(ValueError) as exc_info:
            provider.create_model("invalid-model")

        assert "not available" in str(exc_info.value)

    def test_validate_connection_fails_without_api_key(self):
        """Test that validate_connection fails without API key."""
        provider = MoonshotProvider(config={})
        is_valid, error = provider.validate_connection()

        assert is_valid is False
        assert "API key" in error

    def test_default_base_url(self):
        """Test that default base URL is set correctly."""
        provider = MoonshotProvider()
        assert provider.config.get("base_url") == MOONSHOT_BASE_URL
        assert "api.moonshot.cn" in provider.config.get("base_url", "")

    def test_api_key_from_environment(self):
        """Test that API key is loaded from environment."""
        with patch.dict(os.environ, {"MOONSHOT_API_KEY": "test-env-key"}):
            provider = MoonshotProvider()
            assert provider.get_api_key() == "test-env-key"

    def test_api_key_from_config(self):
        """Test that API key from config takes precedence."""
        provider = MoonshotProvider(config={"api_key": "config-key"})
        assert provider.get_api_key() == "config-key"

    def test_custom_base_url(self):
        """Test that custom base URL can be set."""
        provider = MoonshotProvider(config={"base_url": "https://custom.api.url"})
        assert provider.config.get("base_url") == "https://custom.api.url"


@pytest.mark.skipif(
    not os.getenv("MOONSHOT_API_KEY"),
    reason="MOONSHOT_API_KEY not set - skipping integration tests",
)
class TestMoonshotProviderIntegration:
    """Integration tests for MoonshotProvider (requires API key)."""

    def test_create_model_with_valid_key(self):
        """Test that model can be created with valid API key."""
        provider = MoonshotProvider()
        model = provider.create_model("moonshot-v1-8k", max_tokens=10)

        assert model is not None
        assert model.model_name == "moonshot-v1-8k"

    def test_validate_connection_with_valid_key(self):
        """Test that connection is valid with correct API key."""
        provider = MoonshotProvider()
        is_valid, error = provider.validate_connection()

        assert is_valid is True
        assert error is None
