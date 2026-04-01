import argparse
import json
from pathlib import Path
from typing import Any


ENV_ORDER = ["banking", "slack", "travel", "workspace"]
ENV_LABELS = {
    "banking": "Banking",
    "slack": "Slack",
    "travel": "Travel",
    "workspace": "Workspace",
}

CONFIGS = [
    ("normal", "Normal"),
    ("dual_no_policy", "Dual LLM (No Policy)"),
    ("dual_policy", "Dual LLM + Policy"),
]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def find_latest_run() -> Path:
    root = Path("results/runs")
    if not root.exists():
        raise FileNotFoundError("results/runs not found")
    run_dirs = [p for p in root.iterdir() if p.is_dir()]
    if not run_dirs:
        raise FileNotFoundError("No run directories under results/runs")
    return sorted(run_dirs)[-1]


def attack_match(row: dict[str, Any], scope: str) -> bool:
    attack = str(row.get("attack_type", "none"))
    if scope == "all":
        return True
    if scope == "data_injection":
        return attack == "data_injection"
    return attack != "none"


def format_ratio(n: int, d: int) -> str:
    pct = (n / d * 100.0) if d else 0.0
    return f"{n}/{d} ({pct:.1f}%)"


def metric(rows: list[dict[str, Any]]) -> tuple[int, int, int]:
    total = len(rows)
    utility = sum(1 for r in rows if r.get("utility_pass"))
    asr = sum(1 for r in rows if r.get("security_breach"))
    return utility, asr, total


def render_table(data: dict[str, list[dict[str, Any]]], attack_scope: str) -> str:
    lines: list[str] = []
    lines.append("| Environment | Configuration | Utility | ASR |")
    lines.append("|---|---|---:|---:|")

    totals: dict[str, tuple[int, int, int]] = {}

    for env in ENV_ORDER:
        first = True
        for key, label in CONFIGS:
            rows = [
                r
                for r in data[key]
                if str(r.get("env")) == env and attack_match(r, attack_scope)
            ]
            util_n, asr_n, den = metric(rows)
            if key not in totals:
                totals[key] = (0, 0, 0)
            t_u, t_a, t_d = totals[key]
            totals[key] = (t_u + util_n, t_a + asr_n, t_d + den)

            env_cell = ENV_LABELS.get(env, env) if first else ""
            first = False
            lines.append(
                f"| {env_cell} | {label} | {format_ratio(util_n, den)} | {format_ratio(asr_n, den)} |"
            )

    first = True
    for key, label in CONFIGS:
        util_n, asr_n, den = totals[key]
        env_cell = "Total" if first else ""
        first = False
        lines.append(
            f"| {env_cell} | {label} | {format_ratio(util_n, den)} | {format_ratio(asr_n, den)} |"
        )

    lines.append("")
    lines.append(
        f"_Attack scope for Utility/ASR denominator: `{attack_scope}` "
        "(use `attacked` for attack-only, `all` for all 50 cases)._"
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render environment/config utility+ASR table from experiment JSONL outputs."
    )
    parser.add_argument("--normal", help="Path to baseline JSONL (Normal).")
    parser.add_argument("--dual-no-policy", help="Path to dual_no_policy JSONL.")
    parser.add_argument("--dual-policy", help="Path to dual JSONL (Dual + Policy).")
    parser.add_argument(
        "--attack-scope",
        choices=["attacked", "data_injection", "all"],
        default="attacked",
        help="Rows used as denominator for Utility/ASR.",
    )
    parser.add_argument("--latest-run", action="store_true", help="Use latest results/runs/<run-id>/*.jsonl.")
    parser.add_argument("--output", help="Optional path to write markdown table.")
    args = parser.parse_args()

    normal_path = Path(args.normal) if args.normal else None
    dual_no_policy_path = Path(args.dual_no_policy) if args.dual_no_policy else None
    dual_policy_path = Path(args.dual_policy) if args.dual_policy else None

    if args.latest_run:
        run_dir = find_latest_run()
        if normal_path is None:
            normal_path = run_dir / "baseline.jsonl"
        if dual_no_policy_path is None:
            dual_no_policy_path = run_dir / "dual_no_policy.jsonl"
        if dual_policy_path is None:
            dual_policy_path = run_dir / "dual.jsonl"

    if normal_path is None or dual_no_policy_path is None or dual_policy_path is None:
        raise ValueError("Provide all three: --normal, --dual-no-policy, --dual-policy (or use --latest-run).")

    data = {
        "normal": load_jsonl(normal_path),
        "dual_no_policy": load_jsonl(dual_no_policy_path),
        "dual_policy": load_jsonl(dual_policy_path),
    }
    table_md = render_table(data, args.attack_scope)
    print(table_md)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(table_md, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
