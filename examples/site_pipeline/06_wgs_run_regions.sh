#!/usr/bin/env bash
# WGS步骤2/3：执行已生成的分区caller任务。
# 只写basevar_wgs目录，不读写basevar_test目录。

set -Eeuo pipefail
LANE_PATH="${1:-${LANE_PATH:-}}"
export LANE_PATH
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/00_config.sh"

COMMANDS="${WGS_ROOT}/wgs.commands.sh"
[[ -s "${COMMANDS}" ]] || { echo "ERROR: run 05_wgs_generate_commands.sh first." >&2; exit 1; }

if ((REGION_JOBS == 1)); then
    bash "${COMMANDS}"
else
    command -v parallel >/dev/null 2>&1 || {
        echo "ERROR: GNU parallel is required when REGION_JOBS>1." >&2
        exit 1
    }
    parallel \
        --jobs "${REGION_JOBS}" \
        --halt soon,fail=1 \
        --joblog "${WGS_ROOT}/logs/parallel.joblog" \
        < "${COMMANDS}"
fi

TOTAL=$(grep -c 'basevar caller' "${COMMANDS}")
DONE=$(find "${WGS_ROOT}/regions" -maxdepth 1 -type f -name '*.vcf.gz' | wc -l)
[[ "${DONE}" -eq "${TOTAL}" ]] || {
    echo "ERROR: only ${DONE}/${TOTAL} regional VCFs exist." >&2
    exit 1
}

echo "PASS: all ${DONE} regional VCFs completed"
