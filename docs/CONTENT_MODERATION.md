# Content Moderation System

## Overview

X-Agent features a unique **Dual-Mode Content Moderation System** that provides flexibility for different operational contexts while maintaining security and compliance.

This is a **unique differentiator** that no other autonomous agent framework offers, allowing the same system to operate in both strictly regulated and research-focused environments.

## Moderation Modes

### Moderated Mode (Legal Mode)

**Purpose**: Compliance-focused operation with strict content filtering

**Features**:
- ✅ Strict content classification and filtering
- ✅ Policy-based enforcement
- ✅ Automatic blocking of illegal content
- ✅ Confirmation required for restricted operations
- ✅ Full audit trail
- ✅ Compliance with regulatory requirements

**Use Cases**:
- Enterprise production environments
- Regulated industries (healthcare, finance)
- Customer-facing applications
- Public deployments
- Compliance-mandated scenarios

**Content Categories**:
- **Safe**: Allowed without restrictions
- **Sensitive**: Allowed with caution flags (passwords, credentials)
- **Restricted**: Requires explicit confirmation (destructive operations)
- **Illegal**: Blocked completely (malicious activities)

### Unmoderated Mode (Freedom Mode)

**Purpose**: Maximum operational flexibility for research and specialized use cases

**Features**:
- ✅ No content restrictions
- ✅ Full operational freedom
- ✅ Enhanced responsibility logging
- ✅ Warning system for high-risk operations
- ✅ Explicit user acknowledgment required
- ✅ Legal disclaimer system

**Use Cases**:
- Research and development
- Security testing (authorized)
- Academic studies
- Internal tools with special authorization
- Edge cases requiring flexibility

**Important Notes**:
- Switching to unmoderated mode requires ADMIN role
- Requires explicit user acknowledgment of risks
- All operations are logged with enhanced detail
- Not recommended for production environments
- Users assume full responsibility for actions

## API Endpoints

### Get Moderation Status

```http
GET /moderation/status
Authorization: Bearer <token>
```

**Response**:
```json
{
  "mode": "moderated",
  "acknowledgment_given": false,
  "description": "Moderated mode: Strict content filtering and compliance enforcement"
}
```

**Required Role**: USER or higher

### Set Moderation Mode

```http
POST /moderation/mode
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "mode": "unmoderated",
  "user_acknowledgment": true
}
```

**Response**:
```json
{
  "success": true,
  "previous_mode": "moderated",
  "current_mode": "unmoderated",
  "message": "Successfully switched to unmoderated mode"
}
```

**Required Role**: ADMIN

**Notes**:
- Switching to unmoderated mode requires `user_acknowledgment: true`
- Switching to moderated mode does not require acknowledgment

### Check Content Moderation

```http
POST /moderation/check
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": {
    "action": "delete",
    "target": "database"
  }
}
```

**Response (Moderated Mode)**:
```json
{
  "allowed": false,
  "mode": "moderated",
  "category": "restricted",
  "message": "Content requires explicit confirmation",
  "requires_confirmation": true
}
```

**Response (Unmoderated Mode)**:
```json
{
  "allowed": true,
  "mode": "unmoderated",
  "category": "restricted",
  "message": "Content allowed in unmoderated mode",
  "warning": true
}
```

**Required Role**: USER or higher

### Acknowledge Risks

```http
POST /moderation/acknowledge-risks
Authorization: Bearer <admin_token>
```

**Response**:
```json
{
  "success": true,
  "message": "Risks acknowledged for unmoderated mode",
  "timestamp": "2025-11-11T06:30:00.000000+00:00"
}
```

**Required Role**: ADMIN

**Note**: Only applicable when in unmoderated mode

## Configuration

Add to your `.env` file or environment variables:

```bash
# Content Moderation
MODERATION_MODE=moderated  # or "unmoderated"
MODERATION_ENABLED=true
```

Or programmatically:

```python
from xagent.config import settings

settings.moderation_mode = "moderated"
settings.moderation_enabled = True
```

## Python SDK Usage

### Basic Usage

```python
from xagent.security.moderation import (
    ContentModerator,
    ModerationMode,
    get_moderator
)

# Get global moderator instance
moderator = get_moderator()

# Check current status
status = moderator.get_status()
print(f"Current mode: {status['mode']}")

# Moderate content
result = moderator.moderate_content({
    "action": "read",
    "file": "document.txt"
})

if result["allowed"]:
    print("Content is allowed")
else:
    print(f"Content blocked: {result['message']}")
```

### Switching Modes

```python
from xagent.security.moderation import ModerationMode, get_moderator

moderator = get_moderator()

# Switch to unmoderated mode (requires acknowledgment)
result = moderator.set_mode(
    ModerationMode.UNMODERATED,
    user_acknowledgment=True
)

if result["success"]:
    print("Switched to unmoderated mode")
else:
    print(f"Failed: {result['message']}")

# Switch back to moderated mode
result = moderator.set_mode(ModerationMode.MODERATED)
```

### Content Classification

```python
from xagent.security.moderation import ContentModerator, ContentCategory

moderator = ContentModerator()

# Classify different types of content
safe = moderator.classify_content({"action": "read", "file": "doc.txt"})
# Returns: ContentCategory.SAFE

sensitive = moderator.classify_content({"password": "secret123"})
# Returns: ContentCategory.SENSITIVE

restricted = moderator.classify_content({"action": "delete database"})
# Returns: ContentCategory.RESTRICTED

illegal = moderator.classify_content({"action": "exploit vulnerability"})
# Returns: ContentCategory.ILLEGAL
```

## Security Considerations

### Moderated Mode Security

1. **Illegal Content**: Automatically blocked with audit log
2. **Restricted Content**: Requires explicit confirmation
3. **Sensitive Content**: Allowed with caution flag
4. **Safe Content**: No restrictions

### Unmoderated Mode Security

1. **Enhanced Logging**: All operations logged with extra detail
2. **Warning System**: High-risk operations generate warnings
3. **Audit Trail**: Complete record of all actions
4. **User Responsibility**: Users explicitly acknowledge risks
5. **Admin Only**: Only ADMIN role can enable unmoderated mode

### Best Practices

1. **Use Moderated Mode by Default**: Start in moderated mode for all new deployments
2. **Limit Unmoderated Access**: Only grant to authorized users for specific purposes
3. **Regular Audits**: Review logs from unmoderated mode operations
4. **Clear Policies**: Document when unmoderated mode is appropriate
5. **Rotate Access**: Periodically review who has ADMIN access

## Compliance and Legal

### Moderated Mode Compliance

Moderated mode is designed to help organizations comply with:

- **GDPR**: Data protection and processing restrictions
- **HIPAA**: Healthcare data handling requirements
- **SOC 2**: Security and availability controls
- **ISO 27001**: Information security management
- **Industry Standards**: Various regulatory frameworks

### Unmoderated Mode Disclaimer

⚠️ **Important Legal Notice**:

Unmoderated mode removes content restrictions and is intended **ONLY** for:

1. Authorized research and development
2. Security testing with proper authorization
3. Academic studies in controlled environments
4. Internal tools with special permissions
5. Edge cases where restrictions would prevent legitimate work

**Users of unmoderated mode**:
- Assume full responsibility for all actions
- Must comply with all applicable laws and regulations
- Are subject to enhanced audit logging
- Must have explicit organizational authorization

**Organizations using unmoderated mode**:
- Should implement additional oversight mechanisms
- Must maintain comprehensive audit logs
- Should have clear policies for when unmoderated mode is appropriate
- May be subject to additional compliance requirements

## Monitoring and Auditing

### Audit Logs

All moderation decisions are logged with structured logging:

```python
# Example log entries

# Mode switch (WARNING level)
"Moderation mode changed from moderated to unmoderated (acknowledgment: True)"

# Content blocked (ERROR level)
"BLOCKED: Illegal content detected in moderated mode"

# High-risk in unmoderated mode (WARNING level)
"UNMODERATED MODE: High-risk content detected (restricted). No restrictions applied."
```

### Metrics

Monitor moderation activity through Prometheus metrics:

```
# Content moderation decisions
xagent_moderation_decisions_total{mode="moderated",category="safe",decision="allowed"}
xagent_moderation_decisions_total{mode="moderated",category="restricted",decision="blocked"}
xagent_moderation_decisions_total{mode="unmoderated",category="restricted",decision="allowed"}

# Mode switches
xagent_moderation_mode_switches_total{from="moderated",to="unmoderated"}
```

## Examples

### Example 1: Enterprise Production Deployment

```python
# config.py
MODERATION_MODE = "moderated"
MODERATION_ENABLED = True

# Application code
from xagent.security.moderation import get_moderator

moderator = get_moderator()

# All operations automatically moderated
user_input = get_user_request()
moderation_result = moderator.moderate_content(user_input)

if not moderation_result["allowed"]:
    return {
        "error": "Content not allowed",
        "reason": moderation_result["message"]
    }
    
# Proceed with safe content
process_request(user_input)
```

### Example 2: Research Environment

```python
# Research mode with proper safeguards
from xagent.security.moderation import ModerationMode, get_moderator

# Initialize in moderated mode
moderator = get_moderator()

# Only switch to unmoderated for authorized users
if user_has_research_authorization(current_user):
    # Explicit acknowledgment required
    result = moderator.set_mode(
        ModerationMode.UNMODERATED,
        user_acknowledgment=True
    )
    
    if result["success"]:
        # Log who enabled unmoderated mode
        audit_log.record(
            user=current_user,
            action="enabled_unmoderated_mode",
            timestamp=datetime.now()
        )
        
        # Perform research operations
        research_operation()
        
        # Switch back when done
        moderator.set_mode(ModerationMode.MODERATED)
```

### Example 3: Testing Scenario

```python
# Integration tests can use unmoderated mode
import pytest
from xagent.security.moderation import ModerationMode, get_moderator

@pytest.fixture
def unmoderated_testing():
    """Enable unmoderated mode for testing."""
    moderator = get_moderator()
    
    # Save original mode
    original_mode = moderator.mode
    
    # Switch to unmoderated for testing
    moderator.set_mode(ModerationMode.UNMODERATED, user_acknowledgment=True)
    
    yield moderator
    
    # Restore original mode
    moderator.set_mode(original_mode)

def test_restricted_operation(unmoderated_testing):
    """Test that would normally be restricted."""
    # Operations that would be blocked in moderated mode
    result = perform_test_operation()
    assert result["success"]
```

## Troubleshooting

### Issue: Cannot Switch to Unmoderated Mode

**Problem**: Getting "requires explicit user acknowledgment" error

**Solution**:
```python
# Make sure to include user_acknowledgment=True
result = moderator.set_mode(
    ModerationMode.UNMODERATED,
    user_acknowledgment=True  # This is required!
)
```

### Issue: Content Blocked Unexpectedly

**Problem**: Safe content is being blocked

**Solution**:
1. Check current moderation mode: `GET /moderation/status`
2. Review the content category returned by `/moderation/check`
3. Adjust keywords in moderation rules if needed
4. Consider using unmoderated mode for specific operations (with proper authorization)

### Issue: Unmoderated Mode Not Available

**Problem**: Cannot access unmoderated mode endpoints

**Solution**:
- Verify you have ADMIN role
- Check that `MODERATION_ENABLED=true` in configuration
- Ensure authentication token includes proper scopes

## FAQ

**Q: Why would I need unmoderated mode?**

A: Unmoderated mode is designed for scenarios where content restrictions would prevent legitimate work, such as security research, academic studies, or internal tools with special authorization.

**Q: Is unmoderated mode safe?**

A: Unmoderated mode removes content restrictions but maintains enhanced logging and warning systems. It should only be used by authorized users who understand and accept the risks.

**Q: Can regular users switch to unmoderated mode?**

A: No, only users with ADMIN role can switch moderation modes.

**Q: What happens to existing operations when I switch modes?**

A: Mode switches are immediate but only affect new operations. In-flight operations complete under their original mode.

**Q: How do I customize moderation rules?**

A: You can extend the `ContentModerator` class and override the `classify_content` method with custom classification logic.

**Q: Does moderation impact performance?**

A: Minimal. Content classification is keyword-based and very fast. Most operations add less than 1ms overhead.

## Roadmap

Future enhancements planned for the moderation system:

- **v0.2.1**: ML-based content classification
- **v0.2.2**: Custom moderation policies per user/tenant
- **v0.3.0**: Integration with external moderation APIs
- **v0.3.0**: Advanced analytics and reporting
- **v0.4.0**: Multi-language content moderation

## Support

For questions or issues with the moderation system:

- GitHub Issues: https://github.com/UnknownEngineOfficial/X-Agent/issues
- Documentation: https://github.com/UnknownEngineOfficial/X-Agent/docs
- Security: security@xagent.dev (for security-related concerns)
