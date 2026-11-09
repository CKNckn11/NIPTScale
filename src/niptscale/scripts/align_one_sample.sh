#!/usr/bin/env bash
# Align exactly one single-end FASTQ. Called by align_lane_parallel.sh.

set -Eeuo pipefail
LANE_PATH=${1:?Lane path is required}
PIPELINE_DIR=${2:?Pipeline directory is required}
ALIGN_THREADS_OVERRIDE=${3:?Alignment threads per sample is required}
SAMTOOLS_THREADS_OVERRIDE=${4:?SAMtools threads per sample is required}
SORT_MEMORY_OVERRIDE=${5:?Sort memory per thread is required}
sample=${6:?Sample ID is required}
fq=${7:?FASTQ path is required}
export LANE_PATH
source "${PIPELINE_DIR}/00_config.sh"
ALIGN_THREADS=${ALIGN_THREADS_OVERRIDE}
SAMTOOLS_THREADS=${SAMTOOLS_THREADS_OVERRIDE}
SORT_MEMORY=${SORT_MEMORY_OVERRIDE}

root="${SAMPLES_ROOT}/${sample}"
bam_dir="${root}/bam"
qc_dir="${root}/qc"
log_dir="${root}/logs"
tmp_dir="${root}/tmp"
sample_status="${root}/status"
mkdir -p "${bam_dir}" "${qc_dir}" "${log_dir}" "${tmp_dir}" "${sample_status}"

sai="${tmp_dir}/${sample}.sai"
sorted_bam="${tmp_dir}/${sample}.sorted.bam"
final_bam="${bam_dir}/${sample}.bam"
done_marker="${sample_status}/alignment.done"
failed_marker="${sample_status}/alignment.failed"
rm -f -- "${done_marker}" "${failed_marker}"
trap 'rc=$?; printf "%s\t%s\n" "$(date -Iseconds)" "$rc" > "'"${failed_marker}"'"; exit "$rc"' ERR

for suffix in amb ann bwt pac sa; do
    [[ -s "${BWA_REF}.${suffix}" ]] || {
        echo "ERROR: BWA index missing: ${BWA_REF}.${suffix}" >&2
        exit 1
    }
done

if [[ "${FORCE_REALIGN}" -eq 0 && -s "${final_bam}" && -s "${final_bam}.bai" ]] \
   && samtools quickcheck -q "${final_bam}"; then
    echo "SKIP valid BAM: ${sample}"
    printf '%s\tdone\n' "$(date -Iseconds)" > "${done_marker}"
    exit 0
fi

echo "[$(date -Iseconds)] BWA aln: ${sample}"
bwa aln -t "${ALIGN_THREADS}" "${BWA_REF}" "${fq}" \
    > "${sai}" 2> "${log_dir}/bwa_aln.log"

echo "[$(date -Iseconds)] BWA samse + sort: ${sample}"
bwa samse \
    -r "@RG\tID:${sample}\tSM:${sample}\tPL:BGISEQ\tLB:${RUN_ID}_${LANE_ID}" \
    "${BWA_REF}" "${sai}" "${fq}" \
    2> "${log_dir}/bwa_samse.log" \
| samtools sort -@ "${ALIGN_THREADS}" -m "${SORT_MEMORY}" -o "${sorted_bam}" -

echo "[$(date -Iseconds)] markdup: ${sample}"
samtools markdup -r -s -@ "${SAMTOOLS_THREADS}" \
    "${sorted_bam}" "${final_bam}" \
    2> "${log_dir}/markdup.log"

samtools index -@ "${SAMTOOLS_THREADS}" "${final_bam}"
samtools quickcheck -v "${final_bam}"
samtools flagstat -@ "${SAMTOOLS_THREADS}" "${final_bam}" > "${qc_dir}/flagstat.txt"
samtools stats -@ "${SAMTOOLS_THREADS}" "${final_bam}" > "${qc_dir}/stats.txt"
samtools coverage "${final_bam}" > "${qc_dir}/coverage.tsv"
samtools view -H "${final_bam}" | awk '$1=="@RG"' > "${qc_dir}/read_group.txt"

if [[ "${KEEP_INTERMEDIATE}" -eq 0 ]]; then
    rm -f -- "${sai}" "${sorted_bam}"
fi
printf '%s\tdone\n' "$(date -Iseconds)" > "${done_marker}"
echo "PASS BAM: ${final_bam}"
