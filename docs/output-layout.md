# Output layout

NIPTScale creates a generated project containing commands/logs/status and a data-result tree created by the site pipeline.

## Generated project

```text
PROJECT/
└── 00.shell/
    ├── 01.alignment.commands.sh
    ├── 02.test.commands.sh
    ├── 03.wgs.commands.sh
    ├── command_lists/
    ├── jobs/
    ├── logs/
    ├── runtime/
    └── status/
```

`command_lists` contains one command per Lane; `jobs` contains independent Lane/stage scripts; `logs` contains Lane logs; `runtime` contains packaged alignment helpers; and `status` contains `.done`/`.failed` markers.

## Lane result tree

```text
RESULT_ROOT/Disk_ID/Run_ID/L01/
├── manifest/
│   ├── fq_inventory.csv
│   ├── fastq_manifest.tsv
│   ├── sample_ids.txt
│   └── bam.list
├── samples/SAMPLE_ID/
│   ├── bam/SAMPLE_ID.bam
│   ├── bam/SAMPLE_ID.bam.bai
│   ├── logs/
│   └── status/
├── basevar_test/
│   ├── output/*.vcf.gz
│   ├── qc/
│   └── logs/
└── basevar_wgs/
    ├── regions/
    ├── qc/
    ├── logs/
    └── Run_ID_L01.basevar.vcf.gz
```

The final WGS result is normally:

```text
RESULT_ROOT/Disk_ID/Run_ID/Lane/basevar_wgs/Run_ID_Lane.basevar.vcf.gz
RESULT_ROOT/Disk_ID/Run_ID/Lane/basevar_wgs/Run_ID_Lane.basevar.vcf.gz.tbi
```

## Which sample list is authoritative?

Use `manifest/fastq_manifest.tsv` to determine which FASTQs were included and `manifest/bam.list` to determine which BAMs entered BaseVar2. Old sample directories can remain after an interrupted or previously misconfigured run; directory count alone is not an analysis manifest.

## Result interpretation

Verify that `bcftools query -l` matches the expected sample count, the VCF and index are readable, reference/contig naming matches downstream resources, and sample IDs are unique across Lanes. The Lane-level VCF is not automatically imputed, harmonized across Lanes, or ready for phenotype association analysis.
