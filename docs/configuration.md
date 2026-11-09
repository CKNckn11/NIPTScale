# Configuration reference

NIPTScale reads a two-level YAML file with `paths`, `rules`, and `parallel` sections.

## `paths`

| Key | Required | Meaning |
|---|---:|---|
| `scan_root` | yes | Root searched recursively for Lane directories |
| `result_root` | yes | Root used by the site pipeline for analysis results |
| `pipeline_dir` | yes | Directory containing the site-specific shell adapter |

The `pipeline_dir` must contain:

```text
00_config.sh
03_make_bam_list.sh
04_basevar_test_only.sh
05_wgs_generate_commands.sh
06_wgs_run_regions.sh
07_wgs_concat.sh
```

`00_config.sh` is site-specific and must define the installed BaseVar2 binary, GRCh38 FASTA/BWA prefix, software environment, result root, BaseVar2 batch/thread settings, and region size used by the remaining scripts.

## `rules`

| Key | Default | Meaning |
|---|---:|---|
| `min_fastq_bytes` | `100000000` | Exclude smaller FASTQs while retaining them in the inventory |
| `lane_pattern` | `^L\d{2}$` | Regular expression used to recognize Lane directories |

Files whose sample name contains `undecoded` are also excluded. Check each Lane's `manifest/fastq_manifest.tsv` before compute-intensive execution.

## `parallel`

| Key | Default | Meaning |
|---|---:|---|
| `alignment_lane_jobs` | `4` | Concurrent Lane alignment jobs |
| `samples_per_lane` | `2` | Concurrent samples inside each Lane |
| `alignment_threads_per_sample` | `4` | BWA threads per active sample |
| `samtools_threads_per_sample` | `2` | SAMtools threads per active sample |
| `sort_memory_per_thread` | `1G` | SAMtools sort memory per thread |
| `test_lane_jobs` | `2` | Concurrent Lane test jobs |
| `wgs_lane_jobs` | `1` | Concurrent Lane whole-genome jobs |

Increasing concurrency can saturate shared storage before CPU or memory is exhausted. Start conservatively and observe I/O wait and throughput.

## Generic example

```yaml
paths:
  scan_root: /data/NIPT
  result_root: /results/BaseVar2
  pipeline_dir: /opt/niptscale-pipeline

rules:
  min_fastq_bytes: 100000000
  lane_pattern: '^L\d{2}$'

parallel:
  alignment_lane_jobs: 4
  samples_per_lane: 8
  alignment_threads_per_sample: 3
  samtools_threads_per_sample: 2
  sort_memory_per_thread: 1G
  test_lane_jobs: 4
  wgs_lane_jobs: 4
```

PyYAML is optional. Without PyYAML, do not use anchors, lists, deeper nested objects, or other advanced YAML features.
