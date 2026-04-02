#!/usr/bin/env bash
set -euo pipefail

MODEL="openai/gpt-4.1"
CASES="benchmarks/generated/case_pack_v1_50_attacked.json"
ENV_NAME="all"
LIMIT=""
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
SKIP_BASELINE=0
SKIP_DUAL_NO_POLICY=0
SKIP_DUAL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      MODEL="$2"
      shift 2
      ;;
    --cases)
      CASES="$2"
      shift 2
      ;;
    --env)
      ENV_NAME="$2"
      shift 2
      ;;
    --limit)
      LIMIT="$2"
      shift 2
      ;;
    --run-id)
      RUN_ID="$2"
      shift 2
      ;;
    --skip-baseline)
      SKIP_BASELINE=1
      shift
      ;;
    --skip-dual)
      SKIP_DUAL=1
      shift
      ;;
    --skip-dual-no-policy)
      SKIP_DUAL_NO_POLICY=1
      shift
      ;;
    *)
      echo "Unknown argument: $1"
      exit 2
      ;;
  esac
done

OUT_ROOT="results/runs/${RUN_ID}"
BASE_JSONL="${OUT_ROOT}/baseline.jsonl"
DUAL_JSONL="${OUT_ROOT}/dual.jsonl"
DUAL_NO_POLICY_JSONL="${OUT_ROOT}/dual_no_policy.jsonl"
BASE_TRACE="${OUT_ROOT}/traces_baseline"
DUAL_NO_POLICY_TRACE="${OUT_ROOT}/traces_dual_no_policy"
DUAL_TRACE="${OUT_ROOT}/traces_dual"
SUMMARY_JSON="${OUT_ROOT}/summary.json"

mkdir -p "${OUT_ROOT}"

echo "[run] output root: ${OUT_ROOT}"
echo "[run] model: ${MODEL}"
echo "[run] cases: ${CASES}"
echo "[run] env: ${ENV_NAME}"
echo "[run] limit: ${LIMIT:-<all>}"

docker compose up -d qllm-server

if [[ "${SKIP_BASELINE}" -eq 0 ]]; then
  echo "[run] baseline..."
  cmd=(
    docker compose run --rm -v "$(pwd)/results:/app/results" benchmark-runner
    uv run --no-sync python scripts/run_case_suite.py
    --mode baseline
    --model "${MODEL}"
    --cases "${CASES}"
    --env "${ENV_NAME}"
    --output "${BASE_JSONL}"
    --trace-dir "${BASE_TRACE}"
  )
  if [[ -n "${LIMIT}" ]]; then
    cmd+=(--limit "${LIMIT}")
  fi
  "${cmd[@]}"
fi

if [[ "${SKIP_DUAL}" -eq 0 ]]; then
  echo "[run] dual..."
  cmd=(
    docker compose run --rm -v "$(pwd)/results:/app/results" benchmark-runner
    uv run --no-sync python scripts/run_case_suite.py
    --mode dual
    --model "${MODEL}"
    --cases "${CASES}"
    --env "${ENV_NAME}"
    --output "${DUAL_JSONL}"
    --trace-dir "${DUAL_TRACE}"
  )
  if [[ -n "${LIMIT}" ]]; then
    cmd+=(--limit "${LIMIT}")
  fi
  "${cmd[@]}"
fi

if [[ "${SKIP_DUAL_NO_POLICY}" -eq 0 ]]; then
  echo "[run] dual_no_policy..."
  cmd=(
    docker compose run --rm -v "$(pwd)/results:/app/results" benchmark-runner
    uv run --no-sync python scripts/run_case_suite.py
    --mode dual_no_policy
    --model "${MODEL}"
    --cases "${CASES}"
    --env "${ENV_NAME}"
    --output "${DUAL_NO_POLICY_JSONL}"
    --trace-dir "${DUAL_NO_POLICY_TRACE}"
  )
  if [[ -n "${LIMIT}" ]]; then
    cmd+=(--limit "${LIMIT}")
  fi
  "${cmd[@]}"
fi

summary_cmd=(python3 scripts/summarize_case_results.py --output "${SUMMARY_JSON}")
if [[ "${SKIP_BASELINE}" -eq 0 ]]; then
  summary_cmd+=(--baseline "${BASE_JSONL}")
fi
if [[ "${SKIP_DUAL_NO_POLICY}" -eq 0 ]]; then
  summary_cmd+=(--dual-no-policy "${DUAL_NO_POLICY_JSONL}")
fi
if [[ "${SKIP_DUAL}" -eq 0 ]]; then
  summary_cmd+=(--dual "${DUAL_JSONL}")
fi
"${summary_cmd[@]}"

echo "[done] summary: ${SUMMARY_JSON}"
