import asyncio
import argparse
import warnings
from google.adk.runners import InMemoryRunner
from google.genai import types

# Import our Core
from src.adk_dual_llm.core.privileged_agent import PrivilegedAgent

# Import Benchmark Data
from benchmarks.banking.tools import get_banking_tools
from benchmarks.banking.policy import banking_security_policy

# Warnings Config
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", message=".*Protobuf gencode version.*")

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
BLUE = "\033[94m"
PURPLE = "\033[95m"

async def main(model_name: str = "gemini-2.0-flash"):
    print(f"{PURPLE}{BOLD}=== Initializing Dual LLM Banking Agent ==={RESET}")

    # 1. Instantiate the P-LLM (This automatically sets up KeyPlugin & Q-LLM tool)
    agent = PrivilegedAgent(
        model=model_name,
        tools=get_banking_tools(),          # Inject Banking Tools
        policy_callback=banking_security_policy, # Inject Banking Policy
        qllm_url="http://localhost:8001"    # Point to Q-LLM Server
    )

    # 2. Setup Runner
    runner = InMemoryRunner(
        agent=agent,
        app_name="banking_dual_llm",
        # Note: KeyPlugin is already attached inside PrivilegedAgent, no need to add here
    )

    session = await runner.session_service.create_session(user_id="user1", app_name="banking_dual_llm")

    print(f"{PURPLE}Ready. Type 'exit' to quit.{RESET}\n")

    while True:
        try:
            user_input = input(f"{GREEN}{BOLD}User: {RESET}").strip()
            if not user_input: continue
            if user_input.lower() in ["exit", "quit"]: break

            print(f"\n{BLUE}{BOLD}Agent: {RESET}", end="", flush=True)
            
            async for event in runner.run_async(
                user_id="user1",
                session_id=session.id,
                new_message=types.Content(role="user", parts=[types.Part.from_text(text=user_input)]),
            ):
                # Stream Output
                if event.content and hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                             print(part.text, end="", flush=True)
            print("\n")

        except KeyboardInterrupt:
            break
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="gemini-2.0-flash", help="Model name for P-LLM")
    args = parser.parse_args()
    
    asyncio.run(main(args.model))