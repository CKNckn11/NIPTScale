#!/usr/bin/env bash
# Dispatch independent single-end FASTQ samples within one Lane concurrently.

set -Eeuo pipefail
LANE_PATH=${1:?Lane path is required}
PIPELINE_DIR=${2:?Pipeline directory is required}
SAMPLE_JOBS=${3:?Sample parallelism is required}
ALIGN_THREADS_OVERRIDE=${4:?Alignment threads per sample is required}
SAMTOOLS_THREADS_OVERRIDE=${5:?SAMtools threads per sample is required}
SORT_MEMORY_OVERRIDE=${6:?Sort memory per thread is required}
export LANE_PATH
source "${PIPELINE_DIR}/00_config.sh"
((SAMPLE_JOBS >= 1)) || { echo "ERROR: SAMPLE_JOBS must be >= 1" >&2; exit 1; }

MANIFEST="${MANIFEST_DIR}/fastq_manifest.tsv"
[[ -s "${MANIFEST}" ]] || { echo "ERROR: missing manifest: ${MANIFEST}" >&2; exit 1; }
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

echo "[$(date -Iseconds)] Lane ${LANE_ID}: start sample parallelism=${SAMPLE_JOBS}"
while IFS=$'\t' read -r sample fq; do
    printf '%s\0%s\0' "${sample}" "${fq}"
done < "${MANIFEST}" \
| xargs -0 -r -n 2 -P "${SAMPLE_JOBS}" \
    bash "${SCRIPT_DIR}/align_one_sample.sh" \
    "${LANE_PATH}" "${PIPELINE_DIR}" \
    "${ALIGN_THREADS_OVERRIDE}" "${SAMTOOLS_THREADS_OVERRIDE}" "${SORT_MEMORY_OVERRIDE}"
echo "[$(date -Iseconds)] Lane ${LANE_ID}: all samples completed"
