# Project Structure

This repository is organized around three layers:

## 1) Runtime (`src/adk_dual_llm`)
- `core/`: privileged/quarantined agent wiring, model resolution, server app.
- `security/`: key/plugin layer and policy-enforcement hooks.

## 2) Benchmark Environments (`benchmarks`)
- `banking/`, `slack/`, `travel/`, `workspace/`: mock environment state + tools + policy.
- `generated/`: auto-generated experiment artifacts.
  - `case_registry.json`: full generated case registry.
  - `case_pack_v1_50.json`: curated 50-case pack for quick benchmark runs.
  - `mapping_v1_50.csv`: mapping from curated cases back to source task IDs.

## 3) Orchestration Scripts (`scripts`)
- `run_case_suite.py`: main benchmark runner (`baseline` / `dual`) + assertions + traces.
- `sync_agentdojo_cases.py`: sync user/injection tasks from AgentDojo into `benchmarks/generated/case_registry.json`.
- `build_case_pack_v1_50.py`: select and enrich strict 50-case pack from registry.

## End-to-end Flow
1. Generate/refresh registry: `scripts/sync_agentdojo_cases.py` -> `benchmarks/generated/case_registry.json`
2. Build curated pack: `scripts/build_case_pack_v1_50.py` -> `benchmarks/generated/case_pack_v1_50.json`
3. Execute benchmark: `scripts/run_case_suite.py`
4. Read outputs:
   - Scoreboard JSONL: `results/*.jsonl`
   - Per-case traces: `results/traces/<run-id>/*`

## Current Injection Design
- Injection cases keep user prompt clean.
- Attack payload is injected into environment data placeholders at runtime.
- Security is evaluated from pre/post environment state diffs, not just model text.
