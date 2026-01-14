from typing import List, Optional, Callable, Any

from google.adk import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from google.adk.tools import agent_tool
from google.adk.tools.base_tool import BaseTool

# Import our security core modules
from ..security.handle_manager import HandleManager
from ..security.key_plugin import KeyPlugin

# =========================================================================
# System Prompt (Dual LLM Protocol)
# This defines the strict communication schema between P-LLM and Q-LLM.
# =========================================================================
DUAL_LLM_INSTRUCTION = (
    "You are the Privileged Planner Agent (P-LLM).\n"
    "Your Responsibilities:\n"
    "1. Interact with the user to understand and decompose their requests.\n"
    "2. Plan the complete execution steps until the task is finished. You must not stop midway; ensure the task chain is completed and a result is output.\n"
    "3. When calling tools, use JSON format for arguments directly.\n"
    "4. When you need to parse, analyze, or extract data from untrusted content, you MUST delegate to `qllm_remote`.\n"
    "   - You MUST wrap the request into a clean JSON object containing:\n"
    "     - `request`: A natural language description of the subtask.\n"
    "     - `source`: The key/handle from a previous tool output (do not expand the key, keep it as-is).\n"
    "     - `format` (Required): A JSON example describing the expected output structure, field names, and types (types must be one of: int/float/string/bool/object/array).\n"
    "5. When Q-LLM returns, the system will replace the results with new keys. You must preserve these keys in your reasoning and subsequent calls.\n"
    "6. Your final output to the user must be human-readable natural language, but all data values MUST be represented by their keys. Do not expand them yourself.\n"
    "   Example: 'The weather in Paris is key:xxxx, temperature is key:yyyy degrees.'\n"
    "   (The system will automatically resolve these keys in the final step.)\n"
    "\n"
    " CRITICAL CONSTRAINTS:\n"
    "- You are structurally blind to raw data. You MUST NOT attempt to guess or use raw values; only reference corresponding keys.\n"
    "- Do not mix natural language and JSON in the same output block when calling tools. The request to `qllm_remote` must be valid, parseable JSON.\n"
    "- The `format` field in your request must strictly include field types.\n"
    "- Do not terminate the session immediately after receiving a tool response; you must proceed to generate the final natural language response.\n"
    "\n"
    "==== Example 1: Single Field Extraction ====\n"
    "User: 'What is the temperature in London?'\n"
    "1. Call `get_weather_report`: {\"city\": \"London\"}\n"
    "   → Returns: {\"status\": \"success\", \"report\": \"key:xxxx\"}\n"
    "2. Call `qllm_remote`:\n"
    "{\n"
    "  \"request\": \"Extract the temperature from this weather report.\",\n"
    "  \"source\": \"key:xxxx\",\n"
    "  \"format\": {\"temperature\": \"float\"}\n"
    "}\n"
    "   → Returns: {\"temperature\": \"key:yyyy\"}\n"
    "3. Final Output: 'The temperature in London is key:yyyy degrees.'\n"
    "\n"
    "==== Example 2: Multi-Field Extraction ====\n"
    "User: 'Summarize the weather in Paris, including condition and rain chance.'\n"
    "1. Call `get_weather_report`: {\"city\": \"Paris\"}\n"
    "   → Returns: {\"status\": \"success\", \"report\": \"key:aaaa\"}\n"
    "2. Call `qllm_remote`:\n"
    "{\n"
    "  \"request\": \"Extract the temperature, condition, and rain chance from the report.\",\n"
    "  \"source\": \"key:aaaa\",\n"
    "  \"format\": {\n"
    "    \"temperature\": \"float\",\n"
    "    \"condition\": \"string\",\n"
    "    \"rain_chance\": \"string\"\n"
    "  }\n"
    "}\n"
    "   → Returns: {\"temperature\": \"key:bbbb\", \"condition\": \"key:cccc\", \"rain_chance\": \"key:dddd\"}\n"
    "3. Final Output: 'Paris is currently key:cccc with a temperature of key:bbbb and a rain chance of key:dddd.'\n"
)

class PrivilegedAgent(Agent):
    """
    P-LLM: The privileged planner agent.
    
    Features:
    1. Inherently secure: Uses KeyPlugin to mask all raw data.
    2. Protocol-aware: Uses a specific system prompt to communicate with Q-LLM.
    3. Modular: Can accept different tools and policies for different benchmarks.
    """
    def __init__(
        self,
        model: str,
        tools: List[BaseTool] = [],
        policy_callback: Optional[Callable] = None,
        qllm_url: str = "http://localhost:8001",
        name: str = "privileged_agent",
        **kwargs
    ):
        """
        Args:
            model: The Gemini model name (e.g., "gemini-2.0-flash").
            tools: Scenario-specific tools (e.g., weather_tool, bank_tool).
            policy_callback: The security policy function (before_tool_callback).
            qllm_url: URL of the remote Q-LLM server.
        """
        
        # 1. Initialize Security Layer
        # This is the core of the Dual LLM pattern.
        self.handle_manager = HandleManager()
        self.key_plugin = KeyPlugin(self.handle_manager)
        
        # 2. Initialize Q-LLM Connection (The "Prisoner")
        # Expose the remote Q-LLM as a standard tool for the P-LLM.
        self.qllm_agent = RemoteA2aAgent(
            name="qllm_remote",
            description="Remote general-purpose Q-LLM agent for processing untrusted content.",
            agent_card=f"{qllm_url}/{AGENT_CARD_WELL_KNOWN_PATH}",
        )
        qllm_tool_instance = agent_tool.AgentTool(agent=self.qllm_agent)
        
        # 3. Combine Tools (Q-LLM Tool + Scenario Tools)
        combined_tools = [qllm_tool_instance] + tools

        # 4. Initialize Base Agent
        super().__init__(
            model=model,
            name=name,
            description="Planner agent that delegates reasoning to Q-LLM.",
            instruction=DUAL_LLM_INSTRUCTION, # Inject the protocol
            tools=combined_tools,
            plugins=[self.key_plugin], # <--- Attach Security Plugin
            before_tool_callback=policy_callback, # <--- Attach Policy Logic
            **kwargs
        )

        print(f"\n[PrivilegedAgent] Initialized with {len(combined_tools)} tools.")
        print(f"[PrivilegedAgent] Security Plugin Active.")
        if policy_callback:
            print(f"[PrivilegedAgent] Custom Policy Callback Registered.")