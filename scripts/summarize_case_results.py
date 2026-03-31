import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    status = Counter(r.get("status", "unknown") for r in rows)
    utility_pass = sum(1 for r in rows if r.get("utility_pass"))
    security_breach = sum(1 for r in rows if r.get("security_breach"))
    runtime_ok = sum(1 for r in rows if r.get("runtime_ok"))

    by_env: dict[str, dict[str, Any]] = defaultdict(lambda: {"total": 0, "status": Counter(), "utility_pass": 0, "security_breach": 0, "runtime_ok": 0})
    for r in rows:
        env = r.get("env", "unknown")
        by_env[env]["total"] += 1
        by_env[env]["status"][r.get("status", "unknown")] += 1
        by_env[env]["utility_pass"] += 1 if r.get("utility_pass") else 0
        by_env[env]["security_breach"] += 1 if r.get("security_breach") else 0
        by_env[env]["runtime_ok"] += 1 if r.get("runtime_ok") else 0

    out = {
        "total": total,
        "status": dict(status),
        "utility_pass": utility_pass,
        "security_breach": security_breach,
        "runtime_ok": runtime_ok,
        "rates": {
            "utility_pass": round(utility_pass / total, 4) if total else 0.0,
            "security_breach": round(security_breach / total, 4) if total else 0.0,
            "runtime_ok": round(runtime_ok / total, 4) if total else 0.0,
        },
        "by_env": {},
    }
    for env, data in sorted(by_env.items()):
        t = data["total"]
        out["by_env"][env] = {
            "total": t,
            "status": dict(data["status"]),
            "utility_pass": data["utility_pass"],
            "security_breach": data["security_breach"],
            "runtime_ok": data["runtime_ok"],
            "rates": {
                "utility_pass": round(data["utility_pass"] / t, 4) if t else 0.0,
                "security_breach": round(data["security_breach"] / t, 4) if t else 0.0,
                "runtime_ok": round(data["runtime_ok"] / t, 4) if t else 0.0,
            },
        }
    return out


def find_latest_run() -> Path:
    root = Path("results/runs")
    if not root.exists():
        raise FileNotFoundError("results/runs not found")
    run_dirs = [p for p in root.iterdir() if p.is_dir()]
    if not run_dirs:
        raise FileNotFoundError("No run directories under results/runs")
    return sorted(run_dirs)[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize benchmark JSONL results.")
    parser.add_argument("--baseline", help="Path to baseline JSONL.")
    parser.add_argument("--dual", help="Path to dual JSONL.")
    parser.add_argument("--output", help="Optional path to write summary JSON.")
    parser.add_argument("--latest-run", action="store_true", help="Use latest results/runs/<run-id> baseline/dual JSONL files.")
    args = parser.parse_args()

    baseline_path: Path | None = Path(args.baseline) if args.baseline else None
    dual_path: Path | None = Path(args.dual) if args.dual else None

    if args.latest_run:
        run_dir = find_latest_run()
        if baseline_path is None:
            candidate = run_dir / "baseline.jsonl"
            if candidate.exists():
                baseline_path = candidate
        if dual_path is None:
            candidate = run_dir / "dual.jsonl"
            if candidate.exists():
                dual_path = candidate

    if baseline_path is None and dual_path is None:
        raise ValueError("Provide --baseline and/or --dual (or --latest-run).")

    summary: dict[str, Any] = {}
    if baseline_path is not None and baseline_path.exists():
        baseline_rows = load_jsonl(baseline_path)
        summary["baseline"] = {"path": str(baseline_path), "summary": summarize(baseline_rows)}
    if dual_path is not None and dual_path.exists():
        dual_rows = load_jsonl(dual_path)
        summary["dual"] = {"path": str(dual_path), "summary": summarize(dual_rows)}

    if "baseline" in summary and "dual" in summary:
        b = summary["baseline"]["summary"]
        d = summary["dual"]["summary"]
        summary["compare"] = {
            "delta_utility_pass_rate": round(d["rates"]["utility_pass"] - b["rates"]["utility_pass"], 4),
            "delta_security_breach_rate": round(d["rates"]["security_breach"] - b["rates"]["security_breach"], 4),
            "delta_runtime_ok_rate": round(d["rates"]["runtime_ok"] - b["rates"]["runtime_ok"], 4),
        }

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
