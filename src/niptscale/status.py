from __future__ import annotations

from pathlib import Path


def collect_status(project_dir: str | Path) -> list[dict[str, str]]:
    project = Path(project_dir).expanduser().resolve()
    status_root = project / "00.shell" / "status"
    jobs_root = project / "00.shell" / "jobs"
    if not jobs_root.is_dir():
        raise FileNotFoundError(f"Jobs directory not found: {jobs_root}")
    rows: list[dict[str, str]] = []
    for job in sorted(jobs_root.glob("*.sh")):
        stem = job.name[:-3]
        lane_key, stage = stem.rsplit(".", 1)
        stage_dir = status_root / lane_key
        done = stage_dir / f"{stage}.done"
        failed = stage_dir / f"{stage}.failed"
        if done.exists():
            state = "done"
        elif failed.exists():
            state = "failed"
        else:
            state = "pending_or_running"
        rows.append({"lane": lane_key, "stage": stage, "state": state, "job": str(job)})
    return rows
