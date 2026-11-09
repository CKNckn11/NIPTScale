from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FastqRecord:
    disk_id: str
    run_id: str
    lane_id: str
    lane_path: Path
    sample_id: str
    fastq_path: Path
    size_bytes: int
    status: str
    exclude_reason: str = ""


@dataclass(frozen=True)
class LaneRecord:
    disk_id: str
    run_id: str
    lane_id: str
    lane_path: Path
    total_fastq: int
    included_fastq: int
    excluded_fastq: int

    @property
    def key(self) -> str:
        return f"{self.disk_id}__{self.run_id}__{self.lane_id}"
