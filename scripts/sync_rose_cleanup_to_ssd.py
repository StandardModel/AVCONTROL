#!/usr/bin/env python3
"""
Apply the verified RoseMusicWork cleanup to the mounted HiFi Rose SSD/share.

This deliberately does not mirror-delete the whole SSD. It only applies the
paths found by audit_rose_library.py:

- quarantine the same Unknown Album shards on the SSD
- copy repaired source files over their matching SSD paths, with backups
"""

from __future__ import annotations

import argparse
import csv
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


AUDIO_EXTENSIONS = {".aif", ".aiff", ".flac", ".m4a", ".mp3", ".wav", ".wave"}
SIDECARE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
DEFAULT_SOURCE_ROOT = Path("/Users/roncompton/Music/RoseMusicWork/Music")
DEFAULT_DEST_ROOT = Path("/Volumes/ROSEDISK")
DEFAULT_REPORT = Path("/Users/roncompton/AVCONTROL/reports/rose_library_album_shards.csv")


@dataclass
class Counts:
    shard_files_quarantined: int = 0
    sidecars_quarantined: int = 0
    repaired_files_copied: int = 0
    repaired_files_backed_up: int = 0
    missing_on_dest: int = 0
    missing_on_source: int = 0


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path

    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem} ({counter}){path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def relative_report_path(report_path: str, source_root: Path) -> Path:
    path = Path(report_path)
    return path.relative_to(source_root)


def folder_has_audio(folder: Path) -> bool:
    return any(path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS for path in folder.iterdir())


def move_to_quarantine(path: Path, dest_root: Path, quarantine: Path, *, apply: bool) -> bool:
    if not path.exists():
        return False
    target = unique_destination(quarantine / path.relative_to(dest_root))
    if apply:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(target))
    return True


def quarantine_orphan_sidecars(folder: Path, dest_root: Path, quarantine: Path, *, apply: bool) -> int:
    if not folder.exists() or folder_has_audio(folder):
        return 0

    moved = 0
    for path in folder.iterdir():
        if path.is_file() and path.suffix.lower() in SIDECARE_EXTENSIONS:
            if move_to_quarantine(path, dest_root, quarantine, apply=apply):
                moved += 1
    return moved


def remove_empty_dirs(folder: Path, stop_at: Path, *, apply: bool) -> None:
    current = folder
    while current != stop_at and current.exists():
        try:
            if any(current.iterdir()):
                return
        except FileNotFoundError:
            return
        if apply:
            current.rmdir()
        current = current.parent


def copy_repaired_file(source: Path, dest: Path, dest_root: Path, quarantine: Path, *, apply: bool) -> tuple[bool, bool]:
    if not source.exists():
        return False, False

    backed_up = False
    if apply:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            backup = unique_destination(quarantine / "_repaired_file_backups" / dest.relative_to(dest_root))
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, backup)
            backed_up = True
        shutil.copy2(source, dest)
    else:
        backed_up = dest.exists()
    return True, backed_up


def load_rows(report: Path) -> list[dict[str, str]]:
    with report.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--dest-root", type=Path, default=DEFAULT_DEST_ROOT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    quarantine = args.dest_root / "_quarantine" / f"rose-cleanup-sync-{stamp}"
    counts = Counts()

    rows = load_rows(args.report)
    shard_relpaths = {
        relative_report_path(row["path"], args.source_root)
        for row in rows
        if row["problem"] == "unknown_album_shard"
    }
    repaired_relpaths = {
        relative_report_path(row["path"], args.source_root)
        for row in rows
        if row["problem"] == "malformed_album_track"
    }

    for relpath in sorted(shard_relpaths):
        dest = args.dest_root / relpath
        if not dest.exists():
            counts.missing_on_dest += 1
            continue
        folder = dest.parent
        if move_to_quarantine(dest, args.dest_root, quarantine, apply=args.apply):
            counts.shard_files_quarantined += 1
        counts.sidecars_quarantined += quarantine_orphan_sidecars(
            folder,
            args.dest_root,
            quarantine,
            apply=args.apply,
        )
        remove_empty_dirs(folder, args.dest_root, apply=args.apply)

    for relpath in sorted(repaired_relpaths):
        source = args.source_root / relpath
        dest = args.dest_root / relpath
        copied, backed_up = copy_repaired_file(
            source,
            dest,
            args.dest_root,
            quarantine,
            apply=args.apply,
        )
        if copied:
            counts.repaired_files_copied += 1
        else:
            counts.missing_on_source += 1
        if backed_up:
            counts.repaired_files_backed_up += 1

    mode = "APPLIED" if args.apply else "DRY RUN"
    print(f"{mode}: SSD cleanup sync")
    print(f"destination: {args.dest_root}")
    print(f"quarantine: {quarantine}")
    print(f"shard files quarantined: {counts.shard_files_quarantined}")
    print(f"sidecars quarantined: {counts.sidecars_quarantined}")
    print(f"repaired files copied: {counts.repaired_files_copied}")
    print(f"repaired destination files backed up: {counts.repaired_files_backed_up}")
    print(f"missing on destination: {counts.missing_on_dest}")
    print(f"missing on source: {counts.missing_on_source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
