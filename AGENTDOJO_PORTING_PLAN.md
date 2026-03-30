# AgentDojo Porting Plan (Fast Rebuild Track)

This document defines a practical path to port more AgentDojo cases into this ADK Dual-LLM project while improving experimental rigor.

## What was done now

- Cloned AgentDojo into `external/agentdojo` for direct reference.
- Added a seed case registry: `benchmarks/case_registry.json`.
- Added a batch runner: `scripts/run_case_suite.py`.
- Strengthened security policies in:
  - `benchmarks/slack/policy.py`
  - `benchmarks/workspace/policy.py`
  - `benchmarks/travel/policy.py`
- Added deterministic reset helper in banking:
  - `benchmarks/banking/tools.py::reset_banking_env`

## Upstream references to follow

- Main benchmark script:
  - `external/agentdojo/src/agentdojo/scripts/benchmark.py`
- Benchmark core:
  - `external/agentdojo/src/agentdojo/benchmark.py`
- v1.2 suite deltas (good source for high-value tasks):
  - `external/agentdojo/src/agentdojo/default_suites/v1_2/banking/injection_tasks.py`
  - `external/agentdojo/src/agentdojo/default_suites/v1_2/slack/user_tasks.py`
  - `external/agentdojo/src/agentdojo/default_suites/v1_2/travel/user_tasks.py`
  - `external/agentdojo/src/agentdojo/default_suites/v1_2/travel/injection_tasks.py`
  - `external/agentdojo/src/agentdojo/default_suites/v1_2/workspace/user_tasks.py`
  - `external/agentdojo/src/agentdojo/default_suites/v1_2/workspace/injection_tasks.py`

## Fast rebuild strategy

1. Build case parity first, then score parity.
2. Keep environment mocks simple; prioritize attack semantics and policy outcomes.
3. Version case packs (`seed`, `standard`, `hard`) so paper numbers are reproducible.

## Phase plan

### Phase 1 (Immediate): Expand to 40-60 cases

- Add more prompts and expected outcomes into `benchmarks/case_registry.json`.
- Start from high-signal task IDs in AgentDojo v1.2:
  - Banking `InjectionTask0/1/2/3/4/5/6/8`
  - Workspace `InjectionTask3/6/7/8/9/10/11/12/13`
  - Travel `InjectionTask2`
  - Slack high-risk user tasks from v1.2
- Keep one-file-per-environment mapping notes.

### Phase 2: Formal scoring and comparability

- Extend `run_case_suite.py` with machine-checkable verdicts:
  - `utility_pass`
  - `security_breach`
  - `policy_blocked`
  - `runtime_error`
- Add environment-state assertions (e.g., no attacker transfer, no unsafe outbound email).
- Save outputs to JSONL + summary JSON + markdown table.

### Phase 3: Reproducible experiment pipeline

- Add commands for:
  - baseline mode (without defense callback)
  - defended mode (Dual-LLM + policy)
- Produce side-by-side metrics:
  - attack success rate
  - defense success rate
  - utility retention
  - false positive block rate

## How to run current seed suite

Run all:

```bash
uv run python scripts/run_case_suite.py --env all --output results/case-suite-results.jsonl
```

Run only banking (first 3 cases):

```bash
uv run python scripts/run_case_suite.py --env banking --limit 3 --output results/banking-seed.jsonl
```

## Next coding priorities

1. Add `expected_outcome` and assertion fields to each case.
2. Implement baseline-vs-defended dual execution in the runner.
3. Add per-environment state check hooks for stronger security verdicts.
