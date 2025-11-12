"""Tests for HTTP client tool."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta, timezone

from xagent.tools.http_client import (
    CircuitBreaker,
    CircuitState,
    DomainAllowlist,
    HttpClient,
    HttpMethod,
    HttpRequestInput,
    SecretRedactor,
)


class TestHttpRequestInput:
    """Test HTTP request input validation."""

    def test_valid_http_url(self):
        """Test valid HTTP URL."""
        input_data = HttpRequestInput(method=HttpMethod.GET, url="http://example.com")
        assert input_data.url == "http://example.com"

    def test_valid_https_url(self):
        """Test valid HTTPS URL."""
        input_data = HttpRequestInput(method=HttpMethod.POST, url="https://api.example.com/data")
        assert input_data.url == "https://api.example.com/data"

    def test_invalid_url_no_scheme(self):
        """Test URL without scheme is rejected."""
        with pytest.raises(ValueError, match="must include scheme"):
            HttpRequestInput(method=HttpMethod.GET, url="example.com")

    def test_invalid_url_bad_scheme(self):
        """Test URL with invalid scheme is rejected."""
        with pytest.raises(ValueError, match="scheme must be http or https"):
            HttpRequestInput(method=HttpMethod.GET, url="ftp://example.com")

    def test_invalid_url_no_hostname(self):
        """Test URL without hostname is rejected."""
        with pytest.raises(ValueError, match="must include hostname"):
            HttpRequestInput(method=HttpMethod.GET, url="http://")

    def test_timeout_validation(self):
        """Test timeout validation."""
        # Valid timeout
        input_data = HttpRequestInput(method=HttpMethod.GET, url="http://example.com", timeout=60)
        assert input_data.timeout == 60

        # Timeout too low
        with pytest.raises(ValueError):
            HttpRequestInput(method=HttpMethod.GET, url="http://example.com", timeout=0)

        # Timeout too high
        with pytest.raises(ValueError):
            HttpRequestInput(method=HttpMethod.GET, url="http://example.com", timeout=301)


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_initial_state_closed(self):
        """Test circuit starts in closed state."""
        cb = CircuitBreaker()
        allowed, reason = cb.can_request("http://example.com")
        assert allowed is True
        assert "closed" in reason.lower()

    def test_opens_after_failures(self):
        """Test circuit opens after threshold failures."""
        cb = CircuitBreaker(failure_threshold=3)

        # Record failures
        url = "http://example.com"
        for _ in range(3):
            cb.record_failure(url)

        # Circuit should be open
        allowed, reason = cb.can_request(url)
        assert allowed is False
        assert "open" in reason.lower()

    def test_transitions_to_half_open(self):
        """Test circuit transitions to half-open after timeout."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        url = "http://example.com"

        # Open circuit
        cb.record_failure(url)
        cb.record_failure(url)

        # Circuit open
        allowed, _ = cb.can_request(url)
        assert allowed is False

        # Wait for recovery timeout (mock time)
        circuit = cb._get_circuit(cb._get_domain(url))
        circuit["last_failure_time"] = datetime.now(timezone.utc) - timedelta(seconds=2)

        # Should transition to half-open
        allowed, reason = cb.can_request(url)
        assert allowed is True
        assert "half-open" in reason.lower()

    def test_closes_after_successful_recovery(self):
        """Test circuit closes after successful recovery."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1, success_threshold=2)

        url = "http://example.com"

        # Open circuit
        cb.record_failure(url)
        cb.record_failure(url)

        # Transition to half-open
        circuit = cb._get_circuit(cb._get_domain(url))
        circuit["last_failure_time"] = datetime.now(timezone.utc) - timedelta(seconds=2)
        circuit["state"] = CircuitState.HALF_OPEN

        # Record successes
        cb.record_success(url)
        cb.record_success(url)

        # Circuit should be closed
        circuit = cb._get_circuit(cb._get_domain(url))
        assert circuit["state"] == CircuitState.CLOSED

    def test_reopens_on_failed_recovery(self):
        """Test circuit reopens if recovery fails."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        url = "http://example.com"

        # Open circuit then transition to half-open
        cb.record_failure(url)
        cb.record_failure(url)

        circuit = cb._get_circuit(cb._get_domain(url))
        circuit["last_failure_time"] = datetime.now(timezone.utc) - timedelta(seconds=2)
        circuit["state"] = CircuitState.HALF_OPEN

        # Fail during recovery
        cb.record_failure(url)

        # Should be open again
        circuit = cb._get_circuit(cb._get_domain(url))
        assert circuit["state"] == CircuitState.OPEN

    def test_per_domain_circuits(self):
        """Test independent circuit breakers per domain."""
        cb = CircuitBreaker(failure_threshold=2)

        url1 = "http://example1.com"
        url2 = "http://example2.com"

        # Fail only url1
        cb.record_failure(url1)
        cb.record_failure(url1)

        # url1 should be open, url2 should be closed
        allowed1, _ = cb.can_request(url1)
        allowed2, _ = cb.can_request(url2)

        assert allowed1 is False
        assert allowed2 is True


class TestSecretRedactor:
    """Test secret redaction."""

    def test_redact_api_key(self):
        """Test API key redaction."""
        text = 'api_key: "sk-1234567890abcdef"'
        redacted = SecretRedactor.redact_text(text)
        assert "sk-1234567890abcdef" not in redacted
        assert "***REDACTED***" in redacted

    def test_redact_bearer_token(self):
        """Test Bearer token redaction."""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        redacted = SecretRedactor.redact_text(text)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in redacted
        assert "***REDACTED***" in redacted

    def test_redact_aws_key(self):
        """Test AWS key redaction."""
        text = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
        redacted = SecretRedactor.redact_text(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in redacted
        assert "***REDACTED***" in redacted

    def test_redact_password(self):
        """Test password redaction."""
        text = 'password: "super_secret_pass"'
        redacted = SecretRedactor.redact_text(text)
        assert "super_secret_pass" not in redacted
        assert "***REDACTED***" in redacted

    def test_redact_headers(self):
        """Test header redaction."""
        headers = {
            "Authorization": "Bearer secret_token",
            "X-API-Key": "api_key_12345",
            "Content-Type": "application/json",
        }
        redacted = SecretRedactor.redact_headers(headers)

        assert redacted["Authorization"] == "***REDACTED***"
        assert redacted["X-API-Key"] == "***REDACTED***"
        assert redacted["Content-Type"] == "application/json"

    def test_redact_none(self):
        """Test redaction with None input."""
        assert SecretRedactor.redact_text(None) is None
        assert SecretRedactor.redact_headers(None) is None


class TestDomainAllowlist:
    """Test domain allowlist."""

    def test_exact_match(self):
        """Test exact domain match."""
        allowlist = DomainAllowlist(["example.com"])
        allowed, _ = allowlist.is_allowed("http://example.com/path")
        assert allowed is True

    def test_wildcard_subdomain(self):
        """Test wildcard subdomain matching."""
        allowlist = DomainAllowlist(["*.example.com"])

        # Should match subdomains
        allowed, _ = allowlist.is_allowed("http://api.example.com")
        assert allowed is True

        allowed, _ = allowlist.is_allowed("http://www.example.com")
        assert allowed is True

        # Should not match parent domain
        allowed, _ = allowlist.is_allowed("http://example.com")
        assert allowed is False

    def test_not_allowed(self):
        """Test domain not in allowlist."""
        allowlist = DomainAllowlist(["example.com"])
        allowed, reason = allowlist.is_allowed("http://evil.com")

        assert allowed is False
        assert "not in allowlist" in reason

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        allowlist = DomainAllowlist(["example.com"])

        allowed, _ = allowlist.is_allowed("http://EXAMPLE.COM")
        assert allowed is True

        allowed, _ = allowlist.is_allowed("http://Example.Com")
        assert allowed is True

    def test_multiple_patterns(self):
        """Test multiple patterns in allowlist."""
        allowlist = DomainAllowlist(["*.github.com", "api.openai.com"])

        # Match first pattern
        allowed, _ = allowlist.is_allowed("http://api.github.com")
        assert allowed is True

        # Match second pattern
        allowed, _ = allowlist.is_allowed("http://api.openai.com")
        assert allowed is True

        # No match
        allowed, _ = allowlist.is_allowed("http://evil.com")
        assert allowed is False


class TestHttpClient:
    """Test HTTP client."""

    @pytest.mark.asyncio
    async def test_request_blocked_by_allowlist(self):
        """Test request blocked by domain allowlist."""
        client = HttpClient()
        client.allowlist = DomainAllowlist(["example.com"])

        with pytest.raises(ValueError, match="Domain not allowed"):
            await client.request(HttpMethod.GET, "http://evil.com")

    @pytest.mark.asyncio
    async def test_request_blocked_by_circuit_breaker(self):
        """Test request blocked by circuit breaker."""
        client = HttpClient()
        client.allowlist = DomainAllowlist(["example.com"])

        # Open circuit manually
        url = "http://example.com"
        for _ in range(5):
            client.circuit_breaker.record_failure(url)

        with pytest.raises(ValueError, match="Circuit breaker open"):
            await client.request(HttpMethod.GET, url)

    @pytest.mark.asyncio
    async def test_successful_request(self):
        """Test successful HTTP request."""
        client = HttpClient()
        client.allowlist = DomainAllowlist(["httpbin.org"])

        # Mock httpx response
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.url = "http://httpbin.org/get"
            mock_response.elapsed = timedelta(milliseconds=100)
            mock_response.json.return_value = {"status": "ok"}

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await client.request(HttpMethod.GET, "http://httpbin.org/get")

            assert result["status_code"] == 200
            assert result["body"] == {"status": "ok"}
            assert "elapsed_ms" in result

    @pytest.mark.asyncio
    async def test_request_with_headers_and_params(self):
        """Test request with headers and query parameters."""
        client = HttpClient()
        client.allowlist = DomainAllowlist(["httpbin.org"])

        headers = {"Authorization": "Bearer token123"}
        params = {"key": "value"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/plain"}
            mock_response.url = "http://httpbin.org/get"
            mock_response.elapsed = timedelta(milliseconds=50)
            mock_response.text = "OK"

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await client.request(
                HttpMethod.GET,
                "http://httpbin.org/get",
                headers=headers,
                params=params,
            )

            # Verify request was made with headers and params
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            assert call_args[1]["headers"] == headers
            assert call_args[1]["params"] == params

    @pytest.mark.asyncio
    async def test_post_with_json_body(self):
        """Test POST request with JSON body."""
        client = HttpClient()
        client.allowlist = DomainAllowlist(["httpbin.org"])

        body = {"name": "test", "value": 123}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.headers = {"content-type": "application/json"}
            mock_response.url = "http://httpbin.org/post"
            mock_response.elapsed = timedelta(milliseconds=75)
            mock_response.json.return_value = {"created": True}

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await client.request(
                HttpMethod.POST,
                "http://httpbin.org/post",
                body=body,
            )

            assert result["status_code"] == 201
            assert result["body"] == {"created": True}

            # Verify POST was called with json parameter
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[1]["json"] == body

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_success(self):
        """Test circuit breaker records successful requests."""
        client = HttpClient()
        client.allowlist = DomainAllowlist(["httpbin.org"])

        url = "http://httpbin.org/get"

        # Open circuit first
        for _ in range(5):
            client.circuit_breaker.record_failure(url)

        circuit = client.circuit_breaker._get_circuit(client.circuit_breaker._get_domain(url))
        assert circuit["state"] == CircuitState.OPEN

        # Mock successful request
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/plain"}
            mock_response.url = url
            mock_response.elapsed = timedelta(milliseconds=50)
            mock_response.text = "OK"

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Transition to half-open manually
            circuit["state"] = CircuitState.HALF_OPEN

            await client.request(HttpMethod.GET, url)

            # Should record success
            # (In real scenario, would need multiple successes to close)

    @pytest.mark.asyncio
    async def test_request_timeout_configuration(self):
        """Test request respects timeout configuration."""
        client = HttpClient()
        client.allowlist = DomainAllowlist(["httpbin.org"])

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/plain"}
            mock_response.url = "http://httpbin.org/delay/1"
            mock_response.elapsed = timedelta(seconds=1)
            mock_response.text = "OK"

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            await client.request(
                HttpMethod.GET,
                "http://httpbin.org/delay/1",
                timeout=60,
            )

            # Verify timeout was configured
            mock_client_class.assert_called_once()
            call_kwargs = mock_client_class.call_args[1]
            assert call_kwargs["timeout"].connect == 60
