# Contributing

Issues and pull requests are welcome. Before changing workflow behavior, open an issue describing the input layout, expected output, software versions, and whether the change affects single-end NIPT assumptions.

## Development setup

```bash
git clone https://github.com/CKNckn11/NIPTScale.git
cd NIPTScale
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Pull-request checklist

- Add or update unit tests for Python behavior.
- Keep generated shell commands readable and independently executable.
- Preserve explicit inclusion/exclusion reasons in manifests.
- Update the README or docs when configuration/output behavior changes.
- Do not commit patient/sample identifiers, genomic data, private mount paths, credentials, or logs containing sensitive metadata.
- State which BWA, SAMtools, BCFtools, BaseVar2, and reference versions were used for end-to-end testing.

## Scope

NIPTScale is a workflow generator. Algorithmic changes to BaseVar2 belong upstream in the [BaseVar2 repository](https://github.com/ShujiaHuang/BaseVar2). Clinical interpretation and risk reporting are outside this repository.
