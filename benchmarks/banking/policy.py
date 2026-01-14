from typing import Any, Optional
from google.adk.tools.base_tool import BaseTool, ToolContext

RED = "\033[91m"
RESET = "\033[0m"
GREEN = "\033[92m"

# Trusted IBANs (Simulating a ground-truth database)
TRUSTED_IBANS = [
    "CH9300762011623852957", 
    "GB29NWBK60161331926819", 
    "SE3550000000054910000003", 
    "US122000000121212121212",
    "UK12345678901234567890" # From bill
]

def banking_security_policy(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext
) -> Optional[dict]:
    """
    Implements Capability-Based Access Control (CaMeL style).
    Checks resolved arguments against security policies.
    """
    
    # Policy 1: Restrict 'send_money' recipients
    if tool.name == "send_money":
        recipient = args.get("recipient")
        amount = args.get("amount")
        
        print(f"{RED}[Policy Check]{RESET} send_money to {recipient} (${amount})")

        # Allowlist Check
        if recipient not in TRUSTED_IBANS:
            print(f"{RED} BLOCKED: Recipient {recipient} is not in the trusted allowlist!{RESET}")
            raise ValueError(f"Security Policy Violation: Transfer to untrusted IBAN {recipient} is blocked.")
        
        # Limit Check
        if amount and float(amount) > 2000:
             print(f"{RED} BLOCKED: Amount ${amount} exceeds transfer limit!{RESET}")
             raise ValueError("Security Policy Violation: Amount exceeds $2000 limit.")

        print(f"{GREEN}✔ Policy Passed{RESET}")

    return None