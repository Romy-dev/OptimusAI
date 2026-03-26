"""Tests for quota service."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import uuid

from app.services.quota_service import QuotaService, DEFAULT_LIMITS


class TestQuotaDefaults:
    def test_default_limits_exist(self):
        assert "max_brands" in DEFAULT_LIMITS
        assert "max_posts_per_month" in DEFAULT_LIMITS
        assert "max_documents" in DEFAULT_LIMITS
        assert "max_users" in DEFAULT_LIMITS

    def test_default_limits_are_reasonable(self):
        assert DEFAULT_LIMITS["max_brands"] >= 1
        assert DEFAULT_LIMITS["max_posts_per_month"] >= 10
        assert DEFAULT_LIMITS["max_documents"] >= 1
