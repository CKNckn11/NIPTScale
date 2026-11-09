from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if (value.startswith("'") and value.endswith("'")) or (
        value.startswith('"') and value.endswith('"')
    ):
        return value[1:-1]
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return int(value)
    except ValueError:
        return value


def _load_simple_yaml(path: Path) -> dict[str, Any]:
    """Load the small two-level YAML subset used by NIPTScale.

    This keeps node09 installation offline and dependency-free. If PyYAML is
    installed, it is used instead and full YAML syntax is available.
    """
    data: dict[str, Any] = {}
    section: dict[str, Any] | None = None
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not raw.startswith((" ", "\t")):
            if not line.endswith(":"):
                raise ValueError(f"Invalid YAML line {line_number}: {raw}")
            key = line[:-1].strip()
            section = {}
            data[key] = section
            continue
        if section is None or ":" not in line:
            raise ValueError(f"Invalid YAML line {line_number}: {raw}")
        key, value = line.strip().split(":", 1)
        section[key.strip()] = _scalar(value)
    return data


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError:
        return _load_simple_yaml(path)
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


@dataclass(frozen=True)
class Settings:
    scan_root: Path
    result_root: Path
    pipeline_dir: Path
    min_fastq_bytes: int = 100_000_000
    lane_pattern: str = r"^L\d{2}$"
    alignment_lane_jobs: int = 4
    samples_per_lane: int = 2
    alignment_threads_per_sample: int = 4
    samtools_threads_per_sample: int = 2
    sort_memory_per_thread: str = "1G"
    test_lane_jobs: int = 2
    wgs_lane_jobs: int = 1

    @classmethod
    def from_yaml(cls, filename: str | Path) -> "Settings":
        path = Path(filename).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Configuration file does not exist: {path}")
        data: dict[str, Any] = _load_yaml(path)
        paths = data.get("paths", {})
        rules = data.get("rules", {})
        parallel = data.get("parallel", {})
        required = ("scan_root", "result_root", "pipeline_dir")
        missing = [name for name in required if not paths.get(name)]
        if missing:
            raise ValueError(f"Missing config paths: {', '.join(missing)}")
        return cls(
            scan_root=Path(paths["scan_root"]).expanduser().resolve(),
            result_root=Path(paths["result_root"]).expanduser().resolve(),
            pipeline_dir=Path(paths["pipeline_dir"]).expanduser().resolve(),
            min_fastq_bytes=int(rules.get("min_fastq_bytes", 100_000_000)),
            lane_pattern=str(rules.get("lane_pattern", r"^L\d{2}$")),
            alignment_lane_jobs=int(parallel.get("alignment_lane_jobs", 4)),
            samples_per_lane=int(parallel.get("samples_per_lane", 2)),
            alignment_threads_per_sample=int(
                parallel.get("alignment_threads_per_sample", 4)
            ),
            samtools_threads_per_sample=int(
                parallel.get("samtools_threads_per_sample", 2)
            ),
            sort_memory_per_thread=str(
                parallel.get("sort_memory_per_thread", "1G")
            ),
            test_lane_jobs=int(parallel.get("test_lane_jobs", 2)),
            wgs_lane_jobs=int(parallel.get("wgs_lane_jobs", 1)),
        )

    def validate(self, require_pipeline: bool = False) -> None:
        if not self.scan_root.is_dir():
            raise FileNotFoundError(f"scan_root does not exist: {self.scan_root}")
        if self.min_fastq_bytes < 0:
            raise ValueError("min_fastq_bytes must be >= 0")
        parallel_values = {
            "alignment_lane_jobs": self.alignment_lane_jobs,
            "samples_per_lane": self.samples_per_lane,
            "alignment_threads_per_sample": self.alignment_threads_per_sample,
            "samtools_threads_per_sample": self.samtools_threads_per_sample,
            "test_lane_jobs": self.test_lane_jobs,
            "wgs_lane_jobs": self.wgs_lane_jobs,
        }
        invalid = [name for name, value in parallel_values.items() if value < 1]
        if invalid:
            raise ValueError(f"Parallel settings must be >= 1: {', '.join(invalid)}")
        if not self.sort_memory_per_thread.strip():
            raise ValueError("sort_memory_per_thread must not be empty")
        if require_pipeline:
            required = [
                "00_config.sh", "03_make_bam_list.sh", "04_basevar_test_only.sh",
                "05_wgs_generate_commands.sh",
                "06_wgs_run_regions.sh", "07_wgs_concat.sh",
            ]
            missing = [name for name in required if not (self.pipeline_dir / name).is_file()]
            if missing:
                raise FileNotFoundError(
                    f"pipeline_dir is missing scripts: {', '.join(missing)}"
                )
