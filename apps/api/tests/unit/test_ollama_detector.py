"""Unit tests for utils/ollama_detector.py."""

from unittest.mock import MagicMock, patch

from utils.ollama_detector import OllamaDetector, OllamaStatus


class TestOllamaStatus:
    """Test OllamaStatus dataclass."""

    def test_ollama_status_defaults(self):
        status = OllamaStatus(is_installed=False, is_running=False)
        assert status.is_installed is False
        assert status.is_running is False
        assert status.version is None
        assert status.available_models == []  # Set by __post_init__
        assert status.error_message is None

    def test_ollama_status_with_values(self):
        status = OllamaStatus(
            is_installed=True,
            is_running=True,
            version="0.1.20",
            available_models=["llama3.3:8b", "mistral:7b"],
        )
        assert status.is_installed is True
        assert status.version == "0.1.20"
        assert len(status.available_models) == 2


class TestGetOsType:
    """Test get_os_type method."""

    @patch("utils.ollama_detector.platform.system", return_value="Darwin")
    def test_get_os_type_macos(self, mock_system):
        assert OllamaDetector.get_os_type() == "macos"

    @patch("utils.ollama_detector.platform.system", return_value="Linux")
    def test_get_os_type_linux(self, mock_system):
        assert OllamaDetector.get_os_type() == "linux"

    @patch("utils.ollama_detector.platform.system", return_value="Windows")
    def test_get_os_type_windows(self, mock_system):
        assert OllamaDetector.get_os_type() == "windows"

    @patch("utils.ollama_detector.platform.system", return_value="FreeBSD")
    def test_get_os_type_unknown(self, mock_system):
        assert OllamaDetector.get_os_type() == "unknown"


class TestCheckOllamaInstalled:
    """Test check_ollama_installed method."""

    @patch("utils.ollama_detector.subprocess.run")
    def test_installed_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        assert OllamaDetector.check_ollama_installed() is True

    @patch("utils.ollama_detector.subprocess.run")
    def test_not_installed_file_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        assert OllamaDetector.check_ollama_installed() is False

    @patch("utils.ollama_detector.subprocess.run")
    def test_not_installed_timeout(self, mock_run):
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ollama", timeout=5)
        assert OllamaDetector.check_ollama_installed() is False

    @patch("utils.ollama_detector.subprocess.run")
    def test_not_installed_general_error(self, mock_run):
        mock_run.side_effect = OSError("Permission denied")
        assert OllamaDetector.check_ollama_installed() is False

    @patch("utils.ollama_detector.subprocess.run")
    def test_installed_nonzero_return(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        assert OllamaDetector.check_ollama_installed() is False


class TestGetOllamaVersion:
    """Test get_ollama_version method."""

    @patch("utils.ollama_detector.subprocess.run")
    def test_get_version_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ollama version 0.1.20\n")
        assert OllamaDetector.get_ollama_version() == "ollama version 0.1.20"

    @patch("utils.ollama_detector.subprocess.run")
    def test_get_version_not_installed(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        assert OllamaDetector.get_ollama_version() is None

    @patch("utils.ollama_detector.subprocess.run")
    def test_get_version_nonzero_return(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        assert OllamaDetector.get_ollama_version() is None


class TestCheckOllamaRunning:
    """Test check_ollama_running method."""

    @patch("utils.ollama_detector.requests.get")
    def test_running_success(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        assert OllamaDetector.check_ollama_running() is True

    @patch("utils.ollama_detector.requests.get")
    def test_not_running_non_200(self, mock_get):
        mock_get.return_value = MagicMock(status_code=503)
        assert OllamaDetector.check_ollama_running() is False

    @patch("utils.ollama_detector.requests.get")
    def test_not_running_connection_error(self, mock_get):
        import requests

        mock_get.side_effect = requests.ConnectionError()
        assert OllamaDetector.check_ollama_running() is False

    @patch("utils.ollama_detector.requests.get")
    def test_running_custom_base_url(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        assert OllamaDetector.check_ollama_running("http://custom:11434") is True
        mock_get.assert_called_with("http://custom:11434/api/tags", timeout=3)


class TestGetAvailableModels:
    """Test get_available_models method."""

    @patch("utils.ollama_detector.requests.get")
    def test_get_models_success(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "models": [
                    {"name": "llama3.3:8b"},
                    {"name": "mistral:7b"},
                ]
            },
        )
        models = OllamaDetector.get_available_models()
        assert models == ["llama3.3:8b", "mistral:7b"]

    @patch("utils.ollama_detector.requests.get")
    def test_get_models_empty(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"models": []})
        models = OllamaDetector.get_available_models()
        assert models == []

    @patch("utils.ollama_detector.requests.get")
    def test_get_models_filters_empty_names(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"models": [{"name": "llama3.3:8b"}, {"name": ""}, {}]},
        )
        models = OllamaDetector.get_available_models()
        assert models == ["llama3.3:8b"]

    @patch("utils.ollama_detector.requests.get")
    def test_get_models_error(self, mock_get):
        import requests

        mock_get.side_effect = requests.ConnectionError()
        models = OllamaDetector.get_available_models()
        assert models == []


class TestGetStatus:
    """Test get_status comprehensive method."""

    @patch.object(OllamaDetector, "get_available_models", return_value=["llama3.3:8b"])
    @patch.object(OllamaDetector, "check_ollama_running", return_value=True)
    @patch.object(OllamaDetector, "get_ollama_version", return_value="0.1.20")
    @patch.object(OllamaDetector, "check_ollama_installed", return_value=True)
    def test_status_installed_and_running(
        self, mock_installed, mock_version, mock_running, mock_models
    ):
        status = OllamaDetector.get_status()
        assert status.is_installed is True
        assert status.is_running is True
        assert status.version == "0.1.20"
        assert "llama3.3:8b" in status.available_models
        assert status.error_message is None

    @patch.object(OllamaDetector, "check_ollama_running", return_value=False)
    @patch.object(OllamaDetector, "get_ollama_version", return_value="0.1.20")
    @patch.object(OllamaDetector, "check_ollama_installed", return_value=True)
    def test_status_installed_not_running(self, mock_installed, mock_version, mock_running):
        status = OllamaDetector.get_status()
        assert status.is_installed is True
        assert status.is_running is False
        assert "not running" in status.error_message.lower()

    @patch.object(OllamaDetector, "check_ollama_installed", return_value=False)
    def test_status_not_installed(self, mock_installed):
        status = OllamaDetector.get_status()
        assert status.is_installed is False
        assert status.is_running is False
        assert "not installed" in status.error_message.lower()

    def test_status_custom_base_url(self):
        with patch.object(OllamaDetector, "check_ollama_installed", return_value=False):
            status = OllamaDetector.get_status(base_url="http://custom:11434")
            assert status.base_url == "http://custom:11434"


class TestGetInstallationInstructions:
    """Test get_installation_instructions method."""

    def test_macos_instructions(self):
        instructions = OllamaDetector.get_installation_instructions("macos")
        assert "macOS" in instructions["title"]
        assert "method_1" in instructions
        assert "method_2" in instructions
        assert "post_install" in instructions

    def test_linux_instructions(self):
        instructions = OllamaDetector.get_installation_instructions("linux")
        assert "Linux" in instructions["title"]
        assert "curl" in instructions["method_1"]["command"]

    def test_windows_instructions(self):
        instructions = OllamaDetector.get_installation_instructions("windows")
        assert "Windows" in instructions["title"]
        assert "winget" in instructions["method_2"]["command"]

    def test_unknown_os_instructions(self):
        instructions = OllamaDetector.get_installation_instructions("unknown")
        assert "url" in instructions or "message" in instructions

    @patch("utils.ollama_detector.OllamaDetector.get_os_type", return_value="linux")
    def test_auto_detect_os(self, mock_get_os):
        instructions = OllamaDetector.get_installation_instructions()
        assert "Linux" in instructions["title"]

    def test_unexpected_os_type(self):
        instructions = OllamaDetector.get_installation_instructions("amiga")
        assert isinstance(instructions, dict)


class TestGetRecommendedModels:
    """Test get_recommended_models method."""

    def test_returns_list(self):
        models = OllamaDetector.get_recommended_models()
        assert isinstance(models, list)
        assert len(models) >= 3

    def test_model_structure(self):
        models = OllamaDetector.get_recommended_models()
        for model in models:
            assert "name" in model
            assert "size" in model
            assert "ram" in model
            assert "description" in model
            assert "command" in model
            assert "recommended" in model

    def test_has_recommended_models(self):
        models = OllamaDetector.get_recommended_models()
        recommended = [m for m in models if m["recommended"]]
        assert len(recommended) >= 1
