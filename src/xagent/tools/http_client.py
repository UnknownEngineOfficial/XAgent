"""HTTP Client Tool - Secure HTTP/HTTPS requests with circuit breaker and rate limiting."""

import hashlib
import re
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field, field_validator

from xagent.config import settings
from xagent.utils.logging import get_logger

logger = get_logger(__name__)


class HttpMethod(str, Enum):
    """Supported HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"  # Failing, rejecting requests
    HALF_OPEN = "HALF_OPEN"  # Testing if service recovered


class HttpRequestInput(BaseModel):
    """Input schema for HTTP request tool."""

    method: HttpMethod = Field(description="HTTP method to use")
    url: str = Field(description="Full URL to request")
    headers: dict[str, str] | None = Field(
        default=None, description="Optional HTTP headers"
    )
    params: dict[str, str] | None = Field(
        default=None, description="Optional query parameters"
    )
    body: str | dict | None = Field(default=None, description="Optional request body")
    timeout: int = Field(
        default=30, ge=1, le=300, description="Request timeout in seconds (1-300)"
    )
    follow_redirects: bool = Field(
        default=True, description="Whether to follow redirects"
    )
    verify_ssl: bool = Field(default=True, description="Whether to verify SSL certificates")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format and scheme."""
        if not v or not isinstance(v, str):
            raise ValueError("URL must be a non-empty string")

        parsed = urlparse(v)
        if not parsed.scheme:
            raise ValueError("URL must include scheme (http:// or https://)")
        if parsed.scheme not in ("http", "https"):
            raise ValueError("URL scheme must be http or https")
        if not parsed.netloc:
            raise ValueError("URL must include hostname")

        return v


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for HTTP requests.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail fast
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            success_threshold: Consecutive successes needed to close circuit
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: datetime | None = None
        self.circuits: dict[str, dict[str, Any]] = {}  # Per-domain circuit state

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc

    def _get_circuit(self, domain: str) -> dict[str, Any]:
        """Get or create circuit state for domain."""
        if domain not in self.circuits:
            self.circuits[domain] = {
                "state": CircuitState.CLOSED,
                "failure_count": 0,
                "success_count": 0,
                "last_failure_time": None,
            }
        return self.circuits[domain]

    def can_request(self, url: str) -> tuple[bool, str]:
        """
        Check if request is allowed.

        Returns:
            Tuple of (allowed, reason)
        """
        domain = self._get_domain(url)
        circuit = self._get_circuit(domain)

        if circuit["state"] == CircuitState.CLOSED:
            return True, "Circuit closed, request allowed"

        if circuit["state"] == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            if circuit["last_failure_time"]:
                elapsed = (
                    datetime.now(timezone.utc) - circuit["last_failure_time"]
                ).total_seconds()
                if elapsed >= self.recovery_timeout:
                    # Transition to half-open
                    circuit["state"] = CircuitState.HALF_OPEN
                    circuit["success_count"] = 0
                    logger.info(
                        f"Circuit breaker for {domain} transitioning to HALF_OPEN"
                    )
                    return True, "Circuit half-open, testing recovery"

            return False, f"Circuit open for {domain}, request blocked"

        # HALF_OPEN state
        return True, "Circuit half-open, allowing test request"

    def record_success(self, url: str) -> None:
        """Record successful request."""
        domain = self._get_domain(url)
        circuit = self._get_circuit(domain)

        if circuit["state"] == CircuitState.HALF_OPEN:
            circuit["success_count"] += 1
            if circuit["success_count"] >= self.success_threshold:
                # Recovery successful, close circuit
                circuit["state"] = CircuitState.CLOSED
                circuit["failure_count"] = 0
                circuit["success_count"] = 0
                logger.info(f"Circuit breaker for {domain} closed after recovery")
        else:
            # Reset failure count on success
            circuit["failure_count"] = max(0, circuit["failure_count"] - 1)

    def record_failure(self, url: str) -> None:
        """Record failed request."""
        domain = self._get_domain(url)
        circuit = self._get_circuit(domain)

        circuit["failure_count"] += 1
        circuit["last_failure_time"] = datetime.now(timezone.utc)

        if circuit["state"] == CircuitState.HALF_OPEN:
            # Failed during recovery, reopen circuit
            circuit["state"] = CircuitState.OPEN
            circuit["success_count"] = 0
            logger.warning(f"Circuit breaker for {domain} reopened after failed recovery")
        elif circuit["failure_count"] >= self.failure_threshold:
            # Too many failures, open circuit
            circuit["state"] = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker for {domain} opened after {circuit['failure_count']} failures"
            )


class SecretRedactor:
    """Redact secrets from HTTP requests and responses."""

    # Patterns for common secret formats
    SECRET_PATTERNS = [
        # API keys
        (re.compile(r"(['\"]?api[_-]?key['\"]?\s*[:=]\s*['\"]?)([^'\"]+)(['\"]?)", re.I), r"\1***REDACTED***\3"),
        # Bearer tokens
        (re.compile(r"(bearer\s+)([a-zA-Z0-9_\-\.]+)", re.I), r"\1***REDACTED***"),
        # AWS keys
        (re.compile(r"(AKIA[0-9A-Z]{16})", re.I), r"***REDACTED***"),
        # Generic auth headers
        (re.compile(r"(authorization:\s*)(.+)", re.I), r"\1***REDACTED***"),
        # Passwords
        (re.compile(r"(['\"]?password['\"]?\s*[:=]\s*['\"]?)([^'\"]+)(['\"]?)", re.I), r"\1***REDACTED***\3"),
        # Tokens
        (re.compile(r"(['\"]?token['\"]?\s*[:=]\s*['\"]?)([^'\"]+)(['\"]?)", re.I), r"\1***REDACTED***\3"),
    ]

    @classmethod
    def redact_text(cls, text: str) -> str:
        """Redact secrets from text."""
        if not text:
            return text

        redacted = text
        for pattern, replacement in cls.SECRET_PATTERNS:
            redacted = pattern.sub(replacement, redacted)

        return redacted

    @classmethod
    def redact_headers(cls, headers: dict[str, str]) -> dict[str, str]:
        """Redact secrets from headers."""
        if not headers:
            return headers

        redacted = {}
        for key, value in headers.items():
            if key.lower() in ("authorization", "x-api-key", "api-key"):
                redacted[key] = "***REDACTED***"
            else:
                redacted[key] = cls.redact_text(value)

        return redacted


class DomainAllowlist:
    """Manage allowed domains for HTTP requests."""

    def __init__(self, allowed_patterns: list[str] | None = None):
        """
        Initialize domain allowlist.

        Args:
            allowed_patterns: List of domain patterns (supports wildcards)
                              If None, uses default from settings
        """
        if allowed_patterns is None:
            # Get from settings or use default
            allowed_patterns = getattr(
                settings,
                "http_allowed_domains",
                [
                    "*.github.com",
                    "*.googleapis.com",
                    "api.openai.com",
                    "*.anthropic.com",
                    "httpbin.org",  # For testing
                ],
            )

        self.patterns = [self._pattern_to_regex(p) for p in allowed_patterns]

    @staticmethod
    def _pattern_to_regex(pattern: str) -> re.Pattern:
        """Convert wildcard pattern to regex."""
        # Escape special regex characters except *
        escaped = re.escape(pattern).replace(r"\*", ".*")
        return re.compile(f"^{escaped}$", re.IGNORECASE)

    def is_allowed(self, url: str) -> tuple[bool, str]:
        """
        Check if URL domain is allowed.

        Returns:
            Tuple of (allowed, reason)
        """
        parsed = urlparse(url)
        domain = parsed.netloc

        # Check against all patterns
        for pattern in self.patterns:
            if pattern.match(domain):
                return True, f"Domain {domain} matches allowlist"

        return False, f"Domain {domain} not in allowlist"


class HttpClient:
    """
    HTTP client with security features.

    Features:
    - Circuit breaker pattern
    - Secret redaction in logs
    - Domain allowlist
    - Rate limiting (via external rate limiter)
    - Timeout protection
    """

    def __init__(self):
        """Initialize HTTP client."""
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=getattr(settings, "http_circuit_failure_threshold", 5),
            recovery_timeout=getattr(settings, "http_circuit_recovery_timeout", 60),
            success_threshold=getattr(settings, "http_circuit_success_threshold", 2),
        )
        self.redactor = SecretRedactor()
        self.allowlist = DomainAllowlist()
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(300.0),  # Max timeout
            follow_redirects=True,
            verify=True,
        )

    async def request(
        self,
        method: HttpMethod,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        body: str | dict | None = None,
        timeout: int = 30,
        follow_redirects: bool = True,
        verify_ssl: bool = True,
    ) -> dict[str, Any]:
        """
        Make HTTP request with security features.

        Args:
            method: HTTP method
            url: Request URL
            headers: Optional headers
            params: Optional query parameters
            body: Optional request body
            timeout: Request timeout in seconds
            follow_redirects: Whether to follow redirects
            verify_ssl: Whether to verify SSL

        Returns:
            Response data including status, headers, and body

        Raises:
            ValueError: If domain not allowed or circuit is open
            httpx.HTTPError: On request failure
        """
        # Check domain allowlist
        allowed, reason = self.allowlist.is_allowed(url)
        if not allowed:
            logger.warning(f"HTTP request blocked: {reason}")
            raise ValueError(f"Domain not allowed: {reason}")

        # Check circuit breaker
        can_request, cb_reason = self.circuit_breaker.can_request(url)
        if not can_request:
            logger.warning(f"HTTP request blocked by circuit breaker: {cb_reason}")
            raise ValueError(f"Circuit breaker open: {cb_reason}")

        # Log request (with redacted secrets)
        redacted_headers = self.redactor.redact_headers(headers or {})
        logger.info(
            f"HTTP {method} request to {url}",
            extra={
                "method": method,
                "url": url,
                "headers": redacted_headers,
                "has_body": body is not None,
            },
        )

        try:
            # Configure client for this request
            client_config = {
                "timeout": httpx.Timeout(timeout),
                "follow_redirects": follow_redirects,
                "verify": verify_ssl,
            }

            # Make request
            async with httpx.AsyncClient(**client_config) as client:
                if method == HttpMethod.GET:
                    response = await client.get(url, headers=headers, params=params)
                elif method == HttpMethod.POST:
                    response = await client.post(
                        url, headers=headers, params=params, json=body if isinstance(body, dict) else None, content=body if isinstance(body, str) else None
                    )
                elif method == HttpMethod.PUT:
                    response = await client.put(
                        url, headers=headers, params=params, json=body if isinstance(body, dict) else None, content=body if isinstance(body, str) else None
                    )
                elif method == HttpMethod.DELETE:
                    response = await client.delete(url, headers=headers, params=params)
                elif method == HttpMethod.PATCH:
                    response = await client.patch(
                        url, headers=headers, params=params, json=body if isinstance(body, dict) else None, content=body if isinstance(body, str) else None
                    )
                elif method == HttpMethod.HEAD:
                    response = await client.head(url, headers=headers, params=params)
                elif method == HttpMethod.OPTIONS:
                    response = await client.options(url, headers=headers, params=params)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

            # Record success
            self.circuit_breaker.record_success(url)

            # Parse response
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "url": str(response.url),
                "elapsed_ms": response.elapsed.total_seconds() * 1000,
            }

            # Try to parse body
            try:
                # Check content type
                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type:
                    result["body"] = response.json()
                else:
                    result["body"] = response.text

                # Limit response size in logs
                body_str = str(result["body"])
                if len(body_str) > 1000:
                    body_preview = body_str[:1000] + "...(truncated)"
                else:
                    body_preview = body_str

                logger.info(
                    f"HTTP {method} response: {response.status_code}",
                    extra={
                        "status_code": response.status_code,
                        "elapsed_ms": result["elapsed_ms"],
                        "body_preview": body_preview,
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to parse response body: {e}")
                result["body"] = response.text
                result["parse_error"] = str(e)

            return result

        except httpx.HTTPError as e:
            # Record failure
            self.circuit_breaker.record_failure(url)

            logger.error(
                f"HTTP {method} request failed: {e}",
                extra={"method": method, "url": url, "error": str(e)},
            )
            raise

        except Exception as e:
            # Record failure for unexpected errors
            self.circuit_breaker.record_failure(url)

            logger.error(
                f"Unexpected error during HTTP {method} request: {e}",
                extra={"method": method, "url": url, "error": str(e)},
            )
            raise

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()


# Singleton instance
_http_client: HttpClient | None = None


def get_http_client() -> HttpClient:
    """Get or create HTTP client instance."""
    global _http_client
    if _http_client is None:
        _http_client = HttpClient()
    return _http_client
