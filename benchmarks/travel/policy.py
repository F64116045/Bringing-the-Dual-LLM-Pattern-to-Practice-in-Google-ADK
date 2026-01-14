from typing import Any, Optional
from google.adk.tools.base_tool import BaseTool, ToolContext

RED = "\033[91m"
RESET = "\033[0m"
GREEN = "\033[92m"

# Trusted Partners (Allowlist)
TRUSTED_HOTELS = [
    "Le Marais Boutique", 
    "Good Night"
]

def travel_security_policy(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext
) -> Optional[dict]:
    """
    Security Policy for Travel Benchmark.
    """
    # Create your policies here. 
    

    return None