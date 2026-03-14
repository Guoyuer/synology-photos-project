"""Unit tests for session_manager.py — datetime handling."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from session_manager import is_session_expired, SESSION_EXPIRY_HOURS


class TestIsSessionExpired:
    def test_none_session_is_expired(self):
        assert is_session_expired(None) is True

    def test_missing_last_used_is_expired(self):
        assert is_session_expired({"sid": "x"}) is True

    def test_recent_utc_aware_not_expired(self):
        recent = datetime.now(timezone.utc).isoformat()
        assert is_session_expired({"last_used": recent}) is False

    def test_old_utc_aware_is_expired(self):
        old = (datetime.now(timezone.utc) - timedelta(hours=SESSION_EXPIRY_HOURS + 1)).isoformat()
        assert is_session_expired({"last_used": old}) is True

    def test_legacy_naive_timestamp_not_expired(self):
        """Backward compat: naive timestamps (pre-UTC migration) should still work."""
        recent = datetime.now().isoformat()  # naive, like old code produced
        assert is_session_expired({"last_used": recent}) is False

    def test_legacy_naive_timestamp_expired(self):
        old = (datetime.now() - timedelta(hours=SESSION_EXPIRY_HOURS + 1)).isoformat()
        assert is_session_expired({"last_used": old}) is True
