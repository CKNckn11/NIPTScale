# Architecture

NIPTScale separates workflow generation from workflow execution. The Python package discovers data, validates configuration, and writes auditable job files. BWA, SAMtools, BCFtools, and BaseVar2 remain external command-line programs.

```text
configuration + Lane paths
            |
            v
       NIPTScale Python
            |
            +-- manifests
            +-- independent Lane jobs
            +-- stage command lists
            +-- logs and status markers
```

This model is intentionally similar to ilus: a generated job remains readable and executable even when NIPTScale is no longer running.

## Two-level concurrency

```text
alignment stage
├── Lane 1 ── sample 1 / sample 2 / ... (bounded)
├── Lane 2 ── sample 1 / sample 2 / ... (bounded)
└── Lane N ── sample 1 / sample 2 / ... (bounded)
```

- Lane concurrency is controlled by `alignment_lane_jobs` and `run-commands`.
- Sample concurrency within a Lane is controlled by `samples_per_lane` and `xargs -P`.
- BWA and SAMtools thread counts are configured per sample.
- Test and WGS Lane concurrency are controlled independently.

The theoretical number of simultaneous alignment samples is `alignment_lane_jobs × samples_per_lane`. Thread consumption changes between BWA and SAMtools phases, so this product is not itself the exact total CPU usage.

## Python modules

| Module | Responsibility |
|---|---|
| `config.py` | Parse and validate YAML settings |
| `scanner.py` | Discover Lane/FASTQ hierarchy and write manifests |
| `models.py` | Immutable Lane and FASTQ records |
| `generator.py` | Generate alignment, test, and WGS jobs |
| `jobs.py` | Execute or split command collections |
| `status.py` | Collect `.done` and `.failed` markers |
| `cli.py` | Command-line interface |

`src/niptflow` is a compatibility shim that imports the `niptscale` implementation.

## Stage boundaries

```text
scan
  -> nipt_lane_paths.txt
  -> nipt_fastq_manifest.tsv

generate
  -> 01.alignment.commands.sh
       -> Lane inventory
       -> SE BWA aln/samse
       -> sorted, duplicate-removed BAM/BAI
       -> bam.list

  -> 02.test.commands.sh
       -> optional regional BaseVar2 VCF

  -> 03.wgs.commands.sh
       -> BaseVar2 regional caller commands
       -> regional VCFs
       -> concatenated, indexed Lane VCF
```

The test and WGS stages are output-isolated. WGS does not consume the test VCF. Both consume the `bam.list` generated after alignment.

## Scaling model

The Lane is the outer scheduling unit and the FASTQ-derived sample is the inner alignment unit. Manifests are plain TSV/text files; the framework does not construct one in-memory object containing a 100,000-sample cohort. Generated command lists can be split and submitted in batches.

BaseVar2 calling is currently performed per Lane. Cross-Lane VCF integration is deliberately downstream because it requires cohort-wide decisions about sample identity, reference alleles, duplicate individuals, variant representation, QC, and imputation.

## Safety and reproducibility

- Scanning is read-only; FASTQs are not copied or modified.
- Only direct-child `*.fq.gz` files of matching Lane directories are inventoried.
- Excluded FASTQs remain visible with an explicit reason.
- Existing valid BAMs are checked before reuse.
- Alignment, test, and WGS use separate output areas.
- A non-empty project is not overwritten unless `--force` is supplied.
- Each Lane stage writes a terminal `.done` or `.failed` marker.
- Generated commands use absolute paths.

## Current portability boundary

Version 0.2.0 still requires a site-specific `pipeline_dir`. This adapter contains shell scripts and a local `00_config.sh` defining software, references, environment activation, and output locations. A future release should replace this adapter with fully package-managed templates and a scheduler backend.
