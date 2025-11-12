# HTTP Client Tool Documentation

## Overview

The HTTP Client Tool provides secure HTTP/HTTPS request capabilities for the X-Agent with built-in security features to protect against common vulnerabilities and operational issues.

**Status**: ✅ Production Ready (2025-11-12)

## Features

### 1. **Security Features**

#### Domain Allowlist
- Only whitelisted domains can be accessed
- Supports wildcard patterns (e.g., `*.github.com`)
- Prevents requests to potentially malicious domains
- Case-insensitive matching

**Default Allowed Domains**:
- `*.github.com` - GitHub API access
- `*.googleapis.com` - Google APIs
- `api.openai.com` - OpenAI API
- `*.anthropic.com` - Anthropic API
- `httpbin.org` - Testing purposes

#### Secret Redaction
- Automatically redacts secrets from logs
- Supports multiple secret formats:
  - API keys (`api_key`, `apiKey`)
  - Bearer tokens
  - AWS access keys
  - Authorization headers
  - Passwords
  - Generic tokens

**Example**:
```python
# Original: Authorization: Bearer sk-1234567890
# Logged as: Authorization: ***REDACTED***
```

### 2. **Circuit Breaker Pattern**

Protects against cascading failures by tracking request success/failure rates.

#### States

**CLOSED** (Normal):
- All requests pass through
- Monitors failure count
- Opens if failures exceed threshold

**OPEN** (Failing):
- Blocks all requests fast-fail
- Prevents overwhelming failing service
- Attempts recovery after timeout

**HALF_OPEN** (Testing):
- Allows test requests
- Closes if requests succeed
- Reopens if requests fail

#### Configuration

```python
# Default settings
failure_threshold = 5      # Failures before opening
recovery_timeout = 60      # Seconds before retry
success_threshold = 2      # Successes to close
```

#### Per-Domain Circuits

Each domain has independent circuit breaker state:
```python
# example1.com circuit open
# example2.com circuit still closed
```

### 3. **Request Features**

#### Supported HTTP Methods
- GET
- POST
- PUT
- DELETE
- PATCH
- HEAD
- OPTIONS

#### Request Options
- **Headers**: Custom HTTP headers
- **Query Parameters**: URL query string
- **Body**: JSON object or plain text
- **Timeout**: 1-300 seconds (default: 30s)
- **Follow Redirects**: Enabled by default
- **SSL Verification**: Enabled by default

#### Response Handling
- Automatic JSON parsing for `application/json`
- Text extraction for other content types
- Request duration tracking
- Full header preservation

## Usage

### Basic GET Request

```python
from xagent.tools.langserve_tools import http_request

result = await http_request(
    url="https://api.github.com/users/octocat",
    method="GET"
)

if result["status"] == "success":
    print(f"Status: {result['status_code']}")
    print(f"Body: {result['body']}")
    print(f"Duration: {result['elapsed_ms']}ms")
else:
    print(f"Error: {result['error']}")
```

### POST Request with JSON Body

```python
result = await http_request(
    url="https://api.example.com/data",
    method="POST",
    headers={"Content-Type": "application/json"},
    body={"name": "test", "value": 123},
    timeout=60
)
```

### Request with Authentication

```python
result = await http_request(
    url="https://api.example.com/protected",
    method="GET",
    headers={
        "Authorization": "Bearer YOUR_TOKEN_HERE",
        "X-API-Key": "YOUR_API_KEY"
    }
)
# Secrets automatically redacted in logs
```

### Using the HTTP Client Directly

For advanced use cases, use the `HttpClient` class directly:

```python
from xagent.tools.http_client import HttpClient, HttpMethod

client = HttpClient()

try:
    result = await client.request(
        method=HttpMethod.GET,
        url="https://api.example.com/data",
        headers={"Authorization": "Bearer token"},
        timeout=30
    )
    print(result)
finally:
    await client.close()
```

## Configuration

### Environment Variables

```bash
# Domain Allowlist (comma-separated patterns)
HTTP_ALLOWED_DOMAINS="*.github.com,*.googleapis.com,api.openai.com"

# Circuit Breaker Settings
HTTP_CIRCUIT_FAILURE_THRESHOLD=5
HTTP_CIRCUIT_RECOVERY_TIMEOUT=60
HTTP_CIRCUIT_SUCCESS_THRESHOLD=2
```

### Settings File

```python
# config.py
class Settings(BaseSettings):
    http_allowed_domains: list[str] = [
        "*.github.com",
        "*.googleapis.com",
        "api.openai.com",
    ]
    
    http_circuit_failure_threshold: int = 5
    http_circuit_recovery_timeout: int = 60
    http_circuit_success_threshold: int = 2
```

## Error Handling

### Domain Not Allowed

```python
result = await http_request(url="https://evil.com")
# Returns:
# {
#   "status": "error",
#   "error": "Domain not allowed: Domain evil.com not in allowlist",
#   "url": "https://evil.com"
# }
```

### Circuit Breaker Open

```python
result = await http_request(url="https://failing-service.com")
# After 5 failures:
# {
#   "status": "error",
#   "error": "Circuit breaker open: Circuit open for failing-service.com, request blocked",
#   "url": "https://failing-service.com"
# }
```

### HTTP Error

```python
result = await http_request(url="https://api.example.com/not-found")
# {
#   "status": "error",
#   "error": "HTTP error: 404 Not Found",
#   "url": "https://api.example.com/not-found"
# }
```

## Monitoring

### Logs

All HTTP requests are logged with redacted secrets:

```
INFO: HTTP GET request to https://api.example.com/data
      headers={'Authorization': '***REDACTED***'}
      has_body=False
      
INFO: HTTP GET response: 200
      status_code=200
      elapsed_ms=145.3
      body_preview='{"status": "ok", ...'
```

### Circuit Breaker Events

```
INFO: Circuit breaker for example.com transitioning to HALF_OPEN
WARNING: Circuit breaker for example.com opened after 5 failures
INFO: Circuit breaker for example.com closed after recovery
WARNING: Circuit breaker for example.com reopened after failed recovery
```

### Security Events

```
WARNING: HTTP request blocked: Domain not allowed: evil.com
WARNING: HTTP request blocked by circuit breaker: Circuit open for failing.com
```

## Testing

### Unit Tests

Run the comprehensive test suite:

```bash
pytest tests/unit/test_http_client.py -v
```

**Test Coverage**:
- Input validation
- Circuit breaker states and transitions
- Secret redaction patterns
- Domain allowlist matching
- HTTP request/response handling
- Error handling
- Per-domain circuit isolation

**Test Results**: 25+ tests, 100% passing

### Integration Testing

Test with real endpoints:

```python
# Test with httpbin.org (allowed by default)
result = await http_request(
    url="https://httpbin.org/get",
    method="GET"
)
assert result["status"] == "success"
assert result["status_code"] == 200

# Test POST with JSON
result = await http_request(
    url="https://httpbin.org/post",
    method="POST",
    body={"test": "data"}
)
assert result["body"]["json"] == {"test": "data"}
```

## Security Considerations

### 1. Domain Allowlist
- **Always** configure appropriate domain patterns
- **Never** use `*` or overly broad patterns in production
- Review and update allowlist regularly
- Consider per-environment configurations

### 2. Secret Management
- Secrets are redacted in logs automatically
- Use environment variables or secret managers
- Never hardcode API keys or tokens
- Rotate secrets regularly

### 3. Rate Limiting
- Circuit breaker provides basic protection
- Consider additional rate limiting at API level
- Monitor request patterns for anomalies

### 4. SSL/TLS
- SSL verification enabled by default
- Disable only for testing with self-signed certificates
- Always use HTTPS in production

### 5. Timeouts
- Set appropriate timeouts for different endpoints
- Default 30s may be too short for long-running operations
- Maximum timeout is 300s (5 minutes)

## Best Practices

### 1. Error Handling

Always check the status field:

```python
result = await http_request(url=url, method="GET")

if result["status"] == "success":
    # Handle successful response
    data = result["body"]
else:
    # Handle error
    logger.error(f"Request failed: {result['error']}")
    # Implement retry logic if appropriate
```

### 2. Retry Logic

For transient failures, implement exponential backoff:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def make_request_with_retry(url):
    result = await http_request(url=url, method="GET")
    if result["status"] != "success":
        raise Exception(result["error"])
    return result
```

### 3. Circuit Breaker Monitoring

Monitor circuit breaker state in production:

```python
from xagent.tools.http_client import get_http_client

client = get_http_client()

# Check circuit state for a domain
domain = "api.example.com"
circuit = client.circuit_breaker._get_circuit(domain)

print(f"State: {circuit['state']}")
print(f"Failures: {circuit['failure_count']}")
print(f"Last Failure: {circuit['last_failure_time']}")
```

### 4. Response Size Limits

For large responses, implement size limits:

```python
result = await http_request(url=url, method="GET")

if result["status"] == "success":
    body = result["body"]
    if len(str(body)) > 1_000_000:  # 1MB limit
        logger.warning("Response too large, truncating")
        body = str(body)[:1_000_000]
```

## Performance

### Benchmarks

Typical performance metrics:

```
Small GET request:     10-50ms
Large GET request:     100-500ms
POST with JSON:        20-100ms
Circuit breaker check: <1ms
Secret redaction:      <1ms per pattern
```

### Optimization Tips

1. **Connection Pooling**: Client maintains connection pool automatically
2. **Keep-Alive**: HTTP keep-alive enabled by default
3. **Timeout Configuration**: Set appropriate timeouts per endpoint
4. **Concurrent Requests**: Use `asyncio.gather()` for parallel requests

```python
import asyncio

# Make multiple requests in parallel
results = await asyncio.gather(
    http_request(url="https://api1.com/data", method="GET"),
    http_request(url="https://api2.com/data", method="GET"),
    http_request(url="https://api3.com/data", method="GET"),
)
```

## Troubleshooting

### Domain Blocked

**Problem**: `Domain not allowed: Domain example.com not in allowlist`

**Solution**:
1. Add domain to allowlist in settings
2. Or use wildcard pattern: `*.example.com`

```python
# In config.py or environment
HTTP_ALLOWED_DOMAINS="*.example.com,other-domain.com"
```

### Circuit Breaker Open

**Problem**: `Circuit breaker open: Circuit open for api.example.com`

**Solution**:
1. Wait for recovery timeout (default 60s)
2. Check if target service is actually down
3. Adjust circuit breaker thresholds if too sensitive

### SSL Verification Error

**Problem**: `SSL certificate verification failed`

**Solution**:
1. Ensure target uses valid SSL certificate
2. For testing only, disable verification:

```python
result = await http_request(
    url=url,
    method="GET",
    verify_ssl=False  # Use only for testing!
)
```

### Timeout

**Problem**: Request times out

**Solution**:
1. Increase timeout value:

```python
result = await http_request(
    url=url,
    method="GET",
    timeout=120  # 2 minutes
)
```

2. Check if target service is responding slowly
3. Consider streaming for large responses

## Migration from Basic HTTP

### Old Code (Direct httpx)

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(url)
    data = response.json()
```

### New Code (Secure HTTP Tool)

```python
from xagent.tools.langserve_tools import http_request

result = await http_request(url=url, method="GET")
if result["status"] == "success":
    data = result["body"]
```

**Benefits**:
- ✅ Domain allowlist protection
- ✅ Circuit breaker for resilience
- ✅ Secret redaction in logs
- ✅ Comprehensive error handling
- ✅ Request/response logging

## Changelog

### Version 0.2.0 (2025-11-12)
- ✅ Initial implementation with security features
- ✅ Circuit breaker pattern
- ✅ Secret redaction
- ✅ Domain allowlist
- ✅ Comprehensive test suite
- ✅ Production-ready documentation

## Related Documentation

- [FEATURES.md](../FEATURES.md) - Feature overview
- [SECURITY.md](../SECURITY.md) - Security policies
- [API.md](API.md) - API reference
- [TESTING.md](TESTING.md) - Testing guide

## Support

For issues or questions:
- GitHub Issues: https://github.com/UnknownEngineOfficial/XAgent/issues
- Documentation: https://github.com/UnknownEngineOfficial/XAgent/tree/main/docs

---

**Status**: ✅ Production Ready  
**Version**: 0.2.0  
**Last Updated**: 2025-11-12
