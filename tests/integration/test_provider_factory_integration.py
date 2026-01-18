from unittest.mock import patch

import pytest

from models.provider_factory import ModelProviderFactory


@pytest.fixture
def mock_settings_env():
    with patch("config.settings.os.getenv") as mock_getenv:
        def get_env(key, default=None):
            if key == "OPENAI_API_KEY":
                return "sk-test-openai"
            if key == "ANTHROPIC_API_KEY":
                return "sk-ant-test"
            if key == "GOOGLE_API_KEY":
                return "AIza-test"
            return default
        mock_getenv.side_effect = get_env
        
        # Reload settings or just patch the instance used by factory
        with patch("models.provider_factory.settings") as mock_settings:
            mock_settings.openai_api_key = "sk-test-openai"
            mock_settings.anthropic_api_key = "sk-ant-test"
            mock_settings.google_api_key = "AIza-test"
            mock_settings.default_temperature = 0.5
            mock_settings.default_max_tokens = 2048
            yield mock_settings

def test_list_all_models_integration(mock_settings_env):
    # We need to mock the actual API calls to list_models inside the providers
    # because we don't want to make real network requests with fake keys.
    
    with patch("models.providers.openai.OpenAIProvider.list_models") as mock_openai_list, \
         patch("models.providers.anthropic.AnthropicProvider.list_models") as mock_anthropic_list:
        
        # Setup mocks to return dummy models
        from models.providers.base import ModelInfo
        mock_openai_list.return_value = [ModelInfo(id="gpt-4o", display_name="GPT-4o", provider_name="openai", context_window=128000)]
        mock_anthropic_list.return_value = [ModelInfo(id="claude-3-5-sonnet", display_name="Claude 3.5", provider_name="anthropic", context_window=200000)]
        
        ModelProviderFactory.clear_cache()
        
        all_models = ModelProviderFactory.list_all_models(include_unavailable=True)
        
        # Verify we got models from multiple providers
        provider_names = {m.provider_name for m in all_models}
        assert "openai" in provider_names
        assert "anthropic" in provider_names
        assert len(all_models) >= 2

def test_factory_creates_providers_with_settings(mock_settings_env):
    ModelProviderFactory.clear_cache()
    
    # OpenAI
    openai_provider = ModelProviderFactory.get_provider("openai")
    assert openai_provider.config["api_key"] == "sk-test-openai"
    
    # Anthropic
    anthropic_provider = ModelProviderFactory.get_provider("anthropic")
    assert anthropic_provider.config["api_key"] == "sk-ant-test"
