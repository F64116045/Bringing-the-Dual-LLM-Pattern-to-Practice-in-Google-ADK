# Scripts Index

This directory mixes core runners and utility scripts. Use this index as the quick map.

## Core (daily use)

- `run_case_suite.py`
  - Main runner for one mode.
  - Inputs: case pack JSON, env filter, model, mode.
  - Outputs: JSONL result rows and optional trace files.
- `run_experiment_v1_50.sh`
  - Runs `baseline`, `dual_no_policy`, `dual` sequentially.
  - Writes results under `results/runs/<run-id>/`.
- `summarize_case_results.py`
  - Aggregates JSONL into summary metrics (overall/by env/by attack).
- `render_eval_table.py`
  - Converts JSONL outputs into paper-style markdown table.

## Case generation

- `sync_agentdojo_cases.py`
  - Parses AgentDojo task sources to build `case_registry.json`.
- `build_case_pack_v1_50.py`
  - Selects and enriches fixed attacked-only 50-case pack.

## Retry workflow (token saving)

- `retry_failed_and_merge.sh`
  - Builds retry packs, reruns failed cases, merges updated rows.
- `build_retry_case_pack.py`
  - Selects failed case IDs from one or multiple JSONL files.
- `merge_retry_results.py`
  - Replaces matching IDs in base JSONL with retry rows.

## Service startup

- `start_qllm.py`
  - Starts Q-LLM A2A server process.
