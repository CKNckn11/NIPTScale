#!/usr/bin/env bash
# Build one Lane manifest. The YAML threshold passed by NIPTScale overrides the
# legacy hard-coded MIN_FASTQ_BYTES value in 00_config.sh.

set -Eeuo pipefail
LANE_PATH=${1:?Lane path is required}
PIPELINE_DIR=${2:?Pipeline directory is required}
NIPTFLOW_MIN_FASTQ_BYTES=${3:?Minimum FASTQ bytes is required}
export LANE_PATH
source "${PIPELINE_DIR}/00_config.sh"
MIN_FASTQ_BYTES=${NIPTFLOW_MIN_FASTQ_BYTES}

for cmd in bwa samtools bcftools gzip xargs; do
    command -v "${cmd}" >/dev/null 2>&1 || {
        echo "ERROR: missing program: ${cmd}" >&2
        exit 1
    }
done
[[ -x "${BASEVAR}" ]] || { echo "ERROR: BaseVar2 missing: ${BASEVAR}" >&2; exit 1; }
[[ -s "${REF}" && -s "${REF}.fai" ]] || { echo "ERROR: reference/FAI missing." >&2; exit 1; }

FASTQ_MANIFEST="${MANIFEST_DIR}/fastq_manifest.tsv"
SAMPLE_IDS="${MANIFEST_DIR}/sample_ids.txt"
INVENTORY_TMP="${MANIFEST_DIR}/fq_inventory.rows.tsv"
INVENTORY_CSV="${MANIFEST_DIR}/fq_inventory.csv"
: > "${FASTQ_MANIFEST}"
: > "${SAMPLE_IDS}"
: > "${INVENTORY_TMP}"

TOTAL_FQ=0
INCLUDED=0
EXCLUDED=0
while IFS= read -r -d '' fq; do
    TOTAL_FQ=$((TOTAL_FQ + 1))
    sample=$(basename "${fq}" .fq.gz)
    size=$(stat -c '%s' "${fq}")
    status=included
    reason=""
    gzip_status=not_checked

    if [[ "${sample,,}" == *undecoded* ]]; then
        status=excluded
        reason=undecoded
    elif ((size < MIN_FASTQ_BYTES)); then
        status=excluded
        reason=below_min_fastq_bytes
    fi
    if ((CHECK_GZIP == 1)); then
        if gzip -t "${fq}"; then
            gzip_status=pass
        else
            gzip_status=fail
            status=excluded
            reason=gzip_integrity_failed
        fi
    fi

    if [[ "${status}" == included ]]; then
        INCLUDED=$((INCLUDED + 1))
        printf '%s\n' "${sample}" >> "${SAMPLE_IDS}"
        printf '%s\t%s\n' "${sample}" "${fq}" >> "${FASTQ_MANIFEST}"
        mkdir -p "${SAMPLES_ROOT}/${sample}"/{bam,qc,logs,tmp,status}
    else
        EXCLUDED=$((EXCLUDED + 1))
    fi
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
        "${sample}" "${fq}" "${size}" "${status}" "${reason}" "${gzip_status}" \
        >> "${INVENTORY_TMP}"
done < <(find "${RAW_LANE_DIR}" -maxdepth 1 -type f -name '*.fq.gz' -print0 | sort -zV)

((TOTAL_FQ > 0)) || { echo "ERROR: no fq.gz files found in ${RAW_LANE_DIR}." >&2; exit 1; }
((INCLUDED > 0)) || { echo "ERROR: no FASTQ passed inclusion rules." >&2; exit 1; }

{
    echo 'disk_id,run_id,lane_id,lane_path,total_fq_files,included_sample_count,excluded_fq_count,sample_id,fq_path,size_bytes,status,exclude_reason,gzip_status'
    awk -F '\t' \
        -v disk="${DISK_ID}" -v run="${RUN_ID}" -v lane="${LANE_ID}" \
        -v lane_path="${RAW_LANE_DIR}" -v total="${TOTAL_FQ}" \
        -v included="${INCLUDED}" -v excluded="${EXCLUDED}" '
        function q(s) {gsub(/"/, "\"\"", s); return "\"" s "\""}
        {
            print q(disk) "," q(run) "," q(lane) "," q(lane_path) "," \
                  total "," included "," excluded "," q($1) "," q($2) "," \
                  $3 "," q($4) "," q($5) "," q($6)
        }
    ' "${INVENTORY_TMP}"
} > "${INVENTORY_CSV}"
rm -f -- "${INVENTORY_TMP}"

echo "PASS inventory"
echo "Disk: ${DISK_ID}"
echo "Run: ${RUN_ID}"
echo "Lane: ${LANE_ID}"
echo "Total fq.gz: ${TOTAL_FQ}"
echo "Included samples: ${INCLUDED}"
echo "Excluded fq.gz: ${EXCLUDED}"
echo "Parallel samples per Lane: configured by NIPTScale"
echo "CSV: ${INVENTORY_CSV}"
echo "Analysis manifest: ${FASTQ_MANIFEST}"
