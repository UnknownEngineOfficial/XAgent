"""Tests for content moderation system."""

import pytest

from xagent.security.moderation import (
    ContentCategory,
    ContentModerator,
    ModerationMode,
    get_moderator,
    set_moderation_mode,
)


class TestContentModerator:
    """Tests for ContentModerator class."""

    def test_initialization_default_mode(self) -> None:
        """Test moderator initializes with default moderated mode."""
        moderator = ContentModerator()
        assert moderator.mode == ModerationMode.MODERATED
        assert not moderator._acknowledgment_given

    def test_initialization_unmoderated_mode(self) -> None:
        """Test moderator can initialize in unmoderated mode."""
        moderator = ContentModerator(mode=ModerationMode.UNMODERATED)
        assert moderator.mode == ModerationMode.UNMODERATED

    def test_set_mode_to_unmoderated_without_acknowledgment(self) -> None:
        """Test switching to unmoderated mode requires acknowledgment."""
        moderator = ContentModerator()
        result = moderator.set_mode(ModerationMode.UNMODERATED, user_acknowledgment=False)

        assert not result["success"]
        assert result["requires_acknowledgment"]
        assert moderator.mode == ModerationMode.MODERATED  # Should not have changed

    def test_set_mode_to_unmoderated_with_acknowledgment(self) -> None:
        """Test switching to unmoderated mode with acknowledgment."""
        moderator = ContentModerator()
        result = moderator.set_mode(ModerationMode.UNMODERATED, user_acknowledgment=True)

        assert result["success"]
        assert result["current_mode"] == "unmoderated"
        assert moderator.mode == ModerationMode.UNMODERATED
        assert moderator._acknowledgment_given

    def test_set_mode_to_moderated(self) -> None:
        """Test switching to moderated mode doesn't require acknowledgment."""
        moderator = ContentModerator(mode=ModerationMode.UNMODERATED)
        result = moderator.set_mode(ModerationMode.MODERATED, user_acknowledgment=False)

        assert result["success"]
        assert result["current_mode"] == "moderated"
        assert moderator.mode == ModerationMode.MODERATED

    def test_classify_safe_content(self) -> None:
        """Test classification of safe content."""
        moderator = ContentModerator()
        content = {"action": "get_file", "path": "/home/user/document.txt"}
        category = moderator.classify_content(content)
        assert category == ContentCategory.SAFE

    def test_classify_sensitive_content(self) -> None:
        """Test classification of sensitive content."""
        moderator = ContentModerator()
        content = {"action": "store", "data": {"password": "secret123"}}
        category = moderator.classify_content(content)
        assert category == ContentCategory.SENSITIVE

    def test_classify_restricted_content(self) -> None:
        """Test classification of restricted content."""
        moderator = ContentModerator()
        content = {"action": "execute", "command": "delete database users"}
        category = moderator.classify_content(content)
        assert category == ContentCategory.RESTRICTED

    def test_classify_illegal_content(self) -> None:
        """Test classification of illegal content."""
        moderator = ContentModerator()
        content = {"action": "hack", "target": "exploit vulnerability in system"}
        category = moderator.classify_content(content)
        assert category == ContentCategory.ILLEGAL

    def test_moderate_safe_content_in_moderated_mode(self) -> None:
        """Test safe content is allowed in moderated mode."""
        moderator = ContentModerator(mode=ModerationMode.MODERATED)
        content = {"action": "read", "file": "document.txt"}
        result = moderator.moderate_content(content)

        assert result["allowed"]
        assert result["mode"] == "moderated"
        assert result["category"] == "safe"

    def test_moderate_sensitive_content_in_moderated_mode(self) -> None:
        """Test sensitive content requires caution in moderated mode."""
        moderator = ContentModerator(mode=ModerationMode.MODERATED)
        content = {"action": "store", "password": "secret123"}
        result = moderator.moderate_content(content)

        assert result["allowed"]
        assert result["mode"] == "moderated"
        assert result["category"] == "sensitive"
        assert result["caution"]

    def test_moderate_restricted_content_in_moderated_mode(self) -> None:
        """Test restricted content requires confirmation in moderated mode."""
        moderator = ContentModerator(mode=ModerationMode.MODERATED)
        content = {"action": "delete", "target": "delete database"}
        result = moderator.moderate_content(content)

        assert not result["allowed"]
        assert result["mode"] == "moderated"
        assert result["category"] == "restricted"
        assert result["requires_confirmation"]

    def test_moderate_illegal_content_in_moderated_mode(self) -> None:
        """Test illegal content is blocked in moderated mode."""
        moderator = ContentModerator(mode=ModerationMode.MODERATED)
        content = {"action": "attack", "command": "ddos attack"}
        result = moderator.moderate_content(content)

        assert not result["allowed"]
        assert result["mode"] == "moderated"
        assert result["category"] == "illegal"
        assert result["requires_review"]

    def test_moderate_all_content_allowed_in_unmoderated_mode(self) -> None:
        """Test all content is allowed in unmoderated mode."""
        moderator = ContentModerator(mode=ModerationMode.UNMODERATED)

        # Test illegal content
        illegal_content = {"action": "exploit vulnerability"}
        result = moderator.moderate_content(illegal_content)
        assert result["allowed"]
        assert result["warning"]

        # Test restricted content
        restricted_content = {"action": "delete database"}
        result = moderator.moderate_content(restricted_content)
        assert result["allowed"]
        assert result["warning"]

        # Test safe content
        safe_content = {"action": "read file"}
        result = moderator.moderate_content(safe_content)
        assert result["allowed"]
        assert not result.get("warning", False)

    def test_get_status_moderated_mode(self) -> None:
        """Test get status in moderated mode."""
        moderator = ContentModerator(mode=ModerationMode.MODERATED)
        status = moderator.get_status()

        assert status["mode"] == "moderated"
        assert not status["acknowledgment_given"]
        assert "strict content filtering" in status["description"].lower()

    def test_get_status_unmoderated_mode(self) -> None:
        """Test get status in unmoderated mode."""
        moderator = ContentModerator(mode=ModerationMode.UNMODERATED)
        status = moderator.get_status()

        assert status["mode"] == "unmoderated"
        assert "maximum operational flexibility" in status["description"].lower()

    def test_acknowledge_risks_in_unmoderated_mode(self) -> None:
        """Test acknowledging risks in unmoderated mode."""
        moderator = ContentModerator(mode=ModerationMode.UNMODERATED)
        result = moderator.acknowledge_risks()

        assert result["success"]
        assert moderator._acknowledgment_given

    def test_acknowledge_risks_in_moderated_mode(self) -> None:
        """Test acknowledging risks fails in moderated mode."""
        moderator = ContentModerator(mode=ModerationMode.MODERATED)
        result = moderator.acknowledge_risks()

        assert not result["success"]
        assert not moderator._acknowledgment_given


class TestGlobalModerator:
    """Tests for global moderator functions."""

    def test_get_moderator_singleton(self) -> None:
        """Test get_moderator returns the same instance."""
        moderator1 = get_moderator()
        moderator2 = get_moderator()
        assert moderator1 is moderator2

    def test_set_moderation_mode_global(self) -> None:
        """Test setting global moderation mode."""
        # Reset to moderated
        set_moderation_mode(ModerationMode.MODERATED, user_acknowledgment=False)
        moderator = get_moderator()
        assert moderator.mode == ModerationMode.MODERATED

        # Switch to unmoderated with acknowledgment
        result = set_moderation_mode(ModerationMode.UNMODERATED, user_acknowledgment=True)
        assert result["success"]
        assert moderator.mode == ModerationMode.UNMODERATED


class TestContentClassification:
    """Tests for content classification edge cases."""

    def test_classify_mixed_keywords(self) -> None:
        """Test content with multiple keyword types."""
        moderator = ContentModerator()

        # Illegal keywords take precedence
        content = {
            "action": "hack system with password",  # Has both illegal and sensitive
        }
        category = moderator.classify_content(content)
        assert category == ContentCategory.ILLEGAL

    def test_classify_case_insensitive(self) -> None:
        """Test classification is case insensitive."""
        moderator = ContentModerator()

        content_lower = {"action": "delete database"}
        content_upper = {"action": "DELETE DATABASE"}
        content_mixed = {"action": "DeLeTe DaTaBaSe"}

        assert moderator.classify_content(content_lower) == ContentCategory.RESTRICTED
        assert moderator.classify_content(content_upper) == ContentCategory.RESTRICTED
        assert moderator.classify_content(content_mixed) == ContentCategory.RESTRICTED

    def test_classify_empty_content(self) -> None:
        """Test classification of empty content."""
        moderator = ContentModerator()
        content = {}
        category = moderator.classify_content(content)
        assert category == ContentCategory.SAFE

    def test_classify_complex_nested_content(self) -> None:
        """Test classification of complex nested structures."""
        moderator = ContentModerator()
        content = {
            "operation": "user_action",
            "details": {
                "type": "update",
                "data": {"credentials": {"password": "test123"}},
            },
        }
        category = moderator.classify_content(content)
        assert category == ContentCategory.SENSITIVE


class TestModerationWorkflows:
    """Tests for complete moderation workflows."""

    def test_workflow_moderated_to_unmoderated_and_back(self) -> None:
        """Test complete workflow of switching modes."""
        moderator = ContentModerator(mode=ModerationMode.MODERATED)

        # Start in moderated mode - restricted content blocked
        restricted_content = {"action": "drop table users"}
        result = moderator.moderate_content(restricted_content)
        assert not result["allowed"]

        # Switch to unmoderated mode
        moderator.set_mode(ModerationMode.UNMODERATED, user_acknowledgment=True)

        # Now the same content is allowed
        result = moderator.moderate_content(restricted_content)
        assert result["allowed"]

        # Switch back to moderated mode
        moderator.set_mode(ModerationMode.MODERATED)

        # Content is blocked again
        result = moderator.moderate_content(restricted_content)
        assert not result["allowed"]

    def test_workflow_risk_acknowledgment(self) -> None:
        """Test workflow with risk acknowledgment."""
        moderator = ContentModerator(mode=ModerationMode.UNMODERATED)

        # Initially no acknowledgment
        status = moderator.get_status()
        assert not status["acknowledgment_given"]

        # Acknowledge risks
        result = moderator.acknowledge_risks()
        assert result["success"]

        # Now acknowledgment is recorded
        status = moderator.get_status()
        assert status["acknowledgment_given"]
