# Base Policy for X-Agent
# This policy defines the fundamental security rules for the X-Agent system

package xagent.base

import future.keywords.if
import future.keywords.in

# Default deny policy
default allow = false

# Allow authenticated users with valid tokens
allow if {
    input.user.authenticated == true
    input.user.token_valid == true
}

# Block requests without authentication
deny["Authentication required"] if {
    not input.user.authenticated
}

# Block expired tokens
deny["Token expired"] if {
    input.user.authenticated == true
    input.user.token_valid == false
}

# Rate limiting check
deny["Rate limit exceeded"] if {
    input.request.rate_limit_exceeded == true
}

# System health check - always allow
allow if {
    input.request.path in ["/health", "/healthz", "/ready"]
}

# Metrics endpoint - allow for monitoring
allow if {
    input.request.path == "/metrics"
}
