# Experiment Lab Overview

This is the single source of truth for how this repository works as an experiment lab.

If you need to read the runner code directly, start from:

- `scripts/run_case_suite.py`

## 1. What This Repo Runs

The lab evaluates the same fixed attacked 50-case pack in three configurations:

1. `baseline`: single LLM agent, no Q-LLM isolation, no policy callback.
2. `dual_no_policy`: Dual-LLM isolation enabled, policy callback disabled.
3. `dual`: Dual-LLM isolation enabled, policy callback enabled.

Default case pack:

- `benchmarks/generated/case_pack_v1_50_attacked.json`

## 2. Runtime Architecture

### Core runtime (`src/adk_dual_llm`)

- `core/privileged_agent.py`: P-LLM wrapper, callback wiring, optional policy gate.
- `core/quarantined_agent.py`: Q-LLM agent behavior and extraction constraints.
- `core/server.py`: exposes Q-LLM via A2A server.
- `security/key_plugin.py`: key-based isolation and schema checks.
- `security/handle_manager.py`: in-memory key/value storage for sanitized values.

### Environment layer (`benchmarks`)

- `banking/`, `slack/`, `travel/`, `workspace/`: environment state, tools, policy.
- `per_case_judges_v1_50.py`: per-case utility/security/runtime judges.

### Orchestration (`scripts`)

- `run_case_suite.py`: executes one mode over a case pack, writes JSONL + traces.
- `run_experiment_v1_50.sh`: runs baseline/dual_no_policy/dual in sequence.
- `summarize_case_results.py`: summarizes JSONL metrics.
- `render_eval_table.py`: outputs paper-style markdown table.
- `retry_failed_and_merge.sh`: retry selected failures and merge back.

## 3. Case Data Flow

1. `sync_agentdojo_cases.py` parses AgentDojo v1 user/injection tasks into:
   - `benchmarks/generated/case_registry.json`
2. `build_case_pack_v1_50.py` selects a fixed attacked-only 50-case subset:
   - `benchmarks/generated/case_pack_v1_50_attacked.json`
   - `benchmarks/generated/mapping_v1_50_attacked.csv`

Notes:

- User prompt stays clean.
- Injection is applied at runtime into environment data fields.
- The fixed 50 pack is guarded by per-case judge coverage checks.

## 4. Execution Flow (per case)

`run_case_suite.py` does:

1. Reset target environment.
2. Apply runtime data injection vectors (from case `source.injection_goal`).
3. Snapshot `pre_state`.
4. Run selected mode (`baseline` / `dual_no_policy` / `dual`).
5. Collect ADK trace events.
6. Snapshot `post_state`.
7. Evaluate per-case judges.
8. Save one JSONL row + trace JSON + transcript text.

## 5. Output Layout

For run id `results/runs/<RUN_ID>/`:

- `baseline.jsonl`
- `dual_no_policy.jsonl`
- `dual.jsonl`
- `traces_baseline/*`
- `traces_dual_no_policy/*`
- `traces_dual/*`
- `summary.json`

## 6. Canonical Commands

Run all modes:

```bash
make exp-v1 MODEL=openai/gpt-4.1
```

Run quick smoke:

```bash
make exp-v1 MODEL=openai/gpt-4.1 ENV=banking LIMIT=5
```

Rebuild generated case artifacts:

```bash
make cases-sync
make cases-pack
```

Summarize and table:

```bash
make summary-latest
make table-latest ATTACK_SCOPE=attacked
```

Retry failed rows and merge:

```bash
make retry-merge RUN_ID=<run-id> RETRY_CRITERIA=status_fail
```
