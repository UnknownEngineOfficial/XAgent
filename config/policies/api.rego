# API Access Policies for X-Agent
# These policies control access to REST API endpoints

package xagent.api

import future.keywords.if
import future.keywords.in

# Default allow API access for authenticated users
default allow_api_access = false

# Allow public health check endpoints without authentication
allow_api_access if {
    input.request.method == "GET"
    input.request.path in ["/health", "/healthz", "/ready"]
}

# Allow metrics endpoint
allow_api_access if {
    input.request.method == "GET"
    input.request.path == "/metrics"
}

# Allow authenticated users to access API
allow_api_access if {
    input.user.authenticated == true
    input.user.token_valid == true
}

# Goal management endpoints - require agent_control scope
allow_api_access if {
    input.user.authenticated == true
    "agent_control" in input.user.scopes
    input.request.method in ["GET", "POST", "PUT", "DELETE"]
    startswith(input.request.path, "/api/v1/goals")
}

# Agent control endpoints - require agent_control scope
allow_api_access if {
    input.user.authenticated == true
    "agent_control" in input.user.scopes
    input.request.method in ["GET", "POST"]
    startswith(input.request.path, "/api/v1/agent")
}

# Read-only access for users with readonly scope
allow_api_access if {
    input.user.authenticated == true
    "readonly" in input.user.scopes
    input.request.method == "GET"
}

# Deny write operations for readonly users
deny_api_access["Read-only users cannot perform write operations"] if {
    "readonly" in input.user.scopes
    not "agent_control" in input.user.scopes
    input.request.method in ["POST", "PUT", "DELETE", "PATCH"]
}

# Deny unauthenticated access to protected endpoints
deny_api_access["Authentication required"] if {
    not input.user.authenticated
    not input.request.path in ["/health", "/healthz", "/ready", "/metrics", "/docs", "/openapi.json"]
}

# Rate limiting
deny_api_access["Rate limit exceeded"] if {
    input.request.rate_limit_exceeded == true
}

# IP whitelisting (if configured)
deny_api_access["IP address not whitelisted"] if {
    count(input.security.ip_whitelist) > 0
    not input.request.client_ip in input.security.ip_whitelist
}

# Block suspicious user agents
deny_api_access["Suspicious user agent detected"] if {
    suspicious_user_agent(input.request.user_agent)
}

suspicious_user_agent(ua) if {
    contains(lower(ua), "bot")
    not contains(lower(ua), "googlebot")
}

suspicious_user_agent(ua) if {
    contains(lower(ua), "crawler")
}

suspicious_user_agent(ua) if {
    contains(lower(ua), "scraper")
}
