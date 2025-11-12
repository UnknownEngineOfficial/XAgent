#!/usr/bin/env python
"""
HTTP Client Tool Demonstration

This script demonstrates the secure HTTP client capabilities:
1. Basic GET/POST requests
2. Domain allowlist protection
3. Circuit breaker pattern
4. Secret redaction in logs
5. Error handling and resilience
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xagent.tools.langserve_tools import http_request
from xagent.tools.http_client import get_http_client, HttpMethod


class HttpClientDemo:
    """Demonstration of HTTP client features."""

    def __init__(self):
        """Initialize the demo."""
        self.results = []

    def print_header(self, title: str) -> None:
        """Print a formatted header."""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80 + "\n")

    def print_success(self, message: str) -> None:
        """Print a success message."""
        print(f"✅ {message}")

    def print_info(self, message: str) -> None:
        """Print an info message."""
        print(f"ℹ️  {message}")

    def print_error(self, message: str) -> None:
        """Print an error message."""
        print(f"❌ {message}")

    def print_result(self, result: dict) -> None:
        """Print request result."""
        if result["status"] == "success":
            self.print_success(f"Status: {result['status_code']}")
            self.print_info(f"Duration: {result.get('elapsed_ms', 'N/A')}ms")
            self.print_info(f"URL: {result.get('url', 'N/A')}")
            
            # Print body preview
            body = result.get("body", "")
            body_str = str(body)
            if len(body_str) > 200:
                self.print_info(f"Body: {body_str[:200]}...(truncated)")
            else:
                self.print_info(f"Body: {body_str}")
        else:
            self.print_error(f"Error: {result.get('error', 'Unknown error')}")

    async def demo_1_basic_get(self) -> None:
        """Demonstrate basic GET request."""
        self.print_header("Demo 1: Basic GET Request")
        
        self.print_info("Making GET request to httpbin.org/get...")
        result = await http_request(
            url="https://httpbin.org/get",
            method="GET"
        )
        
        self.print_result(result)
        self.results.append(("Basic GET", result["status"] == "success"))

    async def demo_2_get_with_params(self) -> None:
        """Demonstrate GET request with query parameters."""
        self.print_header("Demo 2: GET Request with Query Parameters")
        
        self.print_info("Making GET request with query parameters...")
        
        # Note: httpbin.org/get echoes back parameters
        result = await http_request(
            url="https://httpbin.org/get?key=value&foo=bar",
            method="GET"
        )
        
        self.print_result(result)
        
        # Verify parameters in response
        if result["status"] == "success":
            args = result.get("body", {}).get("args", {})
            if args.get("key") == "value" and args.get("foo") == "bar":
                self.print_success("Query parameters correctly included")
        
        self.results.append(("GET with params", result["status"] == "success"))

    async def demo_3_post_json(self) -> None:
        """Demonstrate POST request with JSON body."""
        self.print_header("Demo 3: POST Request with JSON Body")
        
        self.print_info("Making POST request with JSON body...")
        
        data = {
            "name": "X-Agent HTTP Demo",
            "version": "0.2.0",
            "features": ["circuit-breaker", "secret-redaction", "domain-allowlist"]
        }
        
        result = await http_request(
            url="https://httpbin.org/post",
            method="POST",
            body=data
        )
        
        self.print_result(result)
        
        # Verify JSON was sent
        if result["status"] == "success":
            received_json = result.get("body", {}).get("json", {})
            if received_json == data:
                self.print_success("JSON body correctly sent and echoed")
        
        self.results.append(("POST with JSON", result["status"] == "success"))

    async def demo_4_auth_headers(self) -> None:
        """Demonstrate request with authentication headers."""
        self.print_header("Demo 4: Request with Authentication Headers")
        
        self.print_info("Making request with auth headers (will be redacted in logs)...")
        
        result = await http_request(
            url="https://httpbin.org/headers",
            method="GET",
            headers={
                "Authorization": "Bearer my_secret_token_12345",
                "X-API-Key": "api_key_67890",
                "User-Agent": "X-Agent HTTP Demo/0.2.0"
            }
        )
        
        self.print_result(result)
        
        self.print_info("Check logs - secrets should be redacted!")
        
        self.results.append(("Auth headers", result["status"] == "success"))

    async def demo_5_domain_blocked(self) -> None:
        """Demonstrate domain allowlist protection."""
        self.print_header("Demo 5: Domain Allowlist Protection")
        
        self.print_info("Attempting request to non-allowed domain...")
        
        result = await http_request(
            url="https://evil-domain-that-should-be-blocked.com",
            method="GET"
        )
        
        # This should fail with domain not allowed
        if result["status"] == "error" and "not allowed" in result["error"].lower():
            self.print_success("Request correctly blocked by domain allowlist")
            self.print_info(f"Error message: {result['error']}")
            self.results.append(("Domain blocked", True))
        else:
            self.print_error("Domain allowlist did not block the request")
            self.results.append(("Domain blocked", False))

    async def demo_6_timeout_config(self) -> None:
        """Demonstrate timeout configuration."""
        self.print_header("Demo 6: Request Timeout Configuration")
        
        self.print_info("Making request with short timeout...")
        
        # httpbin.org/delay/2 waits 2 seconds before responding
        result = await http_request(
            url="https://httpbin.org/delay/1",
            method="GET",
            timeout=5  # 5 second timeout, should succeed
        )
        
        if result["status"] == "success":
            self.print_success("Request completed within timeout")
            elapsed = result.get("elapsed_ms", 0)
            self.print_info(f"Took {elapsed}ms (expected ~1000ms)")
        else:
            self.print_error(f"Request failed: {result['error']}")
        
        self.results.append(("Timeout config", result["status"] == "success"))

    async def demo_7_circuit_breaker(self) -> None:
        """Demonstrate circuit breaker pattern."""
        self.print_header("Demo 7: Circuit Breaker Pattern")
        
        self.print_info("Simulating circuit breaker with repeated failures...")
        
        # Get the HTTP client
        client = get_http_client()
        
        # Manually trigger failures (in production, these would be real failures)
        test_domain = "test-failing-service.example.com"
        url = f"https://{test_domain}/api"
        
        self.print_info("Recording 5 failures to open circuit...")
        for i in range(5):
            client.circuit_breaker.record_failure(url)
            self.print_info(f"  Failure {i+1} recorded")
        
        # Check if circuit is open
        can_request, reason = client.circuit_breaker.can_request(url)
        
        if not can_request:
            self.print_success("Circuit breaker opened after failures")
            self.print_info(f"Reason: {reason}")
            self.results.append(("Circuit breaker", True))
        else:
            self.print_error("Circuit breaker did not open")
            self.results.append(("Circuit breaker", False))
        
        # Show recovery
        self.print_info("\nRecording 2 successes to close circuit...")
        
        # Manually set to half-open for demo
        circuit = client.circuit_breaker._get_circuit(client.circuit_breaker._get_domain(url))
        circuit["state"] = "HALF_OPEN"
        
        client.circuit_breaker.record_success(url)
        self.print_info("  Success 1 recorded")
        
        client.circuit_breaker.record_success(url)
        self.print_info("  Success 2 recorded")
        
        circuit = client.circuit_breaker._get_circuit(client.circuit_breaker._get_domain(url))
        if circuit["state"] == "CLOSED":
            self.print_success("Circuit breaker closed after recovery")
        else:
            self.print_info(f"Circuit state: {circuit['state']}")

    async def demo_8_multiple_requests(self) -> None:
        """Demonstrate concurrent requests."""
        self.print_header("Demo 8: Concurrent Requests (Performance)")
        
        self.print_info("Making 5 concurrent requests...")
        
        import time
        start_time = time.time()
        
        # Make multiple requests concurrently
        results = await asyncio.gather(
            http_request(url="https://httpbin.org/get", method="GET"),
            http_request(url="https://httpbin.org/uuid", method="GET"),
            http_request(url="https://httpbin.org/user-agent", method="GET"),
            http_request(url="https://httpbin.org/headers", method="GET"),
            http_request(url="https://httpbin.org/ip", method="GET"),
        )
        
        elapsed = (time.time() - start_time) * 1000
        
        success_count = sum(1 for r in results if r["status"] == "success")
        
        self.print_success(f"{success_count}/5 requests successful")
        self.print_info(f"Total time: {elapsed:.1f}ms")
        self.print_info(f"Average: {elapsed/5:.1f}ms per request")
        
        self.results.append(("Concurrent requests", success_count == 5))

    async def run_all_demos(self) -> None:
        """Run all demonstrations."""
        self.print_header("🚀 X-Agent HTTP Client Tool Demonstration")
        
        self.print_info("This demo showcases the secure HTTP client features:")
        self.print_info("  1. Basic GET requests")
        self.print_info("  2. Query parameters")
        self.print_info("  3. POST with JSON body")
        self.print_info("  4. Authentication headers (with secret redaction)")
        self.print_info("  5. Domain allowlist protection")
        self.print_info("  6. Timeout configuration")
        self.print_info("  7. Circuit breaker pattern")
        self.print_info("  8. Concurrent requests\n")
        
        input("Press Enter to start the demonstration...")
        
        # Run demos
        await self.demo_1_basic_get()
        input("\nPress Enter to continue...")
        
        await self.demo_2_get_with_params()
        input("\nPress Enter to continue...")
        
        await self.demo_3_post_json()
        input("\nPress Enter to continue...")
        
        await self.demo_4_auth_headers()
        input("\nPress Enter to continue...")
        
        await self.demo_5_domain_blocked()
        input("\nPress Enter to continue...")
        
        await self.demo_6_timeout_config()
        input("\nPress Enter to continue...")
        
        await self.demo_7_circuit_breaker()
        input("\nPress Enter to continue...")
        
        await self.demo_8_multiple_requests()
        
        # Print summary
        self.print_header("📊 Demonstration Summary")
        
        total = len(self.results)
        passed = sum(1 for _, success in self.results if success)
        
        for name, success in self.results:
            status = "✅" if success else "❌"
            print(f"{status} {name}")
        
        print(f"\nTotal: {passed}/{total} demos passed")
        
        if passed == total:
            self.print_success("All demonstrations completed successfully! 🎉")
        else:
            self.print_info(f"{total - passed} demo(s) had issues")
        
        self.print_header("🎓 Key Takeaways")
        print("1. ✅ Domain allowlist prevents unauthorized requests")
        print("2. ✅ Circuit breaker protects against cascading failures")
        print("3. ✅ Secrets are automatically redacted in logs")
        print("4. ✅ Comprehensive error handling for production use")
        print("5. ✅ High performance with concurrent requests")
        
        self.print_header("📚 Next Steps")
        print("- Read docs/HTTP_CLIENT.md for full documentation")
        print("- Review tests/unit/test_http_client.py for test coverage")
        print("- Configure domain allowlist for your use case")
        print("- Monitor circuit breaker state in production")


async def main():
    """Run the demonstration."""
    demo = HttpClientDemo()
    
    try:
        await demo.run_all_demos()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✨ Demo complete!\n")


if __name__ == "__main__":
    asyncio.run(main())
