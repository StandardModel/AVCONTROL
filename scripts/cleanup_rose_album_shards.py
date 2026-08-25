#!/usr/bin/env python3
"""
Quarantine copied Rose album shards and repair obvious album-level tag splits.

This script consumes reports/rose_library_album_shards.csv from
audit_rose_library.py. It is intentionally reversible:

- one-track/small "Unknown Album" shards are moved to a timestamped quarantine
- files whose tags are repaired are copied to quarantine/_tag_backups first
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from mutagen import File as MutagenFile


AUDIO_EXTENSIONS = {".aif", ".aiff", ".flac", ".m4a", ".mp3", ".wav", ".wave"}
SIDECARE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
DEFAULT_ROOT = Path("/Users/roncompton/Music/RoseMusicWork/Music")
DEFAULT_REPORT = Path("/Users/roncompton/AVCONTROL/reports/rose_library_album_shards.csv")
DEFAULT_QUARANTINE_ROOT = Path("/Users/roncompton/Music/RoseMusicWork/_quarantine")

ALBUM_ARTISTS = {
    "A Musical History": "The Band",
}


@dataclass
class ActionCounts:
    moved_audio: int = 0
    moved_sidecars: int = 0
    repaired_tags: int = 0
    skipped: int = 0


def clean_token(value: str) -> str:
    value = re.sub(r"[_~]+", " ", value or "")
    value = re.sub(r"^\s*\d+\s+", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" -_.,")


def parse_track_number(value: str) -> str:
    match = re.match(r"\s*(\d+)", value or "")
    return str(int(match.group(1))) if match else ""


def parse_disc_number(value: str) -> str:
    match = re.search(r"\[CD\s*(\d+)\]", value or "", re.I)
    return str(int(match.group(1))) if match else ""


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 2
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def move_to_quarantine(path: Path, root: Path, quarantine: Path, *, apply: bool) -> bool:
    if not path.exists():
        return False

    relative = path.relative_to(root)
    destination = unique_destination(quarantine / relative)
    if apply:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(destination))
    return True


def folder_has_audio(folder: Path) -> bool:
    return any(path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS for path in folder.iterdir())


def move_orphan_sidecars(folder: Path, root: Path, quarantine: Path, *, apply: bool) -> int:
    if not folder.exists() or folder_has_audio(folder):
        return 0

    moved = 0
    for path in folder.iterdir():
        if path.is_file() and path.suffix.lower() in SIDECARE_EXTENSIONS:
            if move_to_quarantine(path, root, quarantine, apply=apply):
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


def set_tag(tags: object, name: str, value: str) -> None:
    if value:
        tags[name] = [value]


def repair_tags(path: Path, row: dict[str, str], root: Path, quarantine: Path, *, apply: bool) -> bool:
    if not path.exists():
        return False

    album = row["probable_source_album"] or row["tag_album"]
    album_artist = ALBUM_ARTISTS.get(album)
    track_title = row["probable_track_title"]
    track_number = parse_track_number(row["tag_artist"])
    disc_number = parse_disc_number(row["tag_title"])

    if not album or not album_artist or not track_title:
        return False

    if apply:
        backup = unique_destination(quarantine / "_tag_backups" / path.relative_to(root))
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)

        audio = MutagenFile(path, easy=True)
        if audio is None:
            return False
        if audio.tags is None:
            audio.add_tags()

        set_tag(audio.tags, "title", clean_token(track_title))
        set_tag(audio.tags, "album", album)
        set_tag(audio.tags, "albumartist", album_artist)
        if track_number:
            set_tag(audio.tags, "tracknumber", track_number)
        if disc_number:
            set_tag(audio.tags, "discnumber", disc_number)
        audio.save()

    return True


def load_rows(report: Path) -> list[dict[str, str]]:
    with report.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--quarantine-root", type=Path, default=DEFAULT_QUARANTINE_ROOT)
    parser.add_argument("--apply", action="store_true", help="perform moves and tag edits")
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    quarantine = args.quarantine_root / f"album-shards-{stamp}"
    counts = ActionCounts()

    rows = load_rows(args.report)
    unknown_paths = {
        Path(row["path"])
        for row in rows
        if row["problem"] == "unknown_album_shard" and row["path"]
    }
    repair_rows = [
        row
        for row in rows
        if row["problem"] == "malformed_album_track" and row["path"]
    ]

    for path in sorted(unknown_paths):
        if not path.exists():
            counts.skipped += 1
            continue
        source_folder = path.parent
        if move_to_quarantine(path, args.root, quarantine, apply=args.apply):
            counts.moved_audio += 1
        counts.moved_sidecars += move_orphan_sidecars(source_folder, args.root, quarantine, apply=args.apply)
        remove_empty_dirs(source_folder, args.root, apply=args.apply)

    for row in repair_rows:
        path = Path(row["path"])
        if repair_tags(path, row, args.root, quarantine, apply=args.apply):
            counts.repaired_tags += 1
        else:
            counts.skipped += 1

    mode = "APPLIED" if args.apply else "DRY RUN"
    print(f"{mode}: quarantine location: {quarantine}")
    print(f"audio files moved to quarantine: {counts.moved_audio}")
    print(f"sidecar images moved to quarantine: {counts.moved_sidecars}")
    print(f"files with repaired tags: {counts.repaired_tags}")
    print(f"skipped: {counts.skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
