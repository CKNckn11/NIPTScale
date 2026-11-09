# Site pipeline adapter

NIPTScale 0.2.0 uses this small shell adapter to connect generated jobs to local software, references, environments, and result paths.

1. Copy this directory to a deployment-controlled location.
2. Edit `00_config.sh`, or export the supported environment variables.
3. Set YAML `paths.pipeline_dir` to the copied directory.
4. Run `niptscale generate`; it validates that all required adapter scripts exist.

Supported environment overrides:

```text
NIPTSCALE_RESULT_ROOT
BASEVAR
NIPTSCALE_REF
NIPTSCALE_BWA_REF
NIPTSCALE_CONDA_SH
NIPTSCALE_CONDA_ENV
```

The adapter does not install BaseVar2, BWA, SAMtools, BCFtools, or reference files. It also does not contain BaseVar2 source code.

The files `03_make_bam_list.sh` through `07_wgs_concat.sh` define Lane-level handoff from aligned BAMs to a regional BaseVar2 test, whole-genome regional calling, and final VCF concatenation.
