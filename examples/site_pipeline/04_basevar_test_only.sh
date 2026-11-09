#!/usr/bin/env bash
# 独立测试脚本：仅在chr20:10-11 Mb运行。
# 它不写WGS目录，WGS也不依赖本脚本成功。

set -Eeuo pipefail
LANE_PATH="${1:-${LANE_PATH:-}}"
export LANE_PATH
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/00_config.sh"

BAM_LIST="${MANIFEST_DIR}/bam.list"
VCF="${TEST_ROOT}/output/${RUN_ID}_${LANE_ID}.chr20_10M_11M.vcf.gz"

[[ -s "${BAM_LIST}" ]] || { echo "ERROR: bam.list missing; run 03_make_bam_list.sh." >&2; exit 1; }

"${BASEVAR}" caller \
    -f "${REF}" \
    -L "${BAM_LIST}" \
    -r chr20:10000000-11000000 \
    -o "${VCF}" \
    -Q 20 -q 30 \
    -B "${BASEVAR_BATCH_SIZE}" \
    -t "${BASEVAR_THREADS}" \
    --filename-has-samplename \
    --smart-rerun \
    > "${TEST_ROOT}/logs/caller.stdout.log" \
    2> "${TEST_ROOT}/logs/caller.stderr.log"

gzip -t "${VCF}"
bcftools index --force --tbi "${VCF}"
bcftools stats "${VCF}" > "${TEST_ROOT}/qc/vcf.stats.txt"
bcftools query -l "${VCF}" > "${TEST_ROOT}/qc/samples.txt"

EXPECTED=$(wc -l < "${BAM_LIST}")
FOUND=$(bcftools query -l "${VCF}" | wc -l)
[[ "${FOUND}" -eq "${EXPECTED}" ]] || { echo "ERROR: VCF sample count mismatch." >&2; exit 1; }

echo "PASS TEST: ${VCF}"
echo "Samples: ${FOUND}"
echo "Variants: $(bcftools index -n "${VCF}")"
