"""Unit tests for e-signature service.

Task #57: E-Signature Integration
"""

import hashlib
import hmac
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services.esignature_service import (
    HelloSignService,
    get_esignature_service,
)


class TestHelloSignInit:
    """Tests for HelloSignService initialization and configuration."""

    def test_init_production_mode(self):
        """Service uses BASE_URL in production mode."""
        svc = HelloSignService(api_key="key123", test_mode=False)
        assert svc.base_url == HelloSignService.BASE_URL
        assert svc.api_key == "key123"
        assert svc.test_mode is False
        assert svc.client_id is None
        assert svc.webhook_secret is None

    def test_init_sandbox_mode(self):
        """Service uses SANDBOX_URL in test mode."""
        svc = HelloSignService(api_key="key123", test_mode=True)
        assert svc.base_url == HelloSignService.SANDBOX_URL
        assert svc.test_mode is True

    def test_init_with_client_id(self):
        """Client-ID header is set when client_id provided."""
        svc = HelloSignService(api_key="key123", client_id="cid456")
        assert svc.client_id == "cid456"
        assert svc.client.headers.get("Client-Id") == "cid456"

    def test_init_without_client_id_no_header(self):
        """Client-ID header is absent when client_id is not provided."""
        svc = HelloSignService(api_key="key123")
        assert "Client-Id" not in svc.client.headers

    def test_setup_client_auth_headers(self):
        """Auth headers are properly set on the HTTP client."""
        svc = HelloSignService(api_key="my-key")
        assert svc.client.headers["Authorization"] == "Bearer my-key"
        assert svc.client.headers["Content-Type"] == "application/json"
        assert svc.client.headers["Accept"] == "application/json"

    def test_init_with_webhook_secret(self):
        """Webhook secret is stored."""
        svc = HelloSignService(api_key="key", webhook_secret="wh_secret")
        assert svc.webhook_secret == "wh_secret"


class TestHelloSignAvailability:
    """Tests for is_available and get_provider_name."""

    def test_is_available_with_key(self):
        svc = HelloSignService(api_key="key123")
        assert svc.is_available() is True

    def test_is_available_with_empty_key(self):
        svc = HelloSignService(api_key="")
        assert svc.is_available() is False

    def test_get_provider_name(self):
        svc = HelloSignService(api_key="key")
        assert svc.get_provider_name() == "hellosign"


# Helper to create a service with a mocked AsyncClient
def _make_service(**overrides):
    defaults = {"api_key": "test_key", "test_mode": True}
    defaults.update(overrides)
    svc = HelloSignService(**defaults)
    svc.client = AsyncMock()
    return svc


class TestCreateEnvelope:
    """Tests for HelloSignService.create_envelope."""

    @pytest.mark.asyncio
    async def test_basic_envelope(self):
        """Create an envelope with minimal arguments."""
        svc = _make_service()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"signature_request_id": "req_1"}
        mock_resp.raise_for_status = MagicMock()
        svc.client.post.return_value = mock_resp

        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=MagicMock())
        mock_file.__exit__ = MagicMock(return_value=False)

        with patch("builtins.open", return_value=mock_file):
            result = await svc.create_envelope(
                document_path=Path("/tmp/doc.pdf"),
                signers=[{"email": "a@b.com", "name": "Alice"}],
                title="Contract",
            )

        assert result["envelope_id"] == "req_1"
        assert result["status"] == "sent"
        svc.client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_with_optional_fields(self):
        """Create envelope with subject, message, metadata, and expiry."""
        svc = _make_service()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"signature_request_id": "req_2"}
        mock_resp.raise_for_status = MagicMock()
        svc.client.post.return_value = mock_resp

        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=MagicMock())
        mock_file.__exit__ = MagicMock(return_value=False)

        with patch("builtins.open", return_value=mock_file):
            result = await svc.create_envelope(
                document_path=Path("/tmp/doc.pdf"),
                signers=[{"email": "a@b.com", "name": "Alice"}],
                title="Contract",
                subject="Sign now",
                message="Please sign",
                metadata={"deal_id": "D1"},
                expires_days=7,
            )

        assert result["envelope_id"] == "req_2"

        # Verify payload included expires_at
        call_args = svc.client.post.call_args
        payload = (
            call_args[1]["json"]
            if "json" in call_args[1]
            else call_args[0][1]
            if len(call_args[0]) > 1
            else None
        )
        if payload is None:
            payload = call_args.kwargs["json"]
        assert "expires_at" in payload
        assert payload["metadata"] == {"deal_id": "D1"}
        assert payload["subject"] == "Sign now"
        assert payload["message"] == "Please sign"

    @pytest.mark.asyncio
    async def test_multiple_signers_with_roles(self):
        """Multiple signers are assigned sequential order and role preserved."""
        svc = _make_service()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"signature_request_id": "req_3"}
        mock_resp.raise_for_status = MagicMock()
        svc.client.post.return_value = mock_resp

        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=MagicMock())
        mock_file.__exit__ = MagicMock(return_value=False)

        signers = [
            {"email": "a@b.com", "name": "Alice", "role": "buyer"},
            {"email": "c@d.com", "name": "Charlie"},
        ]

        with patch("builtins.open", return_value=mock_file):
            await svc.create_envelope(
                document_path=Path("/tmp/doc.pdf"),
                signers=signers,
                title="Deal",
            )

        payload = svc.client.post.call_args.kwargs["json"]
        assert payload["signers"][0]["order"] == 1
        assert payload["signers"][0]["role"] == "buyer"
        assert payload["signers"][1]["order"] == 2
        assert payload["signers"][1]["role"] == "signer"

    @pytest.mark.asyncio
    async def test_http_error_raises_runtime(self):
        """HTTPStatusError from API raises RuntimeError."""
        svc = _make_service()
        mock_resp = MagicMock()
        mock_resp.text = "Unauthorized"
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "err", request=MagicMock(), response=mock_resp
        )
        svc.client.post.return_value = mock_resp

        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=MagicMock())
        mock_file.__exit__ = MagicMock(return_value=False)

        with patch("builtins.open", return_value=mock_file):
            with pytest.raises(RuntimeError, match="HelloSign API error"):
                await svc.create_envelope(
                    document_path=Path("/tmp/doc.pdf"),
                    signers=[{"email": "a@b.com", "name": "A"}],
                    title="X",
                )

    @pytest.mark.asyncio
    async def test_generic_exception_propagates(self):
        """Non-HTTP exceptions propagate unchanged."""
        svc = _make_service()
        svc.client.post.side_effect = OSError("network down")

        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=MagicMock())
        mock_file.__exit__ = MagicMock(return_value=False)

        with patch("builtins.open", return_value=mock_file):
            with pytest.raises(OSError, match="network down"):
                await svc.create_envelope(
                    document_path=Path("/tmp/doc.pdf"),
                    signers=[{"email": "a@b.com", "name": "A"}],
                    title="X",
                )


class TestGetEnvelopeStatus:
    """Tests for HelloSignService.get_envelope_status."""

    @pytest.mark.asyncio
    async def test_completed_status(self):
        svc = _make_service()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "status": "completed",
            "signatures": [
                {
                    "signer_email_address": "a@b.com",
                    "signer_name": "Alice",
                    "status": "signed",
                    "signed_at": 1700000000,
                }
            ],
            "completed_at": 1700000001,
        }
        mock_resp.raise_for_status = MagicMock()
        svc.client.get.return_value = mock_resp

        result = await svc.get_envelope_status("env_1")

        assert result["status"] == "completed"
        assert result["is_complete"] is True
        assert result["completed_at"] == 1700000001
        assert len(result["signers"]) == 1
        assert result["signers"][0]["email"] == "a@b.com"
        assert result["signers"][0]["status"] == "signed"

    @pytest.mark.asyncio
    async def test_status_mapping(self):
        """All HelloSign statuses map correctly."""
        svc = _make_service()
        status_map = {
            "draft": "draft",
            "sent": "sent",
            "viewed": "viewed",
            "signed": "partially_signed",
            "completed": "completed",
            "expired": "expired",
            "cancelled": "cancelled",
            "declined": "declined",
        }
        for hs_status, expected in status_map.items():
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"status": hs_status, "signatures": []}
            mock_resp.raise_for_status = MagicMock()
            svc.client.get.return_value = mock_resp

            result = await svc.get_envelope_status("env_x")
            assert result["status"] == expected, f"Failed for {hs_status}"

    @pytest.mark.asyncio
    async def test_unknown_status_passes_through(self):
        """Unknown HelloSign status is returned as-is."""
        svc = _make_service()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "weird_new_status", "signatures": []}
        mock_resp.raise_for_status = MagicMock()
        svc.client.get.return_value = mock_resp

        result = await svc.get_envelope_status("env_x")
        assert result["status"] == "weird_new_status"

    @pytest.mark.asyncio
    async def test_signer_defaults_pending(self):
        """Missing signer status defaults to 'pending'."""
        svc = _make_service()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "status": "sent",
            "signatures": [
                {"signer_email_address": "a@b.com", "signer_name": "Alice"},
            ],
        }
        mock_resp.raise_for_status = MagicMock()
        svc.client.get.return_value = mock_resp

        result = await svc.get_envelope_status("env_x")
        assert result["signers"][0]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_http_error_raises_runtime(self):
        svc = _make_service()
        mock_resp = MagicMock()
        mock_resp.text = "Not Found"
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "err", request=MagicMock(), response=mock_resp
        )
        svc.client.get.return_value = mock_resp

        with pytest.raises(RuntimeError, match="HelloSign API error"):
            await svc.get_envelope_status("env_x")

    @pytest.mark.asyncio
    async def test_generic_exception_propagates(self):
        svc = _make_service()
        svc.client.get.side_effect = OSError("timeout")

        with pytest.raises(OSError, match="timeout"):
            await svc.get_envelope_status("env_x")


class TestDownloadSignedDocument:
    """Tests for HelloSignService.download_signed_document."""

    @pytest.mark.asyncio
    async def test_successful_download(self):
        svc = _make_service()
        files_resp = MagicMock()
        files_resp.json.return_value = {"files": [{"file_url": "https://example.com/signed.pdf"}]}
        files_resp.raise_for_status = MagicMock()

        file_resp = MagicMock()
        file_resp.content = b"%PDF-1.4 content"
        file_resp.raise_for_status = MagicMock()

        svc.client.get.side_effect = [files_resp, file_resp]

        result = await svc.download_signed_document("env_1")
        assert result == b"%PDF-1.4 content"
        assert svc.client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_no_files_raises_value_error(self):
        svc = _make_service()
        files_resp = MagicMock()
        files_resp.json.return_value = {"files": []}
        files_resp.raise_for_status = MagicMock()
        svc.client.get.return_value = files_resp

        with pytest.raises(ValueError, match="No signed files available"):
            await svc.download_signed_document("env_1")

    @pytest.mark.asyncio
    async def test_no_file_url_raises_value_error(self):
        svc = _make_service()
        files_resp = MagicMock()
        files_resp.json.return_value = {"files": [{"file_url": None}]}
        files_resp.raise_for_status = MagicMock()
        svc.client.get.return_value = files_resp

        with pytest.raises(ValueError, match="No signed file URL in response"):
            await svc.download_signed_document("env_1")

    @pytest.mark.asyncio
    async def test_http_error_raises_runtime(self):
        svc = _make_service()
        mock_resp = MagicMock()
        mock_resp.text = "Server Error"
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "err", request=MagicMock(), response=mock_resp
        )
        svc.client.get.return_value = mock_resp

        with pytest.raises(RuntimeError, match="HelloSign API error"):
            await svc.download_signed_document("env_1")


class TestCancelEnvelope:
    """Tests for HelloSignService.cancel_envelope."""

    @pytest.mark.asyncio
    async def test_cancel_success(self):
        svc = _make_service()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        svc.client.post.return_value = mock_resp

        assert await svc.cancel_envelope("env_1") is True

    @pytest.mark.asyncio
    async def test_cancel_404_returns_false(self):
        """404 means already completed or not found; return False."""
        svc = _make_service()
        mock_resp = MagicMock()
        mock_resp.text = "Not Found"
        mock_resp.status_code = 404
        error = httpx.HTTPStatusError("err", request=MagicMock(), response=mock_resp)
        mock_resp.raise_for_status.side_effect = error
        svc.client.post.return_value = mock_resp

        assert await svc.cancel_envelope("env_1") is False

    @pytest.mark.asyncio
    async def test_cancel_other_http_error_raises(self):
        """Non-404 HTTP errors propagate."""
        svc = _make_service()
        mock_resp = MagicMock()
        mock_resp.text = "Forbidden"
        mock_resp.status_code = 403
        error = httpx.HTTPStatusError("err", request=MagicMock(), response=mock_resp)
        mock_resp.raise_for_status.side_effect = error
        svc.client.post.return_value = mock_resp

        with pytest.raises(httpx.HTTPStatusError):
            await svc.cancel_envelope("env_1")

    @pytest.mark.asyncio
    async def test_cancel_generic_exception_returns_false(self):
        svc = _make_service()
        svc.client.post.side_effect = OSError("connection lost")

        assert await svc.cancel_envelope("env_1") is False


class TestSendReminder:
    """Tests for HelloSignService.send_reminder."""

    @pytest.mark.asyncio
    async def test_reminder_success(self):
        svc = _make_service()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        svc.client.post.return_value = mock_resp

        assert await svc.send_reminder("env_1") is True

    @pytest.mark.asyncio
    async def test_reminder_http_error_returns_false(self):
        svc = _make_service()
        mock_resp = MagicMock()
        mock_resp.text = "Bad Request"
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "err", request=MagicMock(), response=mock_resp
        )
        svc.client.post.return_value = mock_resp

        assert await svc.send_reminder("env_1") is False

    @pytest.mark.asyncio
    async def test_reminder_generic_exception_returns_false(self):
        svc = _make_service()
        svc.client.post.side_effect = OSError("fail")

        assert await svc.send_reminder("env_1") is False


class TestVerifyWebhookSignature:
    """Tests for HelloSignService.verify_webhook_signature."""

    def test_valid_signature(self):
        secret = "my_secret"
        svc = HelloSignService(api_key="key", webhook_secret=secret)
        payload = b'{"event":"signed"}'

        expected_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        assert svc.verify_webhook_signature(payload, expected_sig) is True

    def test_invalid_signature(self):
        svc = HelloSignService(api_key="key", webhook_secret="secret")
        assert svc.verify_webhook_signature(b"payload", "bad_signature") is False

    def test_no_webhook_secret_returns_true(self):
        """Without a webhook secret configured, verification is skipped."""
        svc = HelloSignService(api_key="key")
        assert svc.verify_webhook_signature(b"payload", "any_sig") is True

    def test_empty_webhook_secret_returns_true(self):
        """Empty string webhook secret is treated as not configured."""
        svc = HelloSignService(api_key="key", webhook_secret="")
        assert svc.verify_webhook_signature(b"payload", "any_sig") is True

    def test_timestamp_param_ignored(self):
        """Timestamp parameter is accepted but not used in verification."""
        secret = "secret"
        svc = HelloSignService(api_key="key", webhook_secret=secret)
        payload = b"data"

        expected_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        assert svc.verify_webhook_signature(payload, expected_sig, timestamp="12345") is True


class TestGetEsignatureServiceFactory:
    """Tests for the get_esignature_service factory function."""

    def _reset_factory(self):
        """Reset the module-level singleton so each test starts fresh."""
        import services.esignature_service as mod

        original = mod._esignature_service
        mod._esignature_service = None
        return original

    def _restore_factory(self, original):
        import services.esignature_service as mod

        mod._esignature_service = original

    def test_returns_none_when_no_api_key(self):
        """Factory returns None when hellosign_api_key is not set."""
        original = self._reset_factory()
        try:
            mock_settings = MagicMock()
            mock_settings.hellosign_api_key = None
            mock_settings.environment = "production"
            mock_settings.hellosign_webhook_secret = None

            with patch("config.settings.settings", mock_settings):
                result = get_esignature_service()
            assert result is None
        finally:
            self._restore_factory(original)

    def test_creates_service_with_api_key(self):
        """Factory creates HelloSignService when API key is configured."""
        original = self._reset_factory()
        try:
            mock_settings = MagicMock()
            mock_settings.hellosign_api_key = "test_key_abc"
            mock_settings.environment = "development"
            mock_settings.hellosign_webhook_secret = "wh_secret"

            with patch("config.settings.settings", mock_settings):
                result = get_esignature_service()

            assert result is not None
            assert isinstance(result, HelloSignService)
            assert result.api_key == "test_key_abc"
            assert result.test_mode is True
            assert result.webhook_secret == "wh_secret"
        finally:
            self._restore_factory(original)

    def test_caches_service_instance(self):
        """Factory returns the same instance on subsequent calls."""
        original = self._reset_factory()
        try:
            mock_settings = MagicMock()
            mock_settings.hellosign_api_key = "cached_key"
            mock_settings.environment = "production"
            mock_settings.hellosign_webhook_secret = None

            with patch("config.settings.settings", mock_settings):
                first = get_esignature_service()
                second = get_esignature_service()

            assert first is second
        finally:
            self._restore_factory(original)


class TestProtocolConformance:
    """Verify HelloSignService satisfies the ESignatureService protocol."""

    def test_protocol_instance_check(self):
        """HelloSignService is an instance of ESignatureService protocol."""
        from services.esignature_service import ESignatureService

        svc = HelloSignService(api_key="key")
        assert isinstance(svc, ESignatureService)
