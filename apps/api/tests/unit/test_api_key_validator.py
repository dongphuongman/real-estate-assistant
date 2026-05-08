"""Unit tests for utils/api_key_validator.py."""

from unittest.mock import MagicMock, patch

from utils.api_key_validator import APIKeyValidator, ValidationResult


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_validation_result_creation(self):
        result = ValidationResult(is_valid=True, provider="Test", message="OK")
        assert result.is_valid is True
        assert result.provider == "Test"
        assert result.message == "OK"
        assert result.error_details is None

    def test_validation_result_with_error_details(self):
        result = ValidationResult(
            is_valid=False, provider="Test", message="Error", error_details="details"
        )
        assert result.is_valid is False
        assert result.error_details == "details"


class TestValidateOpenAI:
    """Test validate_openai method."""

    def test_validate_openai_invalid_key(self):
        with patch("openai.OpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.models.list.side_effect = Exception("Invalid authentication")

            result = APIKeyValidator.validate_openai("sk-invalid")
            assert result.is_valid is False
            assert result.provider == "OpenAI"
            assert "Invalid" in result.message or "error" in result.message.lower()

    def test_validate_openai_network_error(self):
        with patch("openai.OpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.models.list.side_effect = Exception("Connection timeout")

            result = APIKeyValidator.validate_openai("sk-test")
            assert result.is_valid is False
            assert result.error_details is not None

    def test_validate_openai_import_error(self):
        with patch.dict("sys.modules", {"openai": None}):
            result = APIKeyValidator.validate_openai("sk-test")
            assert result.is_valid is False


class TestValidateAnthropic:
    """Test validate_anthropic method."""

    def test_validate_anthropic_invalid_key(self):
        with patch("anthropic.Anthropic") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.messages.create.side_effect = Exception("401 Unauthorized")

            result = APIKeyValidator.validate_anthropic("sk-ant-invalid")
            assert result.is_valid is False
            assert result.provider == "Anthropic"

    def test_validate_anthropic_network_error(self):
        with patch("anthropic.Anthropic") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.messages.create.side_effect = Exception("Connection refused")

            result = APIKeyValidator.validate_anthropic("sk-ant-test")
            assert result.is_valid is False
            assert "error" in result.message.lower()


class TestValidateGoogle:
    """Test validate_google method."""

    def test_validate_google_invalid_key(self):
        mock_genai = MagicMock()
        mock_genai.list_models.side_effect = Exception("API key not valid")
        with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
            result = APIKeyValidator.validate_google("invalid-key")
            assert result.is_valid is False
            assert result.provider == "Google"

    def test_validate_google_403_error(self):
        mock_genai = MagicMock()
        mock_genai.list_models.side_effect = Exception("403 Forbidden")
        with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
            result = APIKeyValidator.validate_google("bad-key")
            assert result.is_valid is False
            assert result.error_details is not None


class TestValidateGrok:
    """Test validate_grok method."""

    @patch("requests.get")
    def test_validate_grok_success(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)

        result = APIKeyValidator.validate_grok("xai-test-key")
        assert result.is_valid is True
        assert result.provider == "Grok"

    @patch("requests.get")
    def test_validate_grok_unauthorized(self, mock_get):
        mock_get.return_value = MagicMock(status_code=401)

        result = APIKeyValidator.validate_grok("xai-bad-key")
        assert result.is_valid is False
        assert "Invalid" in result.message

    @patch("requests.get")
    def test_validate_grok_forbidden(self, mock_get):
        mock_get.return_value = MagicMock(status_code=403)

        result = APIKeyValidator.validate_grok("xai-bad-key")
        assert result.is_valid is False

    @patch("requests.get")
    def test_validate_grok_server_error(self, mock_get):
        mock_get.return_value = MagicMock(status_code=500)

        result = APIKeyValidator.validate_grok("xai-test")
        assert result.is_valid is False
        assert "error" in result.message.lower()

    @patch("requests.get")
    def test_validate_grok_connection_error(self, mock_get):
        mock_get.side_effect = Exception("Connection timeout")

        result = APIKeyValidator.validate_grok("xai-test")
        assert result.is_valid is False


class TestValidateDeepSeek:
    """Test validate_deepseek method."""

    @patch("requests.get")
    def test_validate_deepseek_success(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)

        result = APIKeyValidator.validate_deepseek("ds-test-key")
        assert result.is_valid is True
        assert result.provider == "DeepSeek"

    @patch("requests.get")
    def test_validate_deepseek_unauthorized(self, mock_get):
        mock_get.return_value = MagicMock(status_code=401)

        result = APIKeyValidator.validate_deepseek("ds-bad-key")
        assert result.is_valid is False

    @patch("requests.get")
    def test_validate_deepseek_connection_error(self, mock_get):
        mock_get.side_effect = Exception("Network error")

        result = APIKeyValidator.validate_deepseek("ds-test")
        assert result.is_valid is False
        assert "error" in result.message.lower()


class TestValidateKey:
    """Test validate_key dispatcher method."""

    def test_validate_key_unknown_provider(self):
        result = APIKeyValidator.validate_key("unknown_provider", "test-key")
        assert result.is_valid is False
        assert "Unknown provider" in result.message

    @patch.object(APIKeyValidator, "validate_openai")
    def test_validate_key_routes_to_openai(self, mock_validate):
        mock_validate.return_value = ValidationResult(
            is_valid=True, provider="OpenAI", message="OK"
        )
        result = APIKeyValidator.validate_key("openai", "sk-test")
        assert result.is_valid is True
        mock_validate.assert_called_once_with("sk-test")

    @patch.object(APIKeyValidator, "validate_anthropic")
    def test_validate_key_routes_to_anthropic(self, mock_validate):
        mock_validate.return_value = ValidationResult(
            is_valid=True, provider="Anthropic", message="OK"
        )
        result = APIKeyValidator.validate_key("anthropic", "sk-ant-test")
        assert result.is_valid is True
        mock_validate.assert_called_once_with("sk-ant-test")

    @patch.object(APIKeyValidator, "validate_google")
    def test_validate_key_routes_to_google(self, mock_validate):
        mock_validate.return_value = ValidationResult(
            is_valid=True, provider="Google", message="OK"
        )
        result = APIKeyValidator.validate_key("google", "test-key")
        assert result.is_valid is True

    @patch.object(APIKeyValidator, "validate_grok")
    def test_validate_key_routes_to_grok(self, mock_validate):
        mock_validate.return_value = ValidationResult(is_valid=True, provider="Grok", message="OK")
        result = APIKeyValidator.validate_key("grok", "test-key")
        assert result.is_valid is True

    @patch.object(APIKeyValidator, "validate_deepseek")
    def test_validate_key_routes_to_deepseek(self, mock_validate):
        mock_validate.return_value = ValidationResult(
            is_valid=True, provider="DeepSeek", message="OK"
        )
        result = APIKeyValidator.validate_key("deepseek", "test-key")
        assert result.is_valid is True

    def test_validate_key_case_insensitive(self):
        result = APIKeyValidator.validate_key("OpenAI", "test-key")
        assert result.provider == "OpenAI"
        assert "Unknown" not in result.message
