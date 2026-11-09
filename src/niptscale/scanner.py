from __future__ import annotations

import csv
import os
import re
from pathlib import Path
from typing import Iterable

from .config import Settings
from .models import FastqRecord, LaneRecord


def _sample_id(path: Path) -> str:
    name = path.name
    return name[:-6] if name.endswith(".fq.gz") else path.stem


def discover(settings: Settings) -> tuple[list[LaneRecord], list[FastqRecord]]:
    """Discover non-empty Lane directories and direct child fq.gz files."""
    settings.validate()
    lane_re = re.compile(settings.lane_pattern)
    lanes: list[LaneRecord] = []
    fastqs: list[FastqRecord] = []

    for root, dirnames, filenames in os.walk(settings.scan_root):
        root_path = Path(root)
        if not lane_re.fullmatch(root_path.name):
            continue

        # Match the shell pipeline: only FASTQs directly inside the Lane directory.
        fq_paths = sorted(
            (root_path / name).resolve()
            for name in filenames
            if name.endswith(".fq.gz")
        )
        dirnames[:] = []
        if not fq_paths:
            continue

        run_id = root_path.parent.name
        disk_id = root_path.parent.parent.name
        included = 0
        excluded = 0
        for fq_path in fq_paths:
            sample_id = _sample_id(fq_path)
            size_bytes = fq_path.stat().st_size
            status = "included"
            reason = ""
            if "undecoded" in sample_id.lower():
                status, reason = "excluded", "undecoded"
            elif size_bytes < settings.min_fastq_bytes:
                status, reason = "excluded", "below_min_fastq_bytes"

            included += status == "included"
            excluded += status == "excluded"
            fastqs.append(FastqRecord(
                disk_id=disk_id, run_id=run_id, lane_id=root_path.name,
                lane_path=root_path.resolve(), sample_id=sample_id,
                fastq_path=fq_path, size_bytes=size_bytes,
                status=status, exclude_reason=reason,
            ))

        lanes.append(LaneRecord(
            disk_id=disk_id, run_id=run_id, lane_id=root_path.name,
            lane_path=root_path.resolve(), total_fastq=len(fq_paths),
            included_fastq=included, excluded_fastq=excluded,
        ))

    lanes.sort(key=lambda x: (x.disk_id, x.run_id, x.lane_id))
    fastqs.sort(key=lambda x: (x.disk_id, x.run_id, x.lane_id, x.sample_id))
    return lanes, fastqs


def write_manifests(
    output_dir: str | Path,
    lanes: Iterable[LaneRecord],
    fastqs: Iterable[FastqRecord],
) -> dict[str, Path]:
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    lane_list = list(lanes)
    fastq_list = list(fastqs)
    paths = {
        "lanes": out / "nipt_lane_paths.txt",
        "fastqs": out / "nipt_fastq_paths.txt",
        "lane_summary": out / "nipt_lane_summary.tsv",
        "fastq_manifest": out / "nipt_fastq_manifest.tsv",
    }

    paths["lanes"].write_text(
        "".join(f"{record.lane_path}\n" for record in lane_list), encoding="utf-8"
    )
    paths["fastqs"].write_text(
        "".join(f"{record.fastq_path}\n" for record in fastq_list), encoding="utf-8"
    )

    with paths["lane_summary"].open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow([
            "disk_id", "run_id", "lane_id", "lane_path",
            "total_fastq", "included_fastq", "excluded_fastq",
        ])
        for record in lane_list:
            writer.writerow([
                record.disk_id, record.run_id, record.lane_id, record.lane_path,
                record.total_fastq, record.included_fastq, record.excluded_fastq,
            ])

    with paths["fastq_manifest"].open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow([
            "disk_id", "run_id", "lane_id", "sample_id", "fq_path",
            "size_bytes", "status", "exclude_reason",
        ])
        for record in fastq_list:
            writer.writerow([
                record.disk_id, record.run_id, record.lane_id, record.sample_id,
                record.fastq_path, record.size_bytes, record.status,
                record.exclude_reason,
            ])
    return paths


def read_lane_paths(filename: str | Path) -> list[Path]:
    path = Path(filename).expanduser().resolve()
    lanes = [Path(line.strip()).resolve() for line in path.read_text().splitlines() if line.strip()]
    if not lanes:
        raise ValueError(f"No Lane paths found in {path}")
    return lanes
