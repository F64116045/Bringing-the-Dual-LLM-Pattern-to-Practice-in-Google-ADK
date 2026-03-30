import re
from typing import Any, Optional
from google.adk.tools.base_tool import BaseTool, ToolContext

RED = "\033[91m"
RESET = "\033[0m"
GREEN = "\033[92m"

# Authorized Domains
INTERNAL_DOMAIN = "bluesparrowtech.com"
TRUSTED_PARTNERS = ["clientcorp.com", "bilgen-corp.com"]
SENSITIVE_TERMS = [
    "security code",
    "verification code",
    "2fa",
    "one-time password",
    "otp",
    "password",
]


def _email_domain(addr: str) -> str:
    if "@" not in addr:
        return ""
    return addr.rsplit("@", 1)[1].lower().strip()


def _contains_sensitive_data(text: str) -> bool:
    lowered = (text or "").lower()
    if any(term in lowered for term in SENSITIVE_TERMS):
        return True
    # Common short OTP shape in test prompts and emails.
    if re.search(r"\b\d{6}\b", lowered):
        return True
    return False

def workspace_security_policy(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext
) -> Optional[dict]:
    """
    Security Policy for Workspace Benchmark.
    """
    
    # Policy 1: prevent exfiltration of likely secrets to untrusted domains.
    if tool.name == "send_email":
        to_list = args.get("to") or []
        recipients_list = args.get("recipients") or []
        cc_list = args.get("cc") or []
        bcc_list = args.get("bcc") or []
        recipients = [*to_list, *recipients_list, *cc_list, *bcc_list]

        body = args.get("body", "")
        subject = args.get("subject", "")
        payload = f"{subject}\n{body}"

        print(f"{RED}[Policy Check]{RESET} send_email recipients={recipients}")

        for email in recipients:
            domain = _email_domain(email)
            trusted = domain == INTERNAL_DOMAIN or domain in TRUSTED_PARTNERS
            if not trusted and _contains_sensitive_data(payload):
                print(f"{RED} BLOCKED: Sensitive data to untrusted domain {domain}!{RESET}")
                raise ValueError(
                    f"Security Policy Violation: sensitive outbound email to {email} is blocked."
                )

        print(f"{GREEN}✔ Policy Passed{RESET}")

    return None
