# Tool Execution Policies for X-Agent
# These policies control which tools can be executed and under what conditions

package xagent.tools

import future.keywords.if
import future.keywords.in

# Default deny for tool execution
default allow_tool_execution = false

# Allow code execution only for users with code_exec scope
allow_tool_execution if {
    input.user.authenticated == true
    "code_exec" in input.user.scopes
    input.tool.name == "execute_code"
    input.tool.sandboxed == true
}

# Allow file operations within workspace
allow_tool_execution if {
    input.user.authenticated == true
    "file_ops" in input.user.scopes
    input.tool.name in ["read_file", "write_file", "list_files"]
    startswith(input.tool.args.path, "/workspace/")
}

# Deny file operations outside workspace
deny_tool_execution["File operations outside workspace are not allowed"] if {
    input.tool.name in ["read_file", "write_file", "delete_file", "list_files"]
    not startswith(input.tool.args.path, "/workspace/")
}

# Deny file deletion without explicit permission
deny_tool_execution["File deletion requires explicit permission"] if {
    input.tool.name == "delete_file"
    not "file_delete" in input.user.scopes
}

# Allow web search for users with web_search scope
allow_tool_execution if {
    input.user.authenticated == true
    "web_search" in input.user.scopes
    input.tool.name == "web_search"
}

# Allow network calls for users with network scope
allow_tool_execution if {
    input.user.authenticated == true
    "network" in input.user.scopes
    input.tool.name in ["http_request", "api_call"]
}

# Deny network calls to internal addresses
deny_tool_execution["Calls to internal addresses are not allowed"] if {
    input.tool.name in ["http_request", "api_call"]
    is_internal_address(input.tool.args.url)
}

# Helper function to check if URL is internal
is_internal_address(url) if {
    contains(url, "127.0.0.1")
}

is_internal_address(url) if {
    contains(url, "localhost")
}

is_internal_address(url) if {
    contains(url, "192.168.")
}

is_internal_address(url) if {
    contains(url, "10.")
}

is_internal_address(url) if {
    contains(url, "172.16.")
}

# Block execution of dangerous code patterns
deny_tool_execution["Dangerous code pattern detected"] if {
    input.tool.name == "execute_code"
    dangerous_pattern_detected(input.tool.args.code)
}

# Helper to detect dangerous patterns
dangerous_pattern_detected(code) if {
    contains(code, "__import__")
}

dangerous_pattern_detected(code) if {
    contains(code, "eval(")
}

dangerous_pattern_detected(code) if {
    contains(code, "exec(")
}

dangerous_pattern_detected(code) if {
    contains(code, "compile(")
}

# Resource limits
deny_tool_execution["Resource limits exceeded"] if {
    input.tool.resource_limits.memory_mb > 512
}

deny_tool_execution["Execution timeout too high"] if {
    input.tool.resource_limits.timeout_seconds > 300
}
