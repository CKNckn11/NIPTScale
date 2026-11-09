#!/usr/bin/env bash
# WGS步骤1/3：只生成全基因组分区命令。
# 不检查、不依赖4_basevar_test_only.sh的任何输出。

set -Eeuo pipefail
LANE_PATH="${1:-${LANE_PATH:-}}"
export LANE_PATH
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/00_config.sh"

BAM_LIST="${MANIFEST_DIR}/bam.list"
COMMANDS="${WGS_ROOT}/wgs.commands.sh"

[[ -s "${BAM_LIST}" ]] || { echo "ERROR: bam.list missing; run 03_make_bam_list.sh." >&2; exit 1; }

"${BASEVAR}" pipeline \
    -o "${WGS_ROOT}/regions" \
    --ref_fai "${REF}.fai" \
    -f "${REF}" \
    -L "${BAM_LIST}" \
    -d "${REGION_SIZE}" \
    -Q 20 -q 30 \
    -B "${BASEVAR_BATCH_SIZE}" \
    -t "${BASEVAR_THREADS}" \
    --filename-has-samplename \
    --smart-rerun \
    > "${COMMANDS}"

TASKS=$(grep -c 'basevar caller' "${COMMANDS}" || true)
((TASKS > 0)) || { echo "ERROR: no caller commands generated." >&2; exit 1; }

echo "PASS: generated ${TASKS} WGS region commands"
echo "Commands: ${COMMANDS}"
