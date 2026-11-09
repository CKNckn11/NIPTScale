#!/usr/bin/env bash
# 检查每个样本的最终BAM，生成本lane的BaseVar2 bam.list。

set -Eeuo pipefail
LANE_PATH="${1:-${LANE_PATH:-}}"
export LANE_PATH
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/00_config.sh"

SAMPLE_IDS="${MANIFEST_DIR}/sample_ids.txt"
BAM_LIST="${MANIFEST_DIR}/bam.list"
SM_LIST="${MANIFEST_DIR}/bam_sample_names.txt"

[[ -s "${SAMPLE_IDS}" ]] || { echo "ERROR: sample_ids.txt missing." >&2; exit 1; }
: > "${BAM_LIST}"
: > "${SM_LIST}"

while read -r sample; do
    bam="${SAMPLES_ROOT}/${sample}/bam/${sample}.bam"
    [[ -s "${bam}" && -s "${bam}.bai" ]] || {
        echo "ERROR: BAM/BAI missing: ${bam}" >&2
        exit 1
    }
    samtools quickcheck -q "${bam}"
    printf '%s\n' "${bam}" >> "${BAM_LIST}"
    samtools samples "${bam}" >> "${SM_LIST}"
done < "${SAMPLE_IDS}"

EXPECTED=$(wc -l < "${SAMPLE_IDS}")
FOUND=$(wc -l < "${BAM_LIST}")
UNIQUE_SM=$(sort -u "${SM_LIST}" | wc -l)

[[ "${FOUND}" -eq "${EXPECTED}" && "${UNIQUE_SM}" -eq "${EXPECTED}" ]] || {
    echo "ERROR: BAM count or SM uniqueness check failed." >&2
    exit 1
}

echo "PASS: ${FOUND} BAMs"
echo "BAM list: ${BAM_LIST}"
