from fastapi.testclient import TestClient
from api.main import app
from notifications.notification_preferences import NotificationPreferences, AlertType, AlertFrequency
from unittest.mock import MagicMock, patch

client = TestClient(app)

# Mock API Key
HEADERS = {"X-API-Key": "test-key"}

@patch("api.routers.settings.PREFS_MANAGER")
@patch("api.auth.get_settings")
def test_get_settings(mock_get_settings, mock_prefs_manager):
    # Mock Auth
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings
    
    # Mock Preferences
    mock_prefs = MagicMock(spec=NotificationPreferences)
    mock_prefs.is_alert_enabled.return_value = True
    mock_prefs.alert_frequency = AlertFrequency.WEEKLY
    mock_prefs.expert_mode = True
    mock_prefs.marketing_emails = False
    
    mock_prefs_manager.get_preferences.return_value = mock_prefs
    
    response = client.get("/api/v1/settings/notifications", headers=HEADERS)
    
    assert response.status_code == 200
    data = response.json()
    assert data["email_digest"]
    assert data["frequency"] == "weekly"
    assert data["expert_mode"]
    assert not data["marketing_emails"]

@patch("api.routers.settings.PREFS_MANAGER")
@patch("api.auth.get_settings")
def test_update_settings(mock_get_settings, mock_prefs_manager):
    # Mock Auth
    mock_settings = MagicMock()
    mock_settings.api_access_key = "test-key"
    mock_get_settings.return_value = mock_settings
    
    # Mock Preferences
    mock_prefs = MagicMock(spec=NotificationPreferences)
    mock_prefs.enabled_alerts = set()
    mock_prefs.alert_frequency = AlertFrequency.WEEKLY
    
    mock_prefs_manager.get_preferences.return_value = mock_prefs
    
    payload = {
        "email_digest": True,
        "frequency": "daily",
        "expert_mode": True,
        "marketing_emails": True
    }
    
    response = client.put("/api/v1/settings/notifications", json=payload, headers=HEADERS)
    
    assert response.status_code == 200
    data = response.json()
    assert data["email_digest"]
    assert data["frequency"] == "daily"
    
    # Verify save called
    assert mock_prefs_manager.save_preferences.called
    saved_prefs = mock_prefs_manager.save_preferences.call_args[0][0]
    assert AlertType.DIGEST in saved_prefs.enabled_alerts
    assert saved_prefs.alert_frequency == AlertFrequency.DAILY
    assert saved_prefs.expert_mode
    assert saved_prefs.marketing_emails
