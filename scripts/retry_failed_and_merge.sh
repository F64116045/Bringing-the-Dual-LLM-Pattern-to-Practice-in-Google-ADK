#!/usr/bin/env bash
set -euo pipefail

RUN_ID=""
MODEL="openai/gpt-4.1"
CASES="benchmarks/generated/case_pack_v1_50_attacked.json"
ENV_NAME="all"
CRITERIA_CSV="status_fail"
FROM_MERGED=0
OUTPUT_TAG=""
SKIP_DUAL_NO_POLICY=0
SKIP_DUAL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-id)
      RUN_ID="$2"
      shift 2
      ;;
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
    --criteria)
      CRITERIA_CSV="$2"
      shift 2
      ;;
    --from-merged)
      FROM_MERGED=1
      shift
      ;;
    --output-tag)
      OUTPUT_TAG="$2"
      shift 2
      ;;
    --skip-dual-no-policy)
      SKIP_DUAL_NO_POLICY=1
      shift
      ;;
    --skip-dual)
      SKIP_DUAL=1
      shift
      ;;
    *)
      echo "Unknown argument: $1"
      exit 2
      ;;
  esac
done

if [[ -z "${RUN_ID}" ]]; then
  latest="$(ls -1dt results/runs/* 2>/dev/null | head -n 1 || true)"
  if [[ -z "${latest}" ]]; then
    echo "No run found under results/runs. Provide --run-id."
    exit 1
  fi
  RUN_ID="$(basename "${latest}")"
fi

RUN_ROOT="results/runs/${RUN_ID}"
BASELINE_JSONL="${RUN_ROOT}/baseline.jsonl"
if [[ "${FROM_MERGED}" -eq 1 ]]; then
  DUAL_NO_POLICY_JSONL="${RUN_ROOT}/dual_no_policy_merged.jsonl"
  DUAL_JSONL="${RUN_ROOT}/dual_merged.jsonl"
  if [[ ! -f "${DUAL_NO_POLICY_JSONL}" ]]; then
    DUAL_NO_POLICY_JSONL="${RUN_ROOT}/dual_no_policy.jsonl"
  fi
  if [[ ! -f "${DUAL_JSONL}" ]]; then
    DUAL_JSONL="${RUN_ROOT}/dual.jsonl"
  fi
else
  DUAL_NO_POLICY_JSONL="${RUN_ROOT}/dual_no_policy.jsonl"
  DUAL_JSONL="${RUN_ROOT}/dual.jsonl"
fi

if [[ ! -f "${BASELINE_JSONL}" ]]; then
  echo "Missing baseline JSONL: ${BASELINE_JSONL}"
  exit 1
fi

if [[ -z "${OUTPUT_TAG}" ]] && [[ "${FROM_MERGED}" -eq 1 ]]; then
  OUTPUT_TAG="_v2"
fi

RETRY_DIR="${RUN_ROOT}/retries"
mkdir -p "${RETRY_DIR}"

IFS=',' read -r -a CRITERIA_ARR <<< "${CRITERIA_CSV}"
if [[ "${#CRITERIA_ARR[@]}" -eq 0 ]]; then
  CRITERIA_ARR=("status_fail")
fi

count_cases_in_pack() {
  python3 -c 'import json,sys;obj=json.load(open(sys.argv[1], encoding="utf-8"));print(obj.get("counts",{}).get("selected_case_count", len(obj.get("cases",[]))))' "$1"
}

echo "[retry] run_id: ${RUN_ID}"
echo "[retry] model: ${MODEL}"
echo "[retry] env: ${ENV_NAME}"
echo "[retry] criteria: ${CRITERIA_CSV}"
echo "[retry] cases: ${CASES}"

need_qllm=0
if [[ "${SKIP_DUAL_NO_POLICY}" -eq 0 ]] && [[ -f "${DUAL_NO_POLICY_JSONL}" ]]; then
  need_qllm=1
fi
if [[ "${SKIP_DUAL}" -eq 0 ]] && [[ -f "${DUAL_JSONL}" ]]; then
  need_qllm=1
fi
if [[ "${need_qllm}" -eq 1 ]]; then
  docker compose up -d qllm-server
fi

DUAL_NO_POLICY_RETRY_JSONL=""
DUAL_RETRY_JSONL=""
DUAL_NO_POLICY_MERGED_JSONL="${RUN_ROOT}/dual_no_policy_merged${OUTPUT_TAG}.jsonl"
DUAL_MERGED_JSONL="${RUN_ROOT}/dual_merged${OUTPUT_TAG}.jsonl"

if [[ "${SKIP_DUAL_NO_POLICY}" -eq 0 ]]; then
  if [[ -f "${DUAL_NO_POLICY_JSONL}" ]]; then
    retry_pack="${RETRY_DIR}/retry_dual_no_policy.json"
    python3 scripts/build_retry_case_pack.py \
      --cases "${CASES}" \
      --results "${DUAL_NO_POLICY_JSONL}" \
      --output "${retry_pack}" \
      --criteria "${CRITERIA_ARR[@]}"
    retry_count="$(count_cases_in_pack "${retry_pack}")"
    if [[ "${retry_count}" -gt 0 ]]; then
      DUAL_NO_POLICY_RETRY_JSONL="${RETRY_DIR}/dual_no_policy_retry.jsonl"
      docker compose run --rm -v "$(pwd)/results:/app/results" benchmark-runner \
        uv run --no-sync python scripts/run_case_suite.py \
        --mode dual_no_policy \
        --model "${MODEL}" \
        --cases "${retry_pack}" \
        --env "${ENV_NAME}" \
        --output "${DUAL_NO_POLICY_RETRY_JSONL}" \
        --trace-dir "${RETRY_DIR}/traces_dual_no_policy_retry"
      python3 scripts/merge_retry_results.py \
        --base "${DUAL_NO_POLICY_JSONL}" \
        --retry "${DUAL_NO_POLICY_RETRY_JSONL}" \
        --output "${DUAL_NO_POLICY_MERGED_JSONL}"
    else
      cp "${DUAL_NO_POLICY_JSONL}" "${DUAL_NO_POLICY_MERGED_JSONL}"
      echo "[retry] dual_no_policy: no selected failures, copied original."
    fi
  else
    echo "[retry] dual_no_policy JSONL not found, skipping."
  fi
fi

if [[ "${SKIP_DUAL}" -eq 0 ]]; then
  if [[ -f "${DUAL_JSONL}" ]]; then
    retry_pack="${RETRY_DIR}/retry_dual.json"
    python3 scripts/build_retry_case_pack.py \
      --cases "${CASES}" \
      --results "${DUAL_JSONL}" \
      --output "${retry_pack}" \
      --criteria "${CRITERIA_ARR[@]}"
    retry_count="$(count_cases_in_pack "${retry_pack}")"
    if [[ "${retry_count}" -gt 0 ]]; then
      DUAL_RETRY_JSONL="${RETRY_DIR}/dual_retry.jsonl"
      docker compose run --rm -v "$(pwd)/results:/app/results" benchmark-runner \
        uv run --no-sync python scripts/run_case_suite.py \
        --mode dual \
        --model "${MODEL}" \
        --cases "${retry_pack}" \
        --env "${ENV_NAME}" \
        --output "${DUAL_RETRY_JSONL}" \
        --trace-dir "${RETRY_DIR}/traces_dual_retry"
      python3 scripts/merge_retry_results.py \
        --base "${DUAL_JSONL}" \
        --retry "${DUAL_RETRY_JSONL}" \
        --output "${DUAL_MERGED_JSONL}"
    else
      cp "${DUAL_JSONL}" "${DUAL_MERGED_JSONL}"
      echo "[retry] dual: no selected failures, copied original."
    fi
  else
    echo "[retry] dual JSONL not found, skipping."
  fi
fi

SUMMARY_MERGED_JSON="${RUN_ROOT}/summary_merged${OUTPUT_TAG}.json"
summary_cmd=(python3 scripts/summarize_case_results.py --baseline "${BASELINE_JSONL}" --output "${SUMMARY_MERGED_JSON}")
if [[ "${SKIP_DUAL_NO_POLICY}" -eq 0 ]] && [[ -f "${DUAL_NO_POLICY_MERGED_JSONL}" ]]; then
  summary_cmd+=(--dual-no-policy "${DUAL_NO_POLICY_MERGED_JSONL}")
fi
if [[ "${SKIP_DUAL}" -eq 0 ]] && [[ -f "${DUAL_MERGED_JSONL}" ]]; then
  summary_cmd+=(--dual "${DUAL_MERGED_JSONL}")
fi
"${summary_cmd[@]}"

echo "[done] merged summary: ${SUMMARY_MERGED_JSON}"
if [[ -n "${DUAL_NO_POLICY_RETRY_JSONL}" ]]; then
  echo "[done] dual_no_policy retry results: ${DUAL_NO_POLICY_RETRY_JSONL}"
fi
if [[ -n "${DUAL_RETRY_JSONL}" ]]; then
  echo "[done] dual retry results: ${DUAL_RETRY_JSONL}"
fi
