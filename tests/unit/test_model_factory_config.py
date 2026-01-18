from unittest.mock import MagicMock, patch

import pytest

from models.provider_factory import ModelProviderFactory


@pytest.fixture
def mock_settings():
    ModelProviderFactory.clear_cache()
    with patch("models.provider_factory.settings") as mock:
        mock.openai_api_key = "test-openai-key"
        mock.anthropic_api_key = "test-anthropic-key"
        mock.default_temperature = 0.7
        mock.default_max_tokens = 1000
        yield mock
    ModelProviderFactory.clear_cache()

def test_get_provider_injects_api_key(mock_settings):
    # Get provider without config
    # We use real OpenAIProvider here, which is fine as it's lightweight
    provider = ModelProviderFactory.get_provider("openai", use_cache=False)
    
    # Check if api_key was injected into config
    assert provider.config.get("api_key") == "test-openai-key"

def test_get_provider_manual_config_overrides_settings(mock_settings):
    custom_config = {"api_key": "custom-key"}
    provider = ModelProviderFactory.get_provider("openai", config=custom_config, use_cache=False)
    
    assert provider.config.get("api_key") == "custom-key"

def test_create_model_uses_defaults(mock_settings):
    # Mock provider instance
    mock_provider_instance = MagicMock()
    
    # Mock the provider class constructor
    mock_provider_class = MagicMock(return_value=mock_provider_instance)
    
    # Patch the registry
    with patch.dict(ModelProviderFactory._PROVIDERS, {"openai": mock_provider_class}):
        # Call create_model without temp/tokens
        ModelProviderFactory.create_model("gpt-4o", provider_name="openai")
        
        # Verify create_model was called on provider with defaults from settings
        mock_provider_instance.create_model.assert_called_once()
        call_kwargs = mock_provider_instance.create_model.call_args.kwargs
        
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["max_tokens"] == 1000

def test_create_model_manual_overrides_defaults(mock_settings):
    mock_provider_instance = MagicMock()
    mock_provider_class = MagicMock(return_value=mock_provider_instance)
    
    with patch.dict(ModelProviderFactory._PROVIDERS, {"openai": mock_provider_class}):
        # Call create_model WITH explicit temp/tokens
        ModelProviderFactory.create_model(
            "gpt-4o", 
            provider_name="openai",
            temperature=0.2,
            max_tokens=500
        )
        
        mock_provider_instance.create_model.assert_called_once()
        call_kwargs = mock_provider_instance.create_model.call_args.kwargs
        
        assert call_kwargs["temperature"] == 0.2
        assert call_kwargs["max_tokens"] == 500
