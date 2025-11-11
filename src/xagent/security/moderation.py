"""Content moderation system for X-Agent.

Provides dual-mode content moderation:
- Moderated Mode (Legal Mode): Strict content filtering and compliance
- Unmoderated Mode (Freedom Mode): Maximum operational flexibility
"""

from enum import Enum
from typing import Any

from xagent.utils.logging import get_logger

logger = get_logger(__name__)


class ModerationMode(str, Enum):
    """Content moderation modes."""

    MODERATED = "moderated"  # Legal mode - strict filtering
    UNMODERATED = "unmoderated"  # Freedom mode - no restrictions


class ContentCategory(str, Enum):
    """Content classification categories."""

    SAFE = "safe"
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"
    ILLEGAL = "illegal"


class ContentModerator:
    """
    Content moderation system with dual-mode support.

    In MODERATED mode:
    - Enforces strict content filtering
    - Applies compliance rules
    - Logs all moderation decisions
    - Requires acknowledgment for sensitive content

    In UNMODERATED mode:
    - No content restrictions
    - Full operational flexibility
    - Enhanced responsibility logging
    - Warning system for high-risk operations
    """

    def __init__(self, mode: ModerationMode = ModerationMode.MODERATED) -> None:
        """
        Initialize content moderator.

        Args:
            mode: Moderation mode (moderated or unmoderated)
        """
        self.mode = mode
        self._acknowledgment_given = False
        logger.info(f"Content moderator initialized in {mode.value} mode")

    def set_mode(self, mode: ModerationMode, user_acknowledgment: bool = False) -> dict[str, Any]:
        """
        Switch moderation mode.

        Args:
            mode: New moderation mode
            user_acknowledgment: User acknowledgment for mode switch

        Returns:
            Result of mode switch
        """
        if mode == ModerationMode.UNMODERATED and not user_acknowledgment:
            return {
                "success": False,
                "message": "Switching to unmoderated mode requires explicit user acknowledgment",
                "requires_acknowledgment": True,
            }

        previous_mode = self.mode
        self.mode = mode
        self._acknowledgment_given = user_acknowledgment

        logger.warning(
            f"Moderation mode changed from {previous_mode.value} to {mode.value} "
            f"(acknowledgment: {user_acknowledgment})"
        )

        return {
            "success": True,
            "previous_mode": previous_mode.value,
            "current_mode": mode.value,
            "message": f"Successfully switched to {mode.value} mode",
        }

    def classify_content(self, content: dict[str, Any]) -> ContentCategory:
        """
        Classify content into categories.

        Args:
            content: Content to classify

        Returns:
            Content category
        """
        # Convert content to string for analysis
        content_str = str(content).lower()

        # Check for illegal content indicators
        illegal_keywords = [
            "exploit vulnerability",
            "hack system",
            "steal credentials",
            "ddos attack",
            "malware",
            "ransomware",
        ]
        if any(keyword in content_str for keyword in illegal_keywords):
            return ContentCategory.ILLEGAL

        # Check for restricted content
        restricted_keywords = [
            "delete database",
            "drop table",
            "rm -rf /",
            "format drive",
            "modify system",
        ]
        if any(keyword in content_str for keyword in restricted_keywords):
            return ContentCategory.RESTRICTED

        # Check for sensitive content
        sensitive_keywords = [
            "password",
            "secret",
            "api_key",
            "token",
            "credential",
            "sensitive",
        ]
        if any(keyword in content_str for keyword in sensitive_keywords):
            return ContentCategory.SENSITIVE

        return ContentCategory.SAFE

    def moderate_content(self, content: dict[str, Any]) -> dict[str, Any]:
        """
        Moderate content based on current mode.

        Args:
            content: Content to moderate

        Returns:
            Moderation decision
        """
        category = self.classify_content(content)

        # In unmoderated mode, only log warnings but don't block
        if self.mode == ModerationMode.UNMODERATED:
            if category in (ContentCategory.RESTRICTED, ContentCategory.ILLEGAL):
                logger.warning(
                    f"UNMODERATED MODE: High-risk content detected ({category.value}). "
                    "No restrictions applied due to unmoderated mode."
                )
            return {
                "allowed": True,
                "mode": self.mode.value,
                "category": category.value,
                "message": "Content allowed in unmoderated mode",
                "warning": category in (ContentCategory.RESTRICTED, ContentCategory.ILLEGAL),
            }

        # In moderated mode, enforce strict filtering
        if category == ContentCategory.ILLEGAL:
            logger.error(f"BLOCKED: Illegal content detected in moderated mode")
            return {
                "allowed": False,
                "mode": self.mode.value,
                "category": category.value,
                "message": "Content blocked: Illegal content detected",
                "requires_review": True,
            }

        if category == ContentCategory.RESTRICTED:
            logger.warning(f"RESTRICTED: High-risk content requires confirmation")
            return {
                "allowed": False,
                "mode": self.mode.value,
                "category": category.value,
                "message": "Content requires explicit confirmation",
                "requires_confirmation": True,
            }

        if category == ContentCategory.SENSITIVE:
            logger.info(f"SENSITIVE: Content requires caution")
            return {
                "allowed": True,
                "mode": self.mode.value,
                "category": category.value,
                "message": "Content allowed with caution flag",
                "caution": True,
            }

        # Safe content
        return {
            "allowed": True,
            "mode": self.mode.value,
            "category": category.value,
            "message": "Content is safe",
        }

    def get_status(self) -> dict[str, Any]:
        """
        Get current moderation status.

        Returns:
            Current moderation status
        """
        return {
            "mode": self.mode.value,
            "acknowledgment_given": self._acknowledgment_given,
            "description": (
                "Moderated mode: Strict content filtering and compliance enforcement"
                if self.mode == ModerationMode.MODERATED
                else "Unmoderated mode: Maximum operational flexibility with enhanced logging"
            ),
        }

    def acknowledge_risks(self) -> dict[str, Any]:
        """
        Acknowledge risks of unmoderated mode.

        Returns:
            Acknowledgment status
        """
        if self.mode != ModerationMode.UNMODERATED:
            return {
                "success": False,
                "message": "Risk acknowledgment only applicable in unmoderated mode",
            }

        self._acknowledgment_given = True
        logger.info("User acknowledged risks of unmoderated mode")

        from datetime import datetime, timezone

        return {
            "success": True,
            "message": "Risks acknowledged for unmoderated mode",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Global moderator instance
_moderator: ContentModerator | None = None


def get_moderator() -> ContentModerator:
    """
    Get global content moderator instance.

    Returns:
        Content moderator instance
    """
    global _moderator
    if _moderator is None:
        _moderator = ContentModerator()
    return _moderator


def set_moderation_mode(
    mode: ModerationMode, user_acknowledgment: bool = False
) -> dict[str, Any]:
    """
    Set global moderation mode.

    Args:
        mode: New moderation mode
        user_acknowledgment: User acknowledgment for mode switch

    Returns:
        Result of mode switch
    """
    moderator = get_moderator()
    return moderator.set_mode(mode, user_acknowledgment)
