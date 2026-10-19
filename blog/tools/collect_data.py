#!/usr/bin/env python3
"""Collect the benchmark datasets into blog/data/ for publishing.

The blog ships the raw campaign data with the entry so the site is
self-contained: build.py copies blog/data/ into dist/data/ verbatim and
renders the explorer page from it.

Sources (relative to the repo root):

    results_phone/  ->  blog/data/phone/       (Galaxy S24 FE)
    results/        ->  blog/data/emulator/    (pixel_bench AVD)

Files are renamed from com.cardscanner.<app>.<kind>.json to
<app>.<kind>.json (kind = stages | summary | events | rows).

Usage:

    python3 blog/tools/collect_data.py            # copy / resync
    python3 blog/tools/collect_data.py --check    # report without writing
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

BLOG_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BLOG_DIR.parent
DATA_DIR = BLOG_DIR / "data"

SOURCES = {
    "results_phone": "phone",
    "results": "emulator",
}
PREFIX = "com.cardscanner."


def collect(source_root: Path, data_dir: Path, check: bool) -> int:
    """Copy every recognised dataset file. Returns a process exit code."""
    copied = unchanged = missing = 0
    for source_name, env in sorted(SOURCES.items()):
        source_dir = source_root / source_name
        if not source_dir.is_dir():
            print(f"missing source directory: {source_dir}", file=sys.stderr)
            missing += 1
            continue
        out_dir = data_dir / env
        if not check:
            out_dir.mkdir(parents=True, exist_ok=True)
        for path in sorted(source_dir.glob(f"{PREFIX}*.json")):
            if not path.name.startswith(PREFIX):
                continue
            short = path.name[len(PREFIX):]
            target = out_dir / short
            if check:
                state = "would copy " if _differs(path, target) else "unchanged  "
                print(f"{state} {target.relative_to(data_dir)}")
                if _differs(path, target):
                    copied += 1
                else:
                    unchanged += 1
                continue
            if _differs(path, target):
                shutil.copy2(path, target)
                print(f"copied     {target.relative_to(data_dir)}")
                copied += 1
            else:
                print(f"unchanged  {target.relative_to(data_dir)}")
                unchanged += 1
    verb = "would copy" if check else "copied"
    print(f"\n{verb}: {copied}, unchanged: {unchanged}, missing sources: {missing}")
    return 1 if missing else 0


def _differs(source: Path, target: Path) -> bool:
    if not target.is_file():
        return True
    return source.read_bytes() != target.read_bytes()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--source-root",
        type=Path,
        default=REPO_ROOT,
        help="repository root holding results_phone/ and results/ (default: %(default)s)",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DATA_DIR,
        help="output directory (default: %(default)s)",
    )
    parser.add_argument("--check", action="store_true", help="report without writing")
    args = parser.parse_args(argv)
    return collect(args.source_root, args.data, args.check)


if __name__ == "__main__":
    sys.exit(main())
