"""Tests for RBAC permissions."""

import pytest
from unittest.mock import MagicMock

from app.core.permissions import has_permission, get_permissions_for_role
from app.models.user import UserRole


class TestRBACPermissions:
    def _make_user(self, role: UserRole, superadmin: bool = False):
        user = MagicMock()
        user.role = role
        user.is_superadmin = superadmin
        return user

    def test_owner_has_all_permissions(self):
        user = self._make_user(UserRole.OWNER)
        assert has_permission(user, "posts.publish") is True
        assert has_permission(user, "billing.manage") is True
        assert has_permission(user, "members.manage") is True
        assert has_permission(user, "any.random.perm") is True  # wildcard

    def test_viewer_read_only(self):
        user = self._make_user(UserRole.VIEWER)
        assert has_permission(user, "brands.read") is True
        assert has_permission(user, "posts.read") is True
        assert has_permission(user, "posts.create") is False
        assert has_permission(user, "posts.publish") is False
        assert has_permission(user, "members.manage") is False

    def test_editor_can_create_not_publish(self):
        user = self._make_user(UserRole.EDITOR)
        assert has_permission(user, "posts.create") is True
        assert has_permission(user, "posts.publish") is False
        assert has_permission(user, "knowledge.write") is True
        assert has_permission(user, "billing.manage") is False

    def test_manager_can_publish_and_approve(self):
        user = self._make_user(UserRole.MANAGER)
        assert has_permission(user, "posts.publish") is True
        assert has_permission(user, "approvals.review") is True
        assert has_permission(user, "conversations.reply") is True
        assert has_permission(user, "billing.manage") is False

    def test_support_agent_can_reply(self):
        user = self._make_user(UserRole.SUPPORT_AGENT)
        assert has_permission(user, "conversations.read") is True
        assert has_permission(user, "conversations.reply") is True
        assert has_permission(user, "posts.create") is False
        assert has_permission(user, "posts.publish") is False

    def test_admin_can_connect_social(self):
        user = self._make_user(UserRole.ADMIN)
        assert has_permission(user, "social.connect") is True
        assert has_permission(user, "members.manage") is True
        assert has_permission(user, "audit.read") is True

    def test_superadmin_overrides_all(self):
        user = self._make_user(UserRole.VIEWER, superadmin=True)
        assert has_permission(user, "posts.publish") is True
        assert has_permission(user, "billing.manage") is True

    def test_role_permissions_are_sets(self):
        for role in UserRole:
            perms = get_permissions_for_role(role)
            assert isinstance(perms, set)
