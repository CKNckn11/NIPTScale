from __future__ import annotations

import math
import stat
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def split_jobs(
    command_file: str | Path,
    output_dir: str | Path,
    jobs: int,
    parallel: int = 1,
) -> list[Path]:
    """Split a generated command file into executable sub-jobs."""
    source = Path(command_file).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if jobs < 1 or parallel < 1:
        raise ValueError("jobs and parallel must be >= 1")
    commands = [
        line.strip() for line in source.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#") and not line.startswith("set ")
    ]
    if not commands:
        raise ValueError(f"No commands found in {source}")
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    chunk_size = math.ceil(len(commands) / min(jobs, len(commands)))
    generated: list[Path] = []
    for job_index, start in enumerate(range(0, len(commands), chunk_size), 1):
        subset = commands[start:start + chunk_size]
        target = out / f"job.{job_index:03d}.sh"
        lines = ["#!/usr/bin/env bash", "set -Eeuo pipefail"]
        for index, command in enumerate(subset, 1):
            lines.append(command + (" &" if parallel > 1 else ""))
            if parallel > 1 and index % parallel == 0:
                lines.append("wait")
        if parallel > 1 and len(subset) % parallel:
            lines.append("wait")
        target.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
        generated.append(target)
    return generated


def read_commands(command_file: str | Path) -> list[str]:
    source = Path(command_file).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    commands = [
        line.strip()
        for line in source.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
        and not line.lstrip().startswith("set ")
    ]
    if not commands:
        raise ValueError(f"No commands found in {source}")
    return commands


def _run_one(index: int, command: str) -> tuple[int, int]:
    print(f"START [{index}] {command}", flush=True)
    completed = subprocess.run(command, shell=True, executable="/bin/bash")
    print(f"END   [{index}] exit={completed.returncode}", flush=True)
    return index, completed.returncode


def run_commands(command_file: str | Path, parallel: int) -> None:
    """Run shell command lines concurrently and fail if any command fails."""
    if parallel < 1:
        raise ValueError("parallel must be >= 1")
    commands = read_commands(command_file)
    failures: list[tuple[int, int]] = []
    with ThreadPoolExecutor(max_workers=min(parallel, len(commands))) as executor:
        futures = {
            executor.submit(_run_one, index, command): index
            for index, command in enumerate(commands, 1)
        }
        for future in as_completed(futures):
            index, returncode = future.result()
            if returncode != 0:
                failures.append((index, returncode))
    if failures:
        detail = ", ".join(f"command {i}: exit {rc}" for i, rc in failures)
        raise RuntimeError(f"{len(failures)} command(s) failed: {detail}")
