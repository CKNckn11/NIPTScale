#!/usr/bin/env bash
# WGS步骤3/3：按pipeline原始命令顺序收集VCF，再合并、索引和质控。
# 不使用find|sort重新猜测contig顺序，避免ALT/unplaced contig错序。

set -Eeuo pipefail
LANE_PATH="${1:-${LANE_PATH:-}}"
export LANE_PATH
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/00_config.sh"

COMMANDS="${WGS_ROOT}/wgs.commands.sh"
VCF_LIST="${WGS_ROOT}/vcf.list"
FINAL_VCF="${WGS_ROOT}/${RUN_ID}_${LANE_ID}.basevar.vcf.gz"
BAM_LIST="${MANIFEST_DIR}/bam.list"

[[ -s "${COMMANDS}" ]] || { echo "ERROR: WGS commands missing." >&2; exit 1; }

# 从生成的caller命令中提取-o后的VCF，保留BaseVar2 pipeline顺序。
awk '
    /basevar caller/ {
        for(i=1; i<=NF; i++) if($i=="-o") {print $(i+1); break}
    }
' "${COMMANDS}" > "${VCF_LIST}"

EXPECTED=$(grep -c 'basevar caller' "${COMMANDS}")
LISTED=$(wc -l < "${VCF_LIST}")
[[ "${LISTED}" -eq "${EXPECTED}" ]] || { echo "ERROR: VCF list count mismatch." >&2; exit 1; }

while read -r vcf; do
    [[ -s "${vcf}" ]] || { echo "ERROR: missing regional VCF: ${vcf}" >&2; exit 1; }
    gzip -t "${vcf}"
done < "${VCF_LIST}"

"${BASEVAR}" concat -n -L "${VCF_LIST}" -o "${FINAL_VCF}"
gzip -t "${FINAL_VCF}"
bcftools index --force --tbi "${FINAL_VCF}"
bcftools stats "${FINAL_VCF}" > "${WGS_ROOT}/qc/vcf.stats.txt"
bcftools query -l "${FINAL_VCF}" > "${WGS_ROOT}/qc/samples.txt"

EXPECTED_SAMPLES_IN_VCF=$(wc -l < "${BAM_LIST}")
FOUND_SAMPLES=$(bcftools query -l "${FINAL_VCF}" | wc -l)
[[ "${FOUND_SAMPLES}" -eq "${EXPECTED_SAMPLES_IN_VCF}" ]] || {
    echo "ERROR: final VCF sample count mismatch." >&2
    exit 1
}

echo "PASS WGS: ${FINAL_VCF}"
echo "Samples: ${FOUND_SAMPLES}"
echo "Variants: $(bcftools index -n "${FINAL_VCF}")"
