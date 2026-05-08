"""Tests for notifications.email_service module."""

import os
from email.mime.multipart import MIMEMultipart
from unittest.mock import MagicMock, patch

import pytest

from notifications.email_service import (
    EmailConfig,
    EmailProvider,
    EmailSendError,
    EmailService,
    EmailServiceFactory,
    EmailValidationError,
)


def _config(**overrides):
    defaults = dict(
        provider=EmailProvider.GMAIL,
        smtp_server="smtp.test.com",
        smtp_port=587,
        username="user@test.com",
        password="pass",
        from_email="user@test.com",
        from_name="Test",
    )
    defaults.update(overrides)
    return EmailConfig(**defaults)


class TestEmailProvider:
    def test_values(self):
        assert EmailProvider.GMAIL == "gmail"
        assert EmailProvider.OUTLOOK == "outlook"
        assert EmailProvider.SENDGRID == "sendgrid"
        assert EmailProvider.CUSTOM == "custom"


class TestEmailConfig:
    def test_defaults(self):
        cfg = _config()
        assert cfg.use_tls is True
        assert cfg.use_ssl is False
        assert cfg.timeout == 30
        assert cfg.from_name == "Test"

    def test_custom(self):
        cfg = _config(use_ssl=True, timeout=60)
        assert cfg.use_ssl is True
        assert cfg.timeout == 60


class TestEmailServiceValidate:
    def test_valid_emails(self):
        svc = EmailService(_config())
        assert svc.validate_email("user@example.com") is True
        assert svc.validate_email("a.b+c@domain.org") is True

    def test_invalid_emails(self):
        svc = EmailService(_config())
        assert svc.validate_email("notanemail") is False
        assert svc.validate_email("@missing.com") is False
        assert svc.validate_email("missing@") is False
        assert svc.validate_email("") is False


class TestEmailServiceSend:
    @patch("notifications.email_service.smtplib.SMTP")
    def test_send_plain_text(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        svc = EmailService(_config())
        result = svc.send_email("to@test.com", "Subject", "Hello")
        assert result is True
        assert svc._sent_count == 1

    @patch("notifications.email_service.smtplib.SMTP")
    def test_send_html(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        svc = EmailService(_config())
        result = svc.send_email("to@test.com", "Subject", "<b>Hello</b>", html=True)
        assert result is True

    def test_send_invalid_email_raises(self):
        svc = EmailService(_config())
        with pytest.raises(EmailValidationError):
            svc.send_email("notanemail", "Subject", "body")

    def test_send_invalid_cc_raises(self):
        svc = EmailService(_config())
        with pytest.raises(EmailValidationError):
            svc.send_email("to@test.com", "Subject", "body", cc=["bad"])

    def test_send_invalid_bcc_raises(self):
        svc = EmailService(_config())
        with pytest.raises(EmailValidationError):
            svc.send_email("to@test.com", "Subject", "body", bcc=["bad"])

    @patch("notifications.email_service.time.sleep")
    @patch("notifications.email_service.smtplib.SMTP")
    def test_send_retries_on_failure(self, mock_smtp_cls, mock_sleep):
        mock_server = MagicMock()
        mock_server.send_message.side_effect = Exception("SMTP error")
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        svc = EmailService(_config(), max_retries=2)
        with pytest.raises(EmailSendError) as exc_info:
            svc.send_email("to@test.com", "Subject", "body")
        assert "2 attempts" in str(exc_info.value)
        assert svc._failed_count == 1
        assert mock_sleep.call_count == 1

    @patch("notifications.email_service.smtplib.SMTP_SSL")
    def test_send_with_ssl(self, mock_smtp_ssl_cls):
        mock_server = MagicMock()
        mock_smtp_ssl_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_ssl_cls.return_value.__exit__ = MagicMock(return_value=False)

        svc = EmailService(_config(use_ssl=True, use_tls=False))
        result = svc.send_email("to@test.com", "Subject", "body")
        assert result is True
        mock_smtp_ssl_cls.assert_called_once()

    @patch("notifications.email_service.smtplib.SMTP")
    def test_send_with_cc_and_bcc(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        svc = EmailService(_config())
        result = svc.send_email(
            "to@test.com", "Subject", "body", cc=["cc@test.com"], bcc=["bcc@test.com"]
        )
        assert result is True

    @patch("notifications.email_service.smtplib.SMTP")
    def test_send_no_tls(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        svc = EmailService(_config(use_tls=False, use_ssl=False))
        result = svc.send_email("to@test.com", "Subject", "body")
        assert result is True
        mock_server.starttls.assert_not_called()


class TestEmailServiceBulk:
    @patch("notifications.email_service.smtplib.SMTP")
    def test_bulk_send(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        svc = EmailService(_config())
        result = svc.send_bulk_emails(["a@test.com", "b@test.com"], "Subject", "body", batch_size=1)
        assert result["sent"] == 2
        assert result["failed"] == 0

    @patch("notifications.email_service.smtplib.SMTP")
    def test_bulk_send_with_failures(self, mock_smtp_cls):
        call_count = 0
        mock_server = MagicMock()

        def _enter(self):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise Exception("fail")
            return mock_server

        mock_smtp_cls.return_value.__enter__ = _enter
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        svc = EmailService(_config(), max_retries=1)
        result = svc.send_bulk_emails(["a@test.com", "b@test.com"], "Subject", "body", batch_size=1)
        assert result["sent"] >= 0
        assert result["failed"] > 0

    @patch("notifications.email_service.time.sleep")
    @patch("notifications.email_service.smtplib.SMTP")
    def test_bulk_with_batch_delay(self, mock_smtp_cls, mock_sleep):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        svc = EmailService(_config())
        svc.send_bulk_emails(
            ["a@test.com", "b@test.com"],
            "Subject",
            "body",
            batch_size=1,
            delay_between_batches=0.5,
        )
        assert mock_sleep.called

    @patch("notifications.email_service.smtplib.SMTP")
    def test_bulk_empty_recipients(self, mock_smtp_cls):
        svc = EmailService(_config())
        result = svc.send_bulk_emails([], "Subject", "body")
        assert result["sent"] == 0
        assert result["failed"] == 0

    @patch("notifications.email_service.smtplib.SMTP")
    def test_bulk_single_batch(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        svc = EmailService(_config())
        result = svc.send_bulk_emails(
            ["a@test.com", "b@test.com"], "Subject", "body", batch_size=100
        )
        assert result["sent"] == 2


class TestEmailServiceTestEmail:
    @patch("notifications.email_service.smtplib.SMTP")
    def test_send_test_email(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        svc = EmailService(_config())
        result = svc.send_test_email("to@test.com")
        assert result is True


class TestEmailServiceStatistics:
    def test_initial_stats(self):
        svc = EmailService(_config())
        stats = svc.get_statistics()
        assert stats["sent"] == 0
        assert stats["failed"] == 0
        assert stats["total"] == 0
        assert stats["success_rate"] == 0

    @patch("notifications.email_service.smtplib.SMTP")
    def test_stats_after_send(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        svc = EmailService(_config())
        svc.send_email("to@test.com", "Subject", "body")
        stats = svc.get_statistics()
        assert stats["sent"] == 1
        assert stats["success_rate"] == 100.0

    @patch("notifications.email_service.time.sleep")
    @patch("notifications.email_service.smtplib.SMTP")
    def test_stats_after_failure(self, mock_smtp_cls, mock_sleep):
        mock_server = MagicMock()
        mock_server.send_message.side_effect = Exception("fail")
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        svc = EmailService(_config(), max_retries=1)
        with pytest.raises(EmailSendError):
            svc.send_email("to@test.com", "Subject", "body")

        stats = svc.get_statistics()
        assert stats["failed"] == 1
        assert stats["sent"] == 0


class TestCreateMessage:
    def test_plain_text_message(self):
        svc = EmailService(_config())
        msg = svc._create_message("to@test.com", "Test", "Hello", False, None, None)
        assert isinstance(msg, MIMEMultipart)
        assert msg["Subject"] == "Test"
        assert msg["To"] == "to@test.com"

    def test_html_message(self):
        svc = EmailService(_config())
        msg = svc._create_message("to@test.com", "Test", "<b>Hello</b>", True, None, None)
        assert isinstance(msg, MIMEMultipart)

    def test_message_with_cc_bcc(self):
        svc = EmailService(_config())
        msg = svc._create_message(
            "to@test.com", "Test", "body", False, ["cc@test.com"], ["bcc@test.com"]
        )
        assert msg["Cc"] == "cc@test.com"
        assert msg["Bcc"] == "bcc@test.com"

    def test_message_from_header(self):
        cfg = _config(from_name="Sender", from_email="sender@test.com")
        svc = EmailService(cfg)
        msg = svc._create_message("to@test.com", "Test", "body", False, None, None)
        assert "Sender" in msg["From"]
        assert "sender@test.com" in msg["From"]


class TestEmailServiceFactory:
    def test_create_gmail(self):
        svc = EmailServiceFactory.create_gmail_service("user@gmail.com", "pass")
        assert svc.config.provider == EmailProvider.GMAIL
        assert svc.config.smtp_server == "smtp.gmail.com"
        assert svc.config.smtp_port == 587
        assert svc.config.use_tls is True

    def test_create_gmail_custom_name(self):
        svc = EmailServiceFactory.create_gmail_service("u@gmail.com", "p", "Custom")
        assert svc.config.from_name == "Custom"

    def test_create_outlook(self):
        svc = EmailServiceFactory.create_outlook_service("user@outlook.com", "pass")
        assert svc.config.provider == EmailProvider.OUTLOOK
        assert svc.config.smtp_server == "smtp-mail.outlook.com"

    def test_create_outlook_custom_name(self):
        svc = EmailServiceFactory.create_outlook_service("u@outlook.com", "p", "Custom")
        assert svc.config.from_name == "Custom"

    def test_create_custom(self):
        svc = EmailServiceFactory.create_custom_service(
            "mail.test.com", 465, "user", "pass", "user@test.com", use_ssl=True
        )
        assert svc.config.provider == EmailProvider.CUSTOM
        assert svc.config.smtp_port == 465
        assert svc.config.use_ssl is True

    def test_create_from_env_gmail(self):
        env = {
            "SMTP_PROVIDER": "gmail",
            "SMTP_USERNAME": "user@gmail.com",
            "SMTP_PASSWORD": "pass",
        }
        with patch.dict(os.environ, env, clear=False):
            svc = EmailServiceFactory.create_from_env()
            assert svc is not None
            assert svc.config.provider == EmailProvider.GMAIL

    def test_create_from_env_outlook(self):
        env = {
            "SMTP_PROVIDER": "outlook",
            "SMTP_USERNAME": "user@outlook.com",
            "SMTP_PASSWORD": "pass",
        }
        with patch.dict(os.environ, env, clear=False):
            svc = EmailServiceFactory.create_from_env()
            assert svc is not None
            assert svc.config.provider == EmailProvider.OUTLOOK

    def test_create_from_env_custom(self):
        env = {
            "SMTP_PROVIDER": "custom",
            "SMTP_USERNAME": "user",
            "SMTP_PASSWORD": "pass",
            "SMTP_SERVER": "mail.custom.com",
            "SMTP_PORT": "587",
        }
        with patch.dict(os.environ, env, clear=False):
            svc = EmailServiceFactory.create_from_env()
            assert svc is not None
            assert svc.config.provider == EmailProvider.CUSTOM
            assert svc.config.smtp_server == "mail.custom.com"

    def test_create_from_env_no_provider(self):
        with patch.dict(os.environ, {"SMTP_PROVIDER": ""}, clear=False):
            svc = EmailServiceFactory.create_from_env()
            assert svc is None

    def test_create_from_env_no_credentials(self):
        env = {"SMTP_PROVIDER": "gmail", "SMTP_USERNAME": "", "SMTP_PASSWORD": ""}
        with patch.dict(os.environ, env, clear=False):
            svc = EmailServiceFactory.create_from_env()
            assert svc is None

    def test_create_from_env_custom_missing_server(self):
        env = {
            "SMTP_PROVIDER": "custom",
            "SMTP_USERNAME": "user",
            "SMTP_PASSWORD": "pass",
            "SMTP_SERVER": "",
            "SMTP_PORT": "587",
        }
        with patch.dict(os.environ, env, clear=False):
            svc = EmailServiceFactory.create_from_env()
            assert svc is None

    def test_create_from_env_custom_missing_port(self):
        env = {
            "SMTP_PROVIDER": "custom",
            "SMTP_USERNAME": "user",
            "SMTP_PASSWORD": "pass",
            "SMTP_SERVER": "mail.test.com",
            "SMTP_PORT": "not_a_number",
        }
        with patch.dict(os.environ, env, clear=False):
            svc = EmailServiceFactory.create_from_env()
            assert svc is None

    def test_create_from_env_unknown_provider(self):
        env = {
            "SMTP_PROVIDER": "unknown",
            "SMTP_USERNAME": "user",
            "SMTP_PASSWORD": "pass",
        }
        with patch.dict(os.environ, env, clear=False):
            svc = EmailServiceFactory.create_from_env()
            assert svc is None

    def test_create_from_env_custom_timeout(self):
        env = {
            "SMTP_PROVIDER": "gmail",
            "SMTP_USERNAME": "user@gmail.com",
            "SMTP_PASSWORD": "pass",
            "SMTP_TIMEOUT": "60",
        }
        with patch.dict(os.environ, env, clear=False):
            svc = EmailServiceFactory.create_from_env()
            assert svc is not None
            assert svc.config.timeout == 60

    def test_create_from_env_invalid_timeout_uses_default(self):
        env = {
            "SMTP_PROVIDER": "gmail",
            "SMTP_USERNAME": "user@gmail.com",
            "SMTP_PASSWORD": "pass",
            "SMTP_TIMEOUT": "not_a_number",
        }
        with patch.dict(os.environ, env, clear=False):
            svc = EmailServiceFactory.create_from_env()
            assert svc is not None
            assert svc.config.timeout == 30

    def test_create_from_env_custom_prefix(self):
        env = {
            "MY_PROVIDER": "gmail",
            "MY_USERNAME": "user@gmail.com",
            "MY_PASSWORD": "pass",
        }
        with patch.dict(os.environ, env, clear=False):
            svc = EmailServiceFactory.create_from_env(prefix="MY_")
            assert svc is not None

    def test_create_from_env_from_name(self):
        env = {
            "SMTP_PROVIDER": "gmail",
            "SMTP_USERNAME": "user@gmail.com",
            "SMTP_PASSWORD": "pass",
            "SMTP_FROM_NAME": "Custom Name",
        }
        with patch.dict(os.environ, env, clear=False):
            svc = EmailServiceFactory.create_from_env()
            assert svc is not None
            assert svc.config.from_name == "Custom Name"

    def test_create_from_env_from_email_fallback_custom(self):
        env = {
            "SMTP_PROVIDER": "custom",
            "SMTP_USERNAME": "user",
            "SMTP_PASSWORD": "pass",
            "SMTP_SERVER": "mail.test.com",
            "SMTP_PORT": "587",
            "SMTP_FROM_EMAIL": "custom@test.com",
        }
        with patch.dict(os.environ, env, clear=False):
            svc = EmailServiceFactory.create_from_env()
            assert svc is not None
            assert svc.config.from_email == "custom@test.com"

    def test_create_from_env_from_email_defaults_to_username(self):
        env = {
            "SMTP_PROVIDER": "gmail",
            "SMTP_USERNAME": "user@gmail.com",
            "SMTP_PASSWORD": "pass",
        }
        with patch.dict(os.environ, env, clear=False):
            svc = EmailServiceFactory.create_from_env()
            assert svc is not None
            assert svc.config.from_email == "user@gmail.com"

    def test_create_from_env_tls_ssl_flags(self):
        env = {
            "SMTP_PROVIDER": "custom",
            "SMTP_USERNAME": "user",
            "SMTP_PASSWORD": "pass",
            "SMTP_SERVER": "mail.test.com",
            "SMTP_PORT": "465",
            "SMTP_USE_TLS": "false",
            "SMTP_USE_SSL": "true",
        }
        with patch.dict(os.environ, env, clear=False):
            svc = EmailServiceFactory.create_from_env()
            assert svc is not None
            assert svc.config.use_tls is False
            assert svc.config.use_ssl is True
