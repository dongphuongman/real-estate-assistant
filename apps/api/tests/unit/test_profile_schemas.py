"""Unit tests for profile Pydantic schemas.

Task #88: User Profile Management
"""

from datetime import datetime

from api.routers.profile import (
    AvatarUploadResponse,
    DataExportRequest,
    DataExportResponse,
    DataExportStatusResponse,
    PrivacySettings,
    ProfileResponse,
    ProfileUpdate,
)


class TestProfileUpdate:
    """Tests for ProfileUpdate schema validation."""

    def test_empty_update(self):
        """Test empty update is valid."""
        update = ProfileUpdate()
        assert update.full_name is None
        assert update.phone is None
        assert update.bio is None
        assert update.timezone is None
        assert update.language is None

    def test_full_name_update(self):
        """Test updating full name."""
        update = ProfileUpdate(full_name="John Doe")
        assert update.full_name == "John Doe"

    def test_phone_update(self):
        """Test updating phone number."""
        update = ProfileUpdate(phone="+1 555 123 4567")
        assert update.phone == "+1 555 123 4567"

    def test_bio_update(self):
        """Test updating bio."""
        bio = "Real estate investor interested in Warsaw properties."
        update = ProfileUpdate(bio=bio)
        assert update.bio == bio

    def test_timezone_update(self):
        """Test updating timezone."""
        update = ProfileUpdate(timezone="Europe/Warsaw")
        assert update.timezone == "Europe/Warsaw"

    def test_language_update(self):
        """Test updating language."""
        update = ProfileUpdate(language="pl")
        assert update.language == "pl"

    def test_all_fields_update(self):
        """Test updating all fields."""
        update = ProfileUpdate(
            full_name="Jane Doe",
            phone="+48 123 456 789",
            bio="Looking for apartments in Krakow.",
            timezone="Europe/Krakow",
            language="pl",
        )
        assert update.full_name == "Jane Doe"
        assert update.phone == "+48 123 456 789"
        assert update.bio == "Looking for apartments in Krakow."
        assert update.timezone == "Europe/Krakow"
        assert update.language == "pl"

    def test_model_dump_exclude_unset(self):
        """Test model_dump with exclude_unset=True."""
        update = ProfileUpdate(full_name="Only Name", timezone="UTC")
        dump = update.model_dump(exclude_unset=True)
        assert "full_name" in dump
        assert "timezone" in dump
        assert "phone" not in dump
        assert "bio" not in dump


class TestPrivacySettings:
    """Tests for PrivacySettings schema validation."""

    def test_default_values(self):
        """Test default privacy settings."""
        settings = PrivacySettings()
        assert settings.profile_visible is True
        assert settings.activity_visible is False
        assert settings.show_email is False
        assert settings.show_phone is False
        assert settings.allow_contact is True

    def test_all_visible(self):
        """Test all settings visible."""
        settings = PrivacySettings(
            profile_visible=True,
            activity_visible=True,
            show_email=True,
            show_phone=True,
            allow_contact=True,
        )
        assert settings.profile_visible is True
        assert settings.activity_visible is True
        assert settings.show_email is True
        assert settings.show_phone is True
        assert settings.allow_contact is True

    def test_all_hidden(self):
        """Test all settings hidden."""
        settings = PrivacySettings(
            profile_visible=False,
            activity_visible=False,
            show_email=False,
            show_phone=False,
            allow_contact=False,
        )
        assert settings.profile_visible is False
        assert settings.activity_visible is False
        assert settings.show_email is False
        assert settings.show_phone is False
        assert settings.allow_contact is False

    def test_model_dump(self):
        """Test model_dump returns dict."""
        settings = PrivacySettings(profile_visible=False, show_email=True)
        dump = settings.model_dump()
        assert dump["profile_visible"] is False
        assert dump["show_email"] is True
        assert dump["activity_visible"] is False
        assert dump["show_phone"] is False
        assert dump["allow_contact"] is True


class TestDataExportRequest:
    """Tests for DataExportRequest schema validation."""

    def test_default_values(self):
        """Test default export request."""
        request = DataExportRequest()
        assert request.format == "json"
        assert request.include_favorites is True
        assert request.include_search_history is True
        assert request.include_documents is True

    def test_custom_format(self):
        """Test custom format."""
        request = DataExportRequest(format="csv")
        assert request.format == "csv"

    def test_selective_includes(self):
        """Test selective data includes."""
        request = DataExportRequest(
            include_favorites=True,
            include_search_history=False,
            include_documents=True,
        )
        assert request.include_favorites is True
        assert request.include_search_history is False
        assert request.include_documents is True

    def test_minimal_export(self):
        """Test minimal export (only profile)."""
        request = DataExportRequest(
            include_favorites=False,
            include_search_history=False,
            include_documents=False,
        )
        assert request.include_favorites is False
        assert request.include_search_history is False
        assert request.include_documents is False


class TestDataExportResponse:
    """Tests for DataExportResponse schema validation."""

    def test_response_creation(self):
        """Test creating export response."""
        now = datetime.now()
        response = DataExportResponse(
            export_id="export_123",
            status="pending",
            format="json",
            includes=["favorites", "documents"],
            created_at=now,
        )
        assert response.export_id == "export_123"
        assert response.status == "pending"
        assert response.format == "json"
        assert response.includes == ["favorites", "documents"]
        assert response.created_at == now

    def test_response_defaults(self):
        """Test export response with defaults."""
        now = datetime.now()
        response = DataExportResponse(
            export_id="export_456",
            format="json",
            includes=[],
            created_at=now,
        )
        assert response.status == "pending"


class TestDataExportStatusResponse:
    """Tests for DataExportStatusResponse schema validation."""

    def test_status_response_creation(self):
        """Test creating status response."""
        now = datetime.now()
        response = DataExportStatusResponse(
            export_id="export_789",
            status="processing",
            progress_percent=50,
            created_at=now,
        )
        assert response.export_id == "export_789"
        assert response.status == "processing"
        assert response.progress_percent == 50
        assert response.download_url is None
        assert response.expires_at is None
        assert response.error_message is None
        assert response.completed_at is None

    def test_status_response_completed(self):
        """Test completed status response."""
        now = datetime.now()
        response = DataExportStatusResponse(
            export_id="export_complete",
            status="completed",
            progress_percent=100,
            download_url="/uploads/exports/export_complete.json",
            expires_at=now,
            created_at=now,
            completed_at=now,
        )
        assert response.status == "completed"
        assert response.download_url is not None
        assert response.progress_percent == 100


class TestAvatarUploadResponse:
    """Tests for AvatarUploadResponse schema validation."""

    def test_response_creation(self):
        """Test creating avatar upload response."""
        response = AvatarUploadResponse(avatar_url="/uploads/avatars/test.png")
        assert response.avatar_url == "/uploads/avatars/test.png"
        assert response.message == "Avatar uploaded successfully"

    def test_custom_message(self):
        """Test avatar response with custom message."""
        response = AvatarUploadResponse(
            avatar_url="/uploads/avatars/custom.jpg",
            message="Avatar updated!",
        )
        assert response.message == "Avatar updated!"


class TestProfileResponse:
    """Tests for ProfileResponse schema validation."""

    def test_minimal_response(self):
        """Test minimal profile response."""
        now = datetime.now()
        response = ProfileResponse(
            id="user-123",
            email="test@example.com",
            created_at=now,
        )
        assert response.id == "user-123"
        assert response.email == "test@example.com"
        assert response.full_name is None
        assert response.timezone == "UTC"
        assert response.language == "en"
        assert response.is_active is True
        assert response.is_verified is False
        assert response.role == "user"

    def test_full_response(self):
        """Test full profile response."""
        now = datetime.now()
        response = ProfileResponse(
            id="user-456",
            email="full@example.com",
            full_name="Full User",
            phone="+1 555 123 4567",
            avatar_url="/uploads/avatars/avatar.png",
            timezone="America/New_York",
            language="en",
            bio="Software developer interested in real estate.",
            privacy_settings={"profile_visible": True},
            is_active=True,
            is_verified=True,
            role="admin",
            created_at=now,
            last_login_at=now,
            gdpr_consent_at=now,
        )
        assert response.id == "user-456"
        assert response.email == "full@example.com"
        assert response.full_name == "Full User"
        assert response.phone == "+1 555 123 4567"
        assert response.avatar_url == "/uploads/avatars/avatar.png"
        assert response.timezone == "America/New_York"
        assert response.language == "en"
        assert response.bio == "Software developer interested in real estate."
        assert response.privacy_settings == {"profile_visible": True}
        assert response.is_active is True
        assert response.is_verified is True
        assert response.role == "admin"
        assert response.last_login_at == now
        assert response.gdpr_consent_at == now

    def test_from_attributes(self):
        """Test model_validate from ORM object (from_attributes=True)."""

        class MockUser:
            id = "mock-123"
            email = "mock@example.com"
            full_name = "Mock User"
            phone = None
            avatar_url = None
            timezone = "UTC"
            language = "en"
            bio = None
            privacy_settings = {}
            is_active = True
            is_verified = False
            role = "user"
            created_at = datetime(2024, 1, 1, 0, 0, 0)
            last_login_at = None
            gdpr_consent_at = None

        response = ProfileResponse.model_validate(MockUser())
        assert response.id == "mock-123"
        assert response.email == "mock@example.com"
        assert response.full_name == "Mock User"
