import argparse
import json
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Merge retry JSONL results into a base JSONL by case id. "
            "Rows with matching id are replaced by retry rows."
        )
    )
    parser.add_argument("--base", required=True, help="Base JSONL path (full run result).")
    parser.add_argument(
        "--retry",
        action="append",
        required=True,
        help="Retry JSONL path. Repeat --retry to apply multiple files in order.",
    )
    parser.add_argument("--output", required=True, help="Output merged JSONL path.")
    parser.add_argument("--id-field", default="id", help="Row key used to match rows (default: id).")
    parser.add_argument(
        "--append-missing",
        action="store_true",
        help="Append retry rows whose ids are not found in base.",
    )
    args = parser.parse_args()

    base_path = Path(args.base)
    retry_paths = [Path(p) for p in args.retry]
    output_path = Path(args.output)
    id_field = args.id_field

    base_rows = load_jsonl(base_path)
    base_index: dict[str, int] = {}
    duplicate_base_ids: set[str] = set()
    for idx, row in enumerate(base_rows):
        row_id = str(row.get(id_field, "")).strip()
        if not row_id:
            continue
        if row_id in base_index:
            duplicate_base_ids.add(row_id)
            continue
        base_index[row_id] = idx

    replaced_ids: set[str] = set()
    missing_retry_rows: dict[str, dict[str, Any]] = {}
    total_retry_rows = 0

    for retry_path in retry_paths:
        retry_rows = load_jsonl(retry_path)
        total_retry_rows += len(retry_rows)
        for row in retry_rows:
            row_id = str(row.get(id_field, "")).strip()
            if not row_id:
                continue
            if row_id in base_index:
                base_rows[base_index[row_id]] = row
                replaced_ids.add(row_id)
            else:
                missing_retry_rows[row_id] = row

    appended = 0
    if args.append_missing and missing_retry_rows:
        for row_id in sorted(missing_retry_rows):
            base_rows.append(missing_retry_rows[row_id])
            appended += 1

    write_jsonl(output_path, base_rows)

    print(f"Base rows: {len(base_rows)}")
    print(f"Total retry rows seen: {total_retry_rows}")
    print(f"Replaced rows: {len(replaced_ids)}")
    print(f"Retry ids not found in base: {len(missing_retry_rows)}")
    print(f"Appended missing rows: {appended}")
    if duplicate_base_ids:
        print(f"Warning: duplicate ids in base (kept first occurrence): {len(duplicate_base_ids)}")
    print(f"Wrote merged results to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
