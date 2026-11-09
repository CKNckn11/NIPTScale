from __future__ import annotations

import shlex
import shutil
import stat
import sys
from pathlib import Path

from .config import Settings


def _q(value: Path | str) -> str:
    return shlex.quote(str(value))


def _write_executable(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)


def lane_output(settings: Settings, lane: Path) -> Path:
    lane = lane.resolve()
    return settings.result_root / lane.parent.parent.name / lane.parent.name / lane.name


def _job_script(name: str, commands: list[str], status_dir: Path) -> str:
    done = status_dir / f"{name}.done"
    failed = status_dir / f"{name}.failed"
    body = "\n".join(commands)
    return f'''#!/usr/bin/env bash
set -Eeuo pipefail
mkdir -p {_q(status_dir)}
rm -f -- {_q(done)} {_q(failed)}
trap 'rc=$?; printf "%s\\t%s\\n" "$(date -Iseconds)" "$rc" > {_q(failed)}; exit "$rc"' ERR
{body}
printf "%s\\tdone\\n" "$(date -Iseconds)" > {_q(done)}
'''


def generate_project(
    settings: Settings,
    lane_paths: list[Path],
    project_dir: str | Path,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Generate independent Lane job scripts and stage command files."""
    settings.validate(require_pipeline=True)
    project = Path(project_dir).expanduser().resolve()
    if project.exists() and any(project.iterdir()) and not overwrite:
        raise FileExistsError(f"Project directory is not empty: {project}; use --force")
    shell_dir = project / "00.shell"
    jobs_dir = shell_dir / "jobs"
    status_dir = shell_dir / "status"
    log_dir = shell_dir / "logs"
    runtime_dir = shell_dir / "runtime"
    command_list_dir = shell_dir / "command_lists"
    for directory in (jobs_dir, status_dir, log_dir, runtime_dir, command_list_dir):
        directory.mkdir(parents=True, exist_ok=True)

    resource_dir = Path(__file__).resolve().parent / "scripts"
    for name in ("prepare_lane.sh", "align_lane_parallel.sh", "align_one_sample.sh"):
        source = resource_dir / name
        if not source.is_file():
            raise FileNotFoundError(f"NIPTScale runtime script is missing: {source}")
        target = runtime_dir / name
        shutil.copy2(source, target)
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)

    stage_commands: dict[str, list[str]] = {
        "01.alignment": [], "02.test": [], "03.wgs": []
    }

    for lane in lane_paths:
        lane = lane.expanduser().resolve()
        if not lane.is_dir():
            raise FileNotFoundError(f"Lane directory does not exist: {lane}")
        if not list(lane.glob("*.fq.gz")):
            raise ValueError(f"Lane contains no direct child fq.gz files: {lane}")

        key = f"{lane.parent.parent.name}__{lane.parent.name}__{lane.name}"
        lane_out = lane_output(settings, lane)
        lane_status = status_dir / key
        lane_logs = log_dir / key
        lane_logs.mkdir(parents=True, exist_ok=True)

        alignment = jobs_dir / f"{key}.alignment.sh"
        test = jobs_dir / f"{key}.test.sh"
        wgs = jobs_dir / f"{key}.wgs.sh"

        _write_executable(alignment, _job_script("alignment", [
            f"mkdir -p {_q(lane_out)}",
            f"bash {_q(runtime_dir / 'prepare_lane.sh')} {_q(lane)} {_q(settings.pipeline_dir)} {settings.min_fastq_bytes}",
            f"bash {_q(runtime_dir / 'align_lane_parallel.sh')} {_q(lane)} "
            f"{_q(settings.pipeline_dir)} {settings.samples_per_lane} "
            f"{settings.alignment_threads_per_sample} "
            f"{settings.samtools_threads_per_sample} "
            f"{_q(settings.sort_memory_per_thread)}",
            f"bash {_q(settings.pipeline_dir / '03_make_bam_list.sh')} {_q(lane)}",
        ], lane_status))
        _write_executable(test, _job_script("test", [
            f"bash {_q(settings.pipeline_dir / '04_basevar_test_only.sh')} {_q(lane)}",
        ], lane_status))
        _write_executable(wgs, _job_script("wgs", [
            f"bash {_q(settings.pipeline_dir / '05_wgs_generate_commands.sh')} {_q(lane)}",
            f"bash {_q(settings.pipeline_dir / '06_wgs_run_regions.sh')} {_q(lane)}",
            f"bash {_q(settings.pipeline_dir / '07_wgs_concat.sh')} {_q(lane)}",
        ], lane_status))

        stage_commands["01.alignment"].append(
            f"bash {_q(alignment)} > {_q(lane_logs / 'alignment.log')} 2>&1"
        )
        stage_commands["02.test"].append(
            f"bash {_q(test)} > {_q(lane_logs / 'test.log')} 2>&1"
        )
        stage_commands["03.wgs"].append(
            f"bash {_q(wgs)} > {_q(lane_logs / 'wgs.log')} 2>&1"
        )

    stage_parallel = {
        "01.alignment": settings.alignment_lane_jobs,
        "02.test": settings.test_lane_jobs,
        "03.wgs": settings.wgs_lane_jobs,
    }
    outputs: dict[str, Path] = {}
    for stage, commands in stage_commands.items():
        command_list = command_list_dir / f"{stage}.txt"
        command_list.write_text("\n".join(commands) + "\n", encoding="utf-8", newline="\n")
        path = shell_dir / f"{stage}.commands.sh"
        runner = (
            f"{_q(sys.executable)} -m niptscale run-commands "
            f"-I {_q(command_list)} -j {stage_parallel[stage]}"
        )
        _write_executable(
            path,
            "#!/usr/bin/env bash\nset -Eeuo pipefail\n" + runner + "\n",
        )
        outputs[stage] = path
    return outputs
