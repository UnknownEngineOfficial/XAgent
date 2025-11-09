"""Tests for security policy layer with enhanced rule engine."""

import pytest

from xagent.security.policy import PolicyAction, PolicyLayer, PolicyRule


class TestPolicyRuleBasic:
    """Test basic policy rule functionality."""

    def test_simple_keyword_match(self):
        """Test simple keyword matching."""
        rule = PolicyRule(
            name="test_delete",
            action=PolicyAction.BLOCK,
            condition="delete",
        )

        context = {"action": "delete", "target": "file.txt"}
        assert rule.evaluate(context) is True

        context = {"action": "read", "target": "file.txt"}
        assert rule.evaluate(context) is False

    def test_no_condition_always_matches(self):
        """Test that rule without condition always matches."""
        rule = PolicyRule(
            name="always_match",
            action=PolicyAction.ALLOW,
            condition=None,
        )

        assert rule.evaluate({}) is True
        assert rule.evaluate({"any": "context"}) is True

    def test_case_insensitive_matching(self):
        """Test case-insensitive keyword matching."""
        rule = PolicyRule(
            name="test_case",
            action=PolicyAction.BLOCK,
            condition="DELETE",
        )

        context = {"action": "delete"}
        assert rule.evaluate(context) is True

        context = {"action": "Delete"}
        assert rule.evaluate(context) is True


class TestPolicyRuleLogicalOperators:
    """Test logical operators in policy rules."""

    def test_and_operator(self):
        """Test AND operator."""
        rule = PolicyRule(
            name="test_and",
            action=PolicyAction.BLOCK,
            condition="delete AND system",
        )

        # Both present
        context = {"action": "delete", "target": "system"}
        assert rule.evaluate(context) is True

        # Only one present
        context = {"action": "delete", "target": "user"}
        assert rule.evaluate(context) is False

        # Neither present
        context = {"action": "read", "target": "user"}
        assert rule.evaluate(context) is False

    def test_or_operator(self):
        """Test OR operator."""
        rule = PolicyRule(
            name="test_or",
            action=PolicyAction.BLOCK,
            condition="delete OR remove",
        )

        # First present
        context = {"action": "delete"}
        assert rule.evaluate(context) is True

        # Second present
        context = {"action": "remove"}
        assert rule.evaluate(context) is True

        # Both present
        context = {"action": "delete and remove"}
        assert rule.evaluate(context) is True

        # Neither present
        context = {"action": "read"}
        assert rule.evaluate(context) is False

    def test_not_operator(self):
        """Test NOT operator."""
        rule = PolicyRule(
            name="test_not",
            action=PolicyAction.BLOCK,
            condition="NOT test",
        )

        # Test NOT present - should match
        context = {"action": "production"}
        assert rule.evaluate(context) is True

        # Test present - should not match
        context = {"action": "test"}
        assert rule.evaluate(context) is False

    def test_combined_operators(self):
        """Test combining multiple operators."""
        # AND has higher precedence than OR
        rule = PolicyRule(
            name="test_combined",
            action=PolicyAction.BLOCK,
            condition="delete AND system OR remove AND config",
        )

        # delete AND system = True
        context = {"action": "delete", "target": "system"}
        assert rule.evaluate(context) is True

        # remove AND config = True
        context = {"action": "remove", "target": "config"}
        assert rule.evaluate(context) is True

        # Neither combination true
        context = {"action": "delete", "target": "user"}
        assert rule.evaluate(context) is False


class TestPolicyRuleParentheses:
    """Test parentheses in policy expressions."""

    def test_simple_parentheses(self):
        """Test simple parenthesized expressions."""
        rule = PolicyRule(
            name="test_parens",
            action=PolicyAction.BLOCK,
            condition="(delete OR remove) AND system",
        )

        # delete AND system
        context = {"action": "delete", "target": "system"}
        assert rule.evaluate(context) is True

        # remove AND system
        context = {"action": "remove", "target": "system"}
        assert rule.evaluate(context) is True

        # delete without system
        context = {"action": "delete", "target": "user"}
        assert rule.evaluate(context) is False

    def test_nested_parentheses(self):
        """Test nested parenthesized expressions."""
        rule = PolicyRule(
            name="test_nested",
            action=PolicyAction.BLOCK,
            condition="((delete OR remove) AND system) OR critical",
        )

        # Inner: delete AND system = True
        context = {"action": "delete", "target": "system"}
        assert rule.evaluate(context) is True

        # Critical alone matches OR
        context = {"action": "critical"}
        assert rule.evaluate(context) is True

        # Neither matches
        context = {"action": "read", "target": "user"}
        assert rule.evaluate(context) is False

    def test_not_with_parentheses(self):
        """Test NOT operator with parentheses."""
        rule = PolicyRule(
            name="test_not_parens",
            action=PolicyAction.BLOCK,
            condition="NOT (test OR development)",
        )

        # Neither test nor development
        context = {"env": "production"}
        assert rule.evaluate(context) is True

        # Has test
        context = {"env": "test"}
        assert rule.evaluate(context) is False

        # Has development
        context = {"env": "development"}
        assert rule.evaluate(context) is False


class TestPolicyRuleComplexExpressions:
    """Test complex real-world policy expressions."""

    def test_file_deletion_policy(self):
        """Test realistic file deletion policy."""
        rule = PolicyRule(
            name="file_deletion",
            action=PolicyAction.REQUIRE_CONFIRMATION,
            condition="(delete OR remove) AND (system OR config OR important)",
        )

        # Delete system file - should require confirmation
        context = {"action": "delete", "path": "/etc/system.conf"}
        assert rule.evaluate(context) is True

        # Remove config - should require confirmation
        context = {"action": "remove", "path": "important.config"}
        assert rule.evaluate(context) is True

        # Delete user file - should not match
        context = {"action": "delete", "path": "/home/user/temp.txt"}
        assert rule.evaluate(context) is False

    def test_api_rate_limit_policy(self):
        """Test API rate limiting policy."""
        rule = PolicyRule(
            name="rate_limit",
            action=PolicyAction.BLOCK,
            condition="api AND (excessive OR limit OR quota)",
        )

        # API with excessive calls
        context = {"type": "api", "status": "excessive calls"}
        assert rule.evaluate(context) is True

        # API limit reached
        context = {"type": "api", "message": "rate limit reached"}
        assert rule.evaluate(context) is True

        # Normal API call
        context = {"type": "api", "status": "ok"}
        assert rule.evaluate(context) is False

    def test_security_critical_policy(self):
        """Test security critical operations policy."""
        rule = PolicyRule(
            name="security_critical",
            action=PolicyAction.BLOCK,
            condition="(modify OR change OR update) AND (security OR auth OR credentials) AND NOT test",
        )

        # Modify security in production
        context = {"action": "modify", "target": "security settings", "env": "production"}
        assert rule.evaluate(context) is True

        # Change credentials in production
        context = {"action": "change", "target": "auth credentials", "env": "prod"}
        assert rule.evaluate(context) is True

        # Modify security in test - allowed
        context = {"action": "modify", "target": "security settings", "env": "test"}
        assert rule.evaluate(context) is False

        # Read security - not modify, so allowed
        context = {"action": "read", "target": "security settings"}
        assert rule.evaluate(context) is False


class TestPolicyLayer:
    """Test PolicyLayer class."""

    def test_check_action_with_matching_rule(self):
        """Test action checking with matching rule."""
        # Start with empty policy layer (no defaults)
        layer = PolicyLayer()
        layer.rules = []  # Clear default rules

        layer.add_rule(
            PolicyRule(
                name="block_delete",
                action=PolicyAction.BLOCK,
                condition="delete",
                message="Deletion blocked",
            )
        )

        result = layer.check_action({"action": "delete", "file": "test.txt"})

        assert result["blocked"] is True
        assert result["allowed"] is False
        assert result["rule"] == "block_delete"
        assert "blocked" in result["message"].lower()

    def test_check_action_no_matching_rule(self):
        """Test action checking with no matching rule."""
        layer = PolicyLayer()

        result = layer.check_action({"action": "read", "file": "test.txt"})

        assert result["allowed"] is True
        assert result["blocked"] is False
        assert result["rule"] is None

    def test_require_confirmation_action(self):
        """Test action requiring confirmation."""
        # Start with empty policy layer
        layer = PolicyLayer()
        layer.rules = []  # Clear default rules

        layer.add_rule(
            PolicyRule(
                name="confirm_delete",
                action=PolicyAction.REQUIRE_CONFIRMATION,
                condition="delete AND important",
            )
        )

        result = layer.check_action({"action": "delete", "file": "important.txt"})

        assert result["requires_confirmation"] is True
        assert result["blocked"] is False
        assert result["rule"] == "confirm_delete"

    def test_add_and_remove_rules(self):
        """Test adding and removing rules."""
        layer = PolicyLayer()

        # Add rule
        rule = PolicyRule(name="test_rule", action=PolicyAction.BLOCK, condition="test")
        layer.add_rule(rule)

        result = layer.check_action({"action": "test"})
        assert result["blocked"] is True

        # Remove rule
        layer.remove_rule("test_rule")

        result = layer.check_action({"action": "test"})
        assert result["allowed"] is True

    def test_default_policies_loaded(self):
        """Test that default policies are loaded."""
        layer = PolicyLayer()

        # Should have default rules
        assert len(layer.rules) > 0

        # Check for some default rules
        rule_names = [rule.name for rule in layer.rules]
        assert any("delete" in name.lower() for name in rule_names)


class TestPolicyRuleEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_condition(self):
        """Test rule with empty condition."""
        rule = PolicyRule(
            name="empty",
            action=PolicyAction.ALLOW,
            condition="",
        )

        # Empty condition should match nothing
        context = {"any": "value"}
        assert rule.evaluate(context) is False

    def test_whitespace_in_condition(self):
        """Test handling of whitespace."""
        rule = PolicyRule(
            name="whitespace",
            action=PolicyAction.BLOCK,
            condition="  delete   AND   system  ",
        )

        context = {"action": "delete", "target": "system"}
        assert rule.evaluate(context) is True

    def test_special_characters_in_context(self):
        """Test context with special characters."""
        rule = PolicyRule(
            name="special",
            action=PolicyAction.BLOCK,
            condition="delete",
        )

        context = {"action": "delete", "path": "/path/to/file.txt", "user": "admin@example.com"}
        assert rule.evaluate(context) is True

    def test_unmatched_parenthesis(self):
        """Test handling of unmatched parentheses."""
        rule = PolicyRule(
            name="unmatched",
            action=PolicyAction.BLOCK,
            condition="(delete AND system",
        )

        # Should still work, treating as regular expression
        context = {"action": "delete", "target": "system"}
        # The implementation should handle this gracefully
        result = rule.evaluate(context)
        assert isinstance(result, bool)

    def test_multiple_spaces_between_operators(self):
        """Test multiple spaces between operators."""
        rule = PolicyRule(
            name="spaces",
            action=PolicyAction.BLOCK,
            condition="delete    AND     system",
        )

        context = {"action": "delete", "target": "system"}
        assert rule.evaluate(context) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
