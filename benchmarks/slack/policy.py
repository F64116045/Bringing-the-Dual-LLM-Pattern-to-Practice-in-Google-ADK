from typing import Any, Optional
from google.adk.tools.base_tool import BaseTool, ToolContext

RED = "\033[91m"
RESET = "\033[0m"
GREEN = "\033[92m"

# Trusted Domains (Allowlist)
TRUSTED_DOMAINS = [
    "www.dora-website.com",
    "www.company-todo-list.com/alice",
    "www.company-todo-list.com/bob",

]

def slack_security_policy(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext
) -> Optional[dict]:
    """
    Security Policy for Slack Benchmark.
    """
    
    # Create your policies here. For example:
    # Policy 1: Restrict 'post_message' to trusted domains only
    if tool.name == "post_message":
        channel = args.get("channel")
        print(f"{RED}[Policy Check]{RESET} post_message to {channel}")

        # Allowlist Check
        if channel not in TRUSTED_DOMAINS:
            print(f"{RED} BLOCKED: Channel {channel} is not in the trusted allowlist!{RESET}")
            raise ValueError(f"Security Policy Violation: Posting to untrusted channel {channel} is blocked.")

        print(f"{GREEN}✔ Policy Passed{RESET}")
    return None