import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

# Allow running this script directly from project root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from google.adk.runners import InMemoryRunner
from google.genai import types

from benchmarks.banking.policy import banking_security_policy
from benchmarks.banking.tools import get_banking_tools, reset_banking_env
from benchmarks.slack.policy import slack_security_policy
from benchmarks.slack.tools import get_slack_tools, reset_slack_env
from benchmarks.travel.policy import travel_security_policy
from benchmarks.travel.tools import get_travel_tools, reset_travel_env
from benchmarks.workspace.policy import workspace_security_policy
from benchmarks.workspace.tools import get_workspace_tools, reset_workspace_env
from src.adk_dual_llm.core.privileged_agent import PrivilegedAgent

DEFAULT_MODEL = os.getenv("PLLM_MODEL", "gemini-2.0-flash")
DEFAULT_QLLM_URL = os.getenv("QLLM_URL", "http://localhost:8001")


@dataclass
class EnvConfig:
    app_name: str
    user_id: str
    reset_fn: Callable[[], None]
    tools_fn: Callable[[], list[Any]]
    policy_fn: Callable[..., Any]


ENV_CONFIGS: dict[str, EnvConfig] = {
    "banking": EnvConfig(
        app_name="banking_suite_runner",
        user_id="suite_user_banking",
        reset_fn=reset_banking_env,
        tools_fn=get_banking_tools,
        policy_fn=banking_security_policy,
    ),
    "slack": EnvConfig(
        app_name="slack_suite_runner",
        user_id="suite_user_slack",
        reset_fn=reset_slack_env,
        tools_fn=get_slack_tools,
        policy_fn=slack_security_policy,
    ),
    "travel": EnvConfig(
        app_name="travel_suite_runner",
        user_id="suite_user_travel",
        reset_fn=reset_travel_env,
        tools_fn=get_travel_tools,
        policy_fn=travel_security_policy,
    ),
    "workspace": EnvConfig(
        app_name="workspace_suite_runner",
        user_id="suite_user_workspace",
        reset_fn=reset_workspace_env,
        tools_fn=get_workspace_tools,
        policy_fn=workspace_security_policy,
    ),
}


def _sanitize_user_text(text: str) -> str:
    return text.encode("utf-8", errors="replace").decode("utf-8")


def load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data.get("cases", [])
    if not isinstance(cases, list):
        raise ValueError("Invalid case file format: `cases` must be a list.")
    return cases


async def run_single_case(
    case: dict[str, Any],
    model_name: str,
    qllm_url: str,
) -> dict[str, Any]:
    env_name = case["env"]
    cfg = ENV_CONFIGS[env_name]

    cfg.reset_fn()
    agent = PrivilegedAgent(
        model=model_name,
        tools=cfg.tools_fn(),
        policy_callback=cfg.policy_fn,
        qllm_url=qllm_url,
    )
    runner = InMemoryRunner(agent=agent, app_name=cfg.app_name)
    session = await runner.session_service.create_session(
        user_id=cfg.user_id, app_name=cfg.app_name
    )

    prompt = _sanitize_user_text(case["prompt"])
    started = datetime.utcnow()
    text_parts: list[str] = []
    blocked = False
    error: str | None = None

    try:
        async for event in runner.run_async(
            user_id=cfg.user_id,
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part.from_text(text=prompt)]),
        ):
            if event.content and hasattr(event.content, "parts"):
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        text_parts.append(part.text)
    except Exception as exc:
        error = str(exc)
        if "Security Policy Violation" in error:
            blocked = True

    ended = datetime.utcnow()
    output_text = "".join(text_parts).strip()
    status = "pass"
    if blocked:
        status = "blocked"
    elif error:
        status = "error"
    elif not output_text:
        status = "empty"

    return {
        "id": case["id"],
        "env": env_name,
        "prompt": case["prompt"],
        "tags": case.get("tags", []),
        "status": status,
        "blocked": blocked,
        "error": error,
        "output_text": output_text,
        "started_at_utc": started.isoformat() + "Z",
        "ended_at_utc": ended.isoformat() + "Z",
        "duration_sec": round((ended - started).total_seconds(), 3),
    }


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run batch cases for ADK Dual-LLM benchmark."
    )
    parser.add_argument(
        "--cases",
        default="benchmarks/case_registry.json",
        help="Path to case registry JSON file.",
    )
    parser.add_argument(
        "--env",
        choices=["all", "banking", "slack", "travel", "workspace"],
        default="all",
        help="Run only a single environment or all.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="P-LLM model name.")
    parser.add_argument(
        "--qllm-url", default=DEFAULT_QLLM_URL, help="Q-LLM A2A server URL."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max number of cases to run (0 means all selected).",
    )
    parser.add_argument(
        "--output",
        default="results/case-suite-results.jsonl",
        help="JSONL output file path.",
    )
    args = parser.parse_args()

    selected_cases = load_cases(Path(args.cases))
    if args.env != "all":
        selected_cases = [c for c in selected_cases if c.get("env") == args.env]
    if args.limit > 0:
        selected_cases = selected_cases[: args.limit]

    if not selected_cases:
        print("No cases selected. Check --env and --cases.")
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Running {len(selected_cases)} cases...")
    results: list[dict[str, Any]] = []
    for idx, case in enumerate(selected_cases, start=1):
        print(f"[{idx}/{len(selected_cases)}] {case['id']} ({case['env']})")
        result = await run_single_case(case, args.model, args.qllm_url)
        results.append(result)
        with output_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

    summary = {"pass": 0, "blocked": 0, "error": 0, "empty": 0}
    for r in results:
        summary[r["status"]] = summary.get(r["status"], 0) + 1

    print("\nSummary:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Results saved to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
