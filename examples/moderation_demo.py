#!/usr/bin/env python
"""Demo script for X-Agent Content Moderation System.

This script demonstrates the dual-mode content moderation system,
showing how to classify content, switch modes, and handle different
types of operations.
"""

from xagent.security.moderation import (
    ContentCategory,
    ContentModerator,
    ModerationMode,
    get_moderator,
)


def print_section(title: str) -> None:
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def demonstrate_content_classification() -> None:
    """Demonstrate content classification."""
    print_section("Content Classification Demo")

    moderator = ContentModerator()

    test_contents = [
        {"action": "read", "file": "document.txt", "description": "Read a file"},
        {
            "action": "store",
            "password": "secret123",
            "description": "Store credentials",
        },
        {"action": "delete database users", "description": "Delete database"},
        {"action": "exploit vulnerability", "description": "Malicious action"},
    ]

    for content in test_contents:
        description = content.pop("description")
        category = moderator.classify_content(content)
        print(f"\n{description}")
        print(f"  Content: {content}")
        print(f"  Category: {category.value.upper()}")


def demonstrate_moderated_mode() -> None:
    """Demonstrate moderated mode operation."""
    print_section("Moderated Mode (Legal Mode) Demo")

    moderator = ContentModerator(mode=ModerationMode.MODERATED)

    test_operations = [
        {"action": "read", "file": "document.txt"},
        {"action": "store", "password": "secret123"},
        {"action": "delete database users"},
        {"action": "exploit vulnerability"},
    ]

    for operation in test_operations:
        result = moderator.moderate_content(operation)
        print(f"\nOperation: {operation}")
        print(f"  Allowed: {result['allowed']}")
        print(f"  Category: {result['category']}")
        print(f"  Message: {result['message']}")

        if result.get("requires_confirmation"):
            print("  ⚠️  Requires explicit confirmation")
        if result.get("requires_review"):
            print("  ❌ Blocked - requires review")


def demonstrate_unmoderated_mode() -> None:
    """Demonstrate unmoderated mode operation."""
    print_section("Unmoderated Mode (Freedom Mode) Demo")

    moderator = ContentModerator(mode=ModerationMode.UNMODERATED)

    # Acknowledge risks
    acknowledgment = moderator.acknowledge_risks()
    print(f"\nRisks acknowledged: {acknowledgment['success']}")

    test_operations = [
        {"action": "read", "file": "document.txt"},
        {"action": "delete database users"},
        {"action": "exploit vulnerability"},
    ]

    for operation in test_operations:
        result = moderator.moderate_content(operation)
        print(f"\nOperation: {operation}")
        print(f"  Allowed: {result['allowed']}")
        print(f"  Category: {result['category']}")
        print(f"  Message: {result['message']}")

        if result.get("warning"):
            print("  ⚠️  WARNING: High-risk operation (but allowed)")


def demonstrate_mode_switching() -> None:
    """Demonstrate switching between modes."""
    print_section("Mode Switching Demo")

    moderator = ContentModerator(mode=ModerationMode.MODERATED)

    # Show initial status
    status = moderator.get_status()
    print(f"\nInitial Mode: {status['mode']}")
    print(f"Description: {status['description']}")

    # Try to switch without acknowledgment
    print("\n--- Attempting to switch to unmoderated without acknowledgment ---")
    result = moderator.set_mode(ModerationMode.UNMODERATED, user_acknowledgment=False)
    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")

    # Switch with acknowledgment
    print("\n--- Switching to unmoderated with acknowledgment ---")
    result = moderator.set_mode(ModerationMode.UNMODERATED, user_acknowledgment=True)
    print(f"Success: {result['success']}")
    print(f"Previous Mode: {result['previous_mode']}")
    print(f"Current Mode: {result['current_mode']}")

    # Switch back to moderated
    print("\n--- Switching back to moderated mode ---")
    result = moderator.set_mode(ModerationMode.MODERATED)
    print(f"Success: {result['success']}")
    print(f"Current Mode: {result['current_mode']}")


def demonstrate_workflow() -> None:
    """Demonstrate a complete workflow."""
    print_section("Complete Workflow Demo")

    moderator = get_moderator()  # Use global instance

    # Step 1: Check status
    print("\n1. Check current status")
    status = moderator.get_status()
    print(f"   Mode: {status['mode']}")

    # Step 2: Try a restricted operation in moderated mode
    print("\n2. Try restricted operation in moderated mode")
    restricted_op = {"action": "drop table users"}
    result = moderator.moderate_content(restricted_op)
    print(f"   Allowed: {result['allowed']}")
    print(f"   Message: {result['message']}")

    # Step 3: Switch to unmoderated mode for authorized work
    print("\n3. Switch to unmoderated mode (for authorized research)")
    moderator.set_mode(ModerationMode.UNMODERATED, user_acknowledgment=True)
    print("   Mode switched successfully")

    # Step 4: Same operation now allowed with warning
    print("\n4. Same operation in unmoderated mode")
    result = moderator.moderate_content(restricted_op)
    print(f"   Allowed: {result['allowed']}")
    print(f"   Warning: {result.get('warning', False)}")

    # Step 5: Switch back for safety
    print("\n5. Switch back to moderated mode")
    moderator.set_mode(ModerationMode.MODERATED)
    print("   Mode switched successfully")


def main() -> None:
    """Run all demonstrations."""
    print("\n" + "=" * 70)
    print("  X-Agent Content Moderation System Demo")
    print("  Dual-Mode: Moderated (Legal) & Unmoderated (Freedom)")
    print("=" * 70)

    try:
        demonstrate_content_classification()
        demonstrate_moderated_mode()
        demonstrate_unmoderated_mode()
        demonstrate_mode_switching()
        demonstrate_workflow()

        print("\n" + "=" * 70)
        print("  Demo Complete!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
