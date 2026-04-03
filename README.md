# Bringing the Dual-LLM Pattern to Practice in Google ADK for Deterministic AI Agent Security against Prompt Injection

<p align="center">
  <img src="https://img.shields.io/badge/Conference-AROB%202026-blue?style=for-the-badge&logo=google-scholar&logoColor=white" alt="AROB 2026">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12">
  <img src="https://img.shields.io/badge/Docker-Supported-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/Framework-Google%20ADK-34A853?style=for-the-badge&logo=google&logoColor=white" alt="Google ADK">
</p>

- **Authors:** Huang Shuo and [Shin-Jie Lee](https://sites.google.com/view/shinjielee/)
- **Affiliation:** Department of Computer Science and Information Engineering, National Cheng Kung University, Tainan, Taiwan

> This paper has been presented at the [31st International Symposium on Artificial Life and Robotics (ISAROB 2026)](https://isarob.org/symposium/).

## Experimental Scope (Important)

This repository is an **experimental reproduction lab**.

- It is for **reproducing the benchmark results** in this project.
- It is **not** a production-ready agent platform.
- It focuses on a fixed attacked case pack and controlled comparisons between configurations.

## What This Lab Reproduces

This lab runs the same fixed benchmark pack under three configurations:

1. `baseline` (single LLM)
2. `dual_no_policy` (Dual-LLM isolation only)
3. `dual` (Dual-LLM isolation + policy callback)

Primary metrics:

- `utility_pass`: whether the user task was completed
- `security_breach`: whether the injection succeeded
- `runtime_ok`: whether execution finished without runtime failure

## Core Design

1. **Privileged LLM (P-LLM):** planning + tool use.
2. **Quarantined LLM (Q-LLM):** extraction/summarization over untrusted content.
3. **Key Isolation Plugin:** replaces raw values with symbolic `key:<uuid>` handles.
4. **Security Policy Callback:** deterministic checks before sensitive tool execution.

Core implementation files:

- `src/adk_dual_llm/core/privileged_agent.py`
- `src/adk_dual_llm/core/quarantined_agent.py`
- `src/adk_dual_llm/security/key_plugin.py`
- `scripts/run_case_suite.py`
- `benchmarks/per_case_judges_v1_50.py`

## Repository Entry Points

- `docs/LAB_OVERVIEW.md`: architecture, data flow, and evaluation pipeline
- `EXPERIMENT_WORKFLOW.md`: practical experiment workflow
- `TESTING_GUIDE.md`: troubleshooting and validation checklist
- `scripts/README.md`: script index and usage intent

## Setup

### Prerequisites

- Docker + Docker Compose
- Python 3.12 (for local helper scripts)
- API key in `.env` (`OPENAI_API_KEY` and/or `GOOGLE_API_KEY`)

### Configure Environment

```bash
cp .env.example .env
```

Example `.env`:

```env
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_google_api_key

PLLM_MODEL=openai/gpt-4.1
QLLM_MODEL=openai/gpt-4.1
QLLM_URL=http://qllm-server:8001
```

## Reproduce Results

### 1. Regenerate Fixed Case Pack (Optional but Recommended)

```bash
make cases-sync
make cases-pack
```

Main artifacts:

- `benchmarks/generated/case_pack_v1_50_attacked.json`
- `benchmarks/generated/mapping_v1_50_attacked.csv`

### 2. Quick Smoke Run (5 Cases)

```bash
make exp-v1 MODEL=openai/gpt-4.1 ENV=all LIMIT=5
```

### 3. Full Reproduction Run (50 Cases)

```bash
make exp-v1 MODEL=openai/gpt-4.1
```

This runs all three modes (`baseline`, `dual_no_policy`, `dual`) on the fixed attacked 50-pack.

### 4. Single-Mode Run (Example: Baseline only)

```bash
docker compose up -d qllm-server

docker compose run --rm -v $(pwd)/results:/app/results benchmark-runner \
  uv run --no-sync python scripts/run_case_suite.py \
  --mode baseline \
  --model openai/gpt-4.1 \
  --cases benchmarks/generated/case_pack_v1_50_attacked.json \
  --env all \
  --output results/baseline-only.jsonl \
  --trace-dir results/traces_baseline_only
```

## Outputs and Where to Read Them

Each experiment run is written under:

- `results/runs/<RUN_ID>/`

Key files:

- `baseline.jsonl`
- `dual_no_policy.jsonl`
- `dual.jsonl`
- `summary.json`
- `traces_baseline/`, `traces_dual_no_policy/`, `traces_dual/`

Generate summaries/tables:

```bash
make summary-latest
make table-latest ATTACK_SCOPE=attacked
```

## Retry Failed Cases Only (Save Tokens)

```bash
make retry-merge RUN_ID=<run-id> RETRY_CRITERIA=status_fail
```

This creates retry packs from failed rows, reruns only those cases, then merges back into a consolidated result.

## Notes for Stable Reproduction

- Keep the same model for all three modes when comparing.
- API quota/rate limits can cause temporary errors during long runs.
- Current ADK/A2A dependencies may print experimental/deprecation warnings; this is expected.

## Acknowledgements

- AgentDojo benchmark design: https://github.com/ethz-spylab/agentdojo
- CaMeL prompt-injection defense ideas: https://github.com/google-research/camel-prompt-injection
- Dual-LLM pattern framing: https://simonwillison.net/2023/Apr/25/dual-llm-pattern/
