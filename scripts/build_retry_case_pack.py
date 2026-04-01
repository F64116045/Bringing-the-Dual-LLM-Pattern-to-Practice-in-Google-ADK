import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid JSON root in {path}: expected object")
    return data


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _collect_selected_ids(rows: list[dict[str, Any]], criteria: set[str]) -> set[str]:
    selected: set[str] = set()
    for row in rows:
        case_id = row.get("id")
        if not case_id:
            continue

        status = str(row.get("status", ""))
        utility_pass = bool(row.get("utility_pass"))
        security_breach = bool(row.get("security_breach"))
        runtime_ok = bool(row.get("runtime_ok"))

        status_failed = status in {"error", "blocked", "empty"}
        utility_failed = not utility_pass
        security_failed = security_breach
        runtime_failed = not runtime_ok

        if "status_fail" in criteria and status_failed:
            selected.add(str(case_id))
            continue
        if "utility_fail" in criteria and utility_failed:
            selected.add(str(case_id))
            continue
        if "security_breach" in criteria and security_failed:
            selected.add(str(case_id))
            continue
        if "runtime_fail" in criteria and runtime_failed:
            selected.add(str(case_id))
            continue
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a retry case pack by selecting failed cases from one or more JSONL run results."
    )
    parser.add_argument(
        "--cases",
        default="benchmarks/generated/case_pack_v1_50_attacked.json",
        help="Source case pack JSON path.",
    )
    parser.add_argument(
        "--results",
        action="append",
        required=True,
        help=(
            "Run result JSONL path. "
            "Repeat --results to union failures across multiple mode files."
        ),
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output retry case pack JSON path.",
    )
    parser.add_argument(
        "--criteria",
        nargs="+",
        choices=["status_fail", "utility_fail", "security_breach", "runtime_fail"],
        default=["status_fail"],
        help=(
            "Selection criteria. "
            "status_fail selects status in {error, blocked, empty}. "
            "You can combine multiple criteria."
        ),
    )
    args = parser.parse_args()

    cases_path = Path(args.cases)
    result_paths = [Path(p) for p in args.results]
    output_path = Path(args.output)
    criteria = set(args.criteria)

    case_pack = _load_json(cases_path)
    all_cases = case_pack.get("cases")
    if not isinstance(all_cases, list):
        raise ValueError(f"Invalid case pack format in {cases_path}: missing list field `cases`")

    selected_ids: set[str] = set()
    source_result_count = 0
    per_result_counts: dict[str, dict[str, int]] = {}
    for result_path in result_paths:
        rows = _load_jsonl(result_path)
        source_result_count += len(rows)
        ids = _collect_selected_ids(rows, criteria)
        selected_ids.update(ids)
        per_result_counts[str(result_path)] = {
            "row_count": len(rows),
            "selected_id_count": len(ids),
        }

    selected_cases = [c for c in all_cases if str(c.get("id")) in selected_ids]

    payload = {
        "version": "retry-pack-v1",
        "description": (
            "Subset case pack for retry runs, selected from prior result JSONL."
        ),
        "source_cases_path": str(cases_path),
        "source_results_paths": [str(p) for p in result_paths],
        "criteria": sorted(criteria),
        "counts": {
            "source_case_count": len(all_cases),
            "source_result_count": source_result_count,
            "selected_case_count": len(selected_cases),
        },
        "per_result_counts": per_result_counts,
        "cases": selected_cases,
    }
    if len(result_paths) == 1:
        payload["source_results_path"] = str(result_paths[0])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        f"Selected {len(selected_cases)} unique cases from {source_result_count} total result rows "
        f"across {len(result_paths)} file(s)."
    )
    print(f"Wrote retry case pack to: {output_path}")
    if selected_cases:
        print("Selected IDs:")
        for c in selected_cases:
            print(f"- {c.get('id')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
