import json
import re
from typing import Any, Dict, List, Optional, Union

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.base_tool import BaseTool, ToolContext
from google.genai import types as genai_types

# Import the manager for type hinting
from .handle_manager import HandleManager

# =========================================================================
# Visualization Constants (ANSI Colors)
# =========================================================================
RESET = "\033[0m"
BOLD = "\033[1m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
PURPLE = "\033[95m"
CYAN = "\033[96m"

# Mapping from JSON schema types to Python types for validation
TYPE_MAP = {
    "int": int,
    "integer": int,
    "float": float,
    "number": (int, float),
    "string": str,
    "str": str,
    "bool": bool,
    "boolean": bool,
    "object": dict,
    "array": list,
    "list": list,
}

PRIMITIVE_TOOL_FIELD_MAP = {
    "get_balance": "balance",
    "get_iban": "iban",
}

# =========================================================================
# Helper Functions
# =========================================================================

def _print_val(value: Any, limit: int = 50) -> str:
    """Helper to format values for logging (truncate long strings)"""
    s = str(value)
    if len(s) > limit:
        return f"{s[:limit]}..."
    return s

def resolve_keys_recursively(obj: Any, handle_manager: HandleManager) -> Any:
    """
    Recursively traverses a dictionary or list to find strings starting with 'key:'.
    Replaces them with the actual raw value from HandleManager.
    """
    if isinstance(obj, dict):
        return {k: resolve_keys_recursively(v, handle_manager) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [resolve_keys_recursively(v, handle_manager) for v in obj]
    elif isinstance(obj, str) and obj.startswith("key:"):
        # Extract UUID
        key = obj.split(":", 1)[1]
        try:
            resolved = handle_manager.resolve_handle(key)
            
            # [Visualization] Show resolution
            val_type = type(resolved).__name__
            print(f"   {CYAN}Key resolved:{RESET} key:{key} → {val_type}")
            print(f"   │  Value: {_print_val(resolved)}")
            
            return resolved
        except KeyError:
            # If key not found, return original string to avoid crashing
            print(f"   {YELLOW}Key not found:{RESET} {key} (keeping as-is)")
            return obj
    return obj


class KeyPlugin(BasePlugin):
    """
    Core Security Plugin with Visualization.
    1. Intercepts Tool Arguments: Translates UUID keys -> Raw Values (Logic: Resolve).
    2. Intercepts Tool Results: Translates Raw Values -> UUID keys (Logic: Sanitize).
    3. Validates Q-LLM schema conformance.
    """

    def __init__(self, handle_manager: HandleManager):
        super().__init__(name="key_plugin")
        object.__setattr__(self, "handle_manager", handle_manager)

    # =========================================================================
    # Before Agent (Log User Input)
    # =========================================================================
    async def before_agent_callback(
        self,
        callback_context: CallbackContext,
        *,
        agent: Optional[BaseAgent] = None,
        **_: Any,
    ):
        agent_name = agent.name if agent else "agent"
        print(f"\n{BOLD}{BLUE} [BeforeAgent]{RESET} {agent_name}")
        print(f"   └─ User Input: {callback_context.user_content}")

    # =========================================================================
    # Before Tool Execution: RESOLVE (UUID -> Raw)
    # =========================================================================
    async def before_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
    ) -> Optional[dict]:
        
        print(f"\n{BOLD}{BLUE} [BeforeTool]{RESET} {tool.name}")
        print(f"   └─ Raw Args: {_print_val(tool_args, 100)}")

        # Special logging for Q-LLM raw request
        if tool.name == "qllm_remote" and "request" in tool_args:
             print(f"   └─ Q-LLM Request Payload: {_print_val(tool_args['request'], 100)}")

        # 1. Standard recursive resolution for normal arguments
        resolved_args = resolve_keys_recursively(tool_args, self.handle_manager)

        # 2. Special handling for 'qllm_remote' tool
        if tool.name == "qllm_remote" and "request" in resolved_args:
            req_str = resolved_args["request"]

            # If planner provides flat args, package them into one JSON payload
            # so remote Q-LLM definitely sees request/source/format together.
            if (
                isinstance(req_str, str)
                and "source" in resolved_args
                and "format" in resolved_args
                and isinstance(resolved_args.get("format"), dict)
            ):
                payload = {
                    "request": req_str,
                    "source": resolved_args.get("source"),
                    "format": resolved_args.get("format"),
                }
                resolved_args.clear()
                resolved_args["request"] = json.dumps(payload, ensure_ascii=False)
                print(f"\n{BOLD}{CYAN} [Packed Q-LLM Payload]{RESET}")
                print(f"   └─ Payload: {_print_val(resolved_args['request'], 100)}")

            # If request itself is nested JSON, recursively resolve inner keys.
            req_str = resolved_args.get("request")
            if isinstance(req_str, str) and req_str.lstrip().startswith("{"):
                try:
                    print(f"\n{BOLD}{CYAN} [Resolving Nested JSON in Q-LLM Request]{RESET}")
                    req_data = json.loads(req_str)
                    resolved_req_data = resolve_keys_recursively(req_data, self.handle_manager)
                    resolved_args["request"] = json.dumps(resolved_req_data, ensure_ascii=False)
                    print(f"   └─ Resolved JSON Payload: {_print_val(resolved_args['request'], 100)}")
                except json.JSONDecodeError:
                    print(f"{RED}JSON parse error in qllm_remote request{RESET}")

        # Update the tool arguments in-place
        if resolved_args != tool_args:
            print(f"\n{BOLD}{CYAN} [In-place Args Modification]{RESET}")
            tool_args.clear()
            tool_args.update(resolved_args)
            print(f"   {GREEN}Args modified in-place, Tool ready to execute.{RESET}")
        
        return None

    # =========================================================================
    # Schema Validation (Helper)
    # =========================================================================
    def _extract_expected_format(self, tool_args: dict[str, Any]) -> dict[str, Any]:
        """Extract expected schema from flat or nested qllm request args."""
        if isinstance(tool_args.get("format"), dict):
            return tool_args["format"]

        req_payload = tool_args.get("request", "{}")
        if isinstance(req_payload, str):
            try:
                req_json = json.loads(req_payload)
                if isinstance(req_json, dict) and isinstance(req_json.get("format"), dict):
                    return req_json["format"]
            except json.JSONDecodeError:
                return {}
        return {}

    def _validate_qllm_schema(self, tool_args: dict, result: Any) -> bool:
        """
        Ensures the Q-LLM's output matches the schema requested by the P-LLM.
        """
        try:
            expected_format = self._extract_expected_format(tool_args)

            parsed_result = result
            if isinstance(result, str):
                try:
                    parsed_result = json.loads(result)
                except json.JSONDecodeError:
                    return False 

            if not isinstance(parsed_result, dict):
                return False

            errors = []
            for field, expected_type_name in expected_format.items():
                if field not in parsed_result:
                    errors.append(f"Missing field: {field}")
                    continue
                
                value = parsed_result[field]
                if value is None:
                    # Null is allowed for unavailable/unparseable fields.
                    continue
                py_type = TYPE_MAP.get(expected_type_name.lower())
                
                if py_type and not isinstance(value, py_type):
                    errors.append(f"Field '{field}' expected {expected_type_name}, got {type(value).__name__}")

            if errors:
                print(f"{RED}[SchemaCheck] Errors:{RESET}")
                for e in errors:
                    print(f"   - {e}")
                return False

            print(f"{GREEN}[SchemaCheck] All fields match expected types ✔{RESET}")
            return True

        except Exception as e:
            print(f"{RED}[SchemaCheck] Exception:{RESET} {e}")
            return False

    # =========================================================================
    # After Tool Execution: SANITIZE (Raw -> UUID)
    # =========================================================================
    async def after_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: Optional[dict[str, Any]] = None,
        tool_context: ToolContext,
        result: Any = None,
        args: Optional[dict[str, Any]] = None,
        tool_response: Any = None,
        **_: Any,
    ) -> Optional[dict]:
        if tool_args is None:
            tool_args = args or {}
        if result is None:
            result = tool_response
        
        print(f"\n{BOLD}{GREEN} [AfterTool]{RESET} {tool.name}")
        print(f"   ├─ Output Type: {type(result).__name__}")
        print(f"   └─ Raw Output: {_print_val(result, 100)}")

        # 1. Validation for Q-LLM outputs
        if tool.name == "qllm_remote":
            expected_format = self._extract_expected_format(tool_args)

            if isinstance(result, dict) and all(
                isinstance(v, str) and v.startswith("key:") for v in result.values()
            ):
                print(f"   {GREEN}✓ Q-LLM bypass response detected (already sanitized){RESET}")
                return result
            if result in (None, ""):
                print(f"   {YELLOW}Q-LLM empty response, returning null-filled fallback.{RESET}")
                result = {k: None for k in expected_format} if expected_format else {"output": None}
            is_valid = self._validate_qllm_schema(tool_args, result)
            if not is_valid:
                print(f"   {YELLOW}Schema mismatch from Q-LLM, returning null-filled fallback.{RESET}")
                result = {k: None for k in expected_format} if expected_format else {"output": None}
            else:
                 print(f"   {GREEN}✓ Schema Validated{RESET}")

        # 2. Store and Sanitize
        return self._sanitize_and_store(tool.name, result)

    def _sanitize_and_store(self, tool_name: str, result: Any) -> Optional[dict]:
        """
        Helper to store raw results in HandleManager and return a sanitized dictionary.
        """
        if result is None:
            return None

        print(f"\n{BOLD}{PURPLE} [Storing Result & Sanitizing]{RESET}")

        # Try to parse string results as JSON
        parsed_result = result
        if isinstance(result, str):
            try:
                cleaned = result.strip()
                cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
                cleaned = re.sub(r"```$", "", cleaned).strip()
                parsed_result = json.loads(cleaned)
                print(f"   ├─ Parsed JSON string successfully")
            except json.JSONDecodeError:
                parsed_result = result 

        # Case A: Result is a Dictionary -> Sanitize each field
        if isinstance(parsed_result, dict):
            sanitized_dict = {}
            for field, value in parsed_result.items():
                key = self.handle_manager.create_handle(
                    value, type_hint=f"tool:{tool_name}:{field}"
                )
                sanitized_dict[field] = f"key:{key}"
                print(f"   ├─ {GREEN}Stored:{RESET} {field} → key:{key}")
                print(f"   │  Value: {_print_val(value)}")
            
            print(f"   └─ {GREEN}Returning sanitized dict{RESET}")
            return sanitized_dict

        # Case B: Result is a primitive -> Sanitize the whole thing
        key = self.handle_manager.create_handle(
            parsed_result, type_hint=f"tool:{tool_name}"
        )
        print(f"   └─ {GREEN}Stored full result:{RESET} key:{key}")
        field_name = PRIMITIVE_TOOL_FIELD_MAP.get(tool_name, "output")
        return {field_name: f"key:{key}"}

    # =========================================================================
    # After Agent: Final Display Resolution
    # =========================================================================
    async def after_agent_callback(
        self,
        callback_context: CallbackContext,
        *,
        agent: Optional[BaseAgent] = None,
        **_: Any,
    ):
        agent_name = agent.name if agent else "agent"
        print(f"\n{BOLD}{YELLOW} [AfterAgent]{RESET} {agent_name}")

        try:
            session = callback_context._invocation_context.session
            events = getattr(session, "events", [])

            last_model_event = next(
                (e for e in reversed(events) if e.content and getattr(e.content, "role", None) == "model"),
                None,
            )

            if not last_model_event:
                return

            original_content: genai_types.Content = last_model_event.content
            texts = [p.text for p in getattr(original_content, "parts", []) if getattr(p, "text", None)]
            full_text = " ".join(texts)
            
            print(f"   ├─ Original Response (with keys): {_print_val(full_text, 100)}")

            def replace_match(match):
                key = match.group(1)
                try:
                    resolved_value = self.handle_manager.resolve_handle(key)
                    print(f"   {CYAN}Final Display Resolve:{RESET} key:{key} -> {_print_val(resolved_value)}")
                    if isinstance(resolved_value, (dict, list, tuple)):
                        return json.dumps(resolved_value, ensure_ascii=False)
                    return str(resolved_value)
                except KeyError:
                    print(f"{RED}Key not found for display:{RESET} {key}")
                    return f"key:{key}" 

            modified_text = re.sub(r"key:([A-Za-z0-9\-]+)", replace_match, full_text)

            if modified_text != full_text:
                print(f"   {GREEN}Response modified for user display.{RESET}")
                return genai_types.Content(parts=[genai_types.Part(text=modified_text)])
            else:
                 print(f"   └─ No keys needed resolving.")

        except Exception as e:
            print(f"{RED}[AfterAgent Error]{RESET} {e}")
