#!/usr/bin/env bash
# Site adapter template. Copy this directory outside the repository, edit the
# paths below, and point pipeline_dir in the YAML configuration to that copy.

set -Eeuo pipefail

# Input must end at one L0X directory.
: "${LANE_PATH:?LANE_PATH is required and must point to one L0X directory}"

RAW_LANE_DIR=$(readlink -f -- "${LANE_PATH}")
[[ -d "${RAW_LANE_DIR}" ]] || { echo "ERROR: lane path missing: ${RAW_LANE_DIR}" >&2; exit 1; }

LANE_ID=$(basename "${RAW_LANE_DIR}")
RUN_DIR=$(dirname "${RAW_LANE_DIR}")
RUN_ID=$(basename "${RUN_DIR}")
DISK_DIR=$(dirname "${RUN_DIR}")
DISK_ID=$(basename "${DISK_DIR}")

[[ "${LANE_ID}" =~ ^L[0-9]{2}$ ]] || {
    echo "ERROR: input must end at a lane directory such as L01/L02: ${RAW_LANE_DIR}" >&2
    exit 1
}

# Override these defaults with environment variables or edit this file.
RESULT_ROOT="${NIPTSCALE_RESULT_ROOT:-/results/BaseVar2}"
LANE_ROOT="${RESULT_ROOT}/${DISK_ID}/${RUN_ID}/${LANE_ID}"
SAMPLES_ROOT="${LANE_ROOT}/samples"
MANIFEST_DIR="${LANE_ROOT}/manifest"

# Test and WGS outputs are isolated.
TEST_ROOT="${LANE_ROOT}/basevar_test"
WGS_ROOT="${LANE_ROOT}/basevar_wgs"

# Software and reference paths.
BASEVAR="${BASEVAR:-/opt/basevar/bin/basevar}"
REF="${NIPTSCALE_REF:-/reference/GRCh38.fa}"
BWA_REF="${NIPTSCALE_BWA_REF:-${REF}}"

# ---------------------------- 运行参数 ----------------------------
# FASTQs below 100 MB remain in the inventory but are not analyzed.
MIN_FASTQ_BYTES=100000000

# 0: do not gzip-test every FASTQ during inventory; 1: run gzip -t.
CHECK_GZIP=0

ALIGN_THREADS=16
SAMTOOLS_THREADS=8
BASEVAR_THREADS=4
BASEVAR_BATCH_SIZE=500
REGION_SIZE=2000000

# BaseVar2 regional jobs. Increase only after checking I/O capacity.
REGION_JOBS=1

# 0: reuse an existing valid BAM; 1: force realignment.
FORCE_REALIGN=0

# 0: remove intermediate SAI/sorted BAM; 1: retain them.
KEEP_INTERMEDIATE=0

# Directories and optional Conda activation.
mkdir -p \
    "${SAMPLES_ROOT}" \
    "${MANIFEST_DIR}" \
    "${TEST_ROOT}"/{output,qc,logs,tmp} \
    "${WGS_ROOT}"/{regions,qc,logs,tmp}

if [[ -n "${NIPTSCALE_CONDA_SH:-}" ]]; then
    source "${NIPTSCALE_CONDA_SH}"
    conda activate "${NIPTSCALE_CONDA_ENV:-biosoft}"
fi

for cmd in bwa samtools bcftools gzip; do
    command -v "${cmd}" >/dev/null 2>&1 || {
        echo "ERROR: missing program in PATH: ${cmd}" >&2
        exit 1
    }
done
[[ -x "${BASEVAR}" ]] || { echo "ERROR: BaseVar2 is not executable: ${BASEVAR}" >&2; exit 1; }
[[ -s "${REF}" && -s "${REF}.fai" ]] || { echo "ERROR: missing reference or FAI: ${REF}" >&2; exit 1; }
