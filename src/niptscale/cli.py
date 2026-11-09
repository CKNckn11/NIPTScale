from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from . import __version__
from .config import Settings
from .generator import generate_project
from .jobs import run_commands, split_jobs
from .scanner import discover, read_lane_paths, write_manifests
from .status import collect_status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="niptscale",
        description="Generate BaseVar2 workflows for single-end low-pass WGS-NIPT.",
    )
    parser.add_argument("--version", action="version", version=f"niptscale {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    scan = commands.add_parser("scan", help="Discover NIPT Lane and FASTQ paths")
    scan.add_argument("-C", "--config", required=True)
    scan.add_argument("-O", "--outdir", required=True)

    generate = commands.add_parser("generate", help="Generate independent shell jobs")
    generate.add_argument("-C", "--config", required=True)
    group = generate.add_mutually_exclusive_group(required=True)
    group.add_argument("-I", "--lane-list")
    group.add_argument("-L", "--lane", action="append")
    generate.add_argument("-O", "--outdir", required=True)
    generate.add_argument("-f", "--force", action="store_true")

    split = commands.add_parser("split-jobs", help="Split a command file")
    split.add_argument("-I", "--input", required=True)
    split.add_argument("-O", "--outdir", required=True)
    split.add_argument("-n", "--jobs", type=int, required=True)
    split.add_argument("-t", "--parallel", type=int, default=1)

    run = commands.add_parser("run-commands", help="Run a command file concurrently")
    run.add_argument("-I", "--input", required=True)
    run.add_argument("-j", "--jobs", type=int, required=True)

    status = commands.add_parser("check-jobs", help="Check generated job markers")
    status.add_argument("-P", "--project", required=True)
    status.add_argument("-O", "--output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "scan":
            settings = Settings.from_yaml(args.config)
            lanes, fastqs = discover(settings)
            paths = write_manifests(args.outdir, lanes, fastqs)
            print(f"Lanes: {len(lanes)}")
            print(f"FASTQs: {len(fastqs)}")
            print(f"Included: {sum(x.status == 'included' for x in fastqs)}")
            for name, path in paths.items():
                print(f"{name}: {path}")
        elif args.command == "generate":
            settings = Settings.from_yaml(args.config)
            lanes = read_lane_paths(args.lane_list) if args.lane_list else [Path(x).resolve() for x in args.lane]
            outputs = generate_project(settings, lanes, args.outdir, overwrite=args.force)
            print(f"Generated project for {len(lanes)} Lane(s)")
            for stage, path in outputs.items():
                print(f"{stage}: {path}")
        elif args.command == "split-jobs":
            paths = split_jobs(args.input, args.outdir, args.jobs, args.parallel)
            print(f"Generated {len(paths)} sub-jobs")
            for path in paths:
                print(path)
        elif args.command == "run-commands":
            run_commands(args.input, args.jobs)
        elif args.command == "check-jobs":
            rows = collect_status(args.project)
            output = Path(args.output).resolve() if args.output else None
            if output:
                output.parent.mkdir(parents=True, exist_ok=True)
                with output.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(
                        handle,
                        fieldnames=["lane", "stage", "state", "job"],
                        delimiter="\t",
                        lineterminator="\n",
                    )
                    writer.writeheader()
                    writer.writerows(rows)
            for row in rows:
                print(f"{row['state']}\t{row['lane']}\t{row['stage']}\t{row['job']}")
            if output:
                print(f"Status table: {output}")
        return 0
    except (FileNotFoundError, FileExistsError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
