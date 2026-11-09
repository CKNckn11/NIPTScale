# Changelog

All notable changes to NIPTScale are documented here.

## [0.2.0] - 2026-11-09

### Added

- New `niptscale` command and package name.
- Automatic discovery of Disk/Run/Lane/FASTQ hierarchies.
- FASTQ inventory with inclusion/exclusion reasons.
- Configurable minimum FASTQ size and `undecoded` exclusion.
- Two-level concurrency across Lanes and samples.
- Independent alignment, regional test, and WGS stages.
- Per-sample and per-Lane status markers.
- BaseVar2 regional command generation and final Lane VCF orchestration.
- `niptflow` compatibility command and import shim.

### Known limitations

- Requires a site-specific external shell adapter in `pipeline_dir`.
- Supports the current single-end short-read workflow only.
- Does not include cross-Lane merging, imputation, GWAS, or fetal genotype inference.

[0.2.0]: https://github.com/CKNckn11/NIPTScale/releases/tag/v0.2.0
