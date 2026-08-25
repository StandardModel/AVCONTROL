#!/usr/bin/env python3
"""
Audit a copied HiFi Rose/Roon-ready music folder for album shards.

The common failure this catches is a full album plus many one-track folders such
as "Move Me (Song Sketch)/Unknown Album", where the track's real title was
written into the artist/folder field and the real album was lost.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from mutagen import File as MutagenFile


AUDIO_EXTENSIONS = {".aif", ".aiff", ".flac", ".m4a", ".mp3", ".wav"}
DEFAULT_ROOT = Path("/Users/roncompton/Music/RoseMusicWork/Music")


@dataclass(frozen=True)
class TrackInfo:
    path: Path
    title: str
    artist: str
    album: str
    album_artist: str
    track: str
    disc: str
    duration: int


def first_tag(tags: object, *names: str) -> str:
    if not tags:
        return ""

    lowered = {name.lower(): name for name in getattr(tags, "keys", lambda: [])()}
    for name in names:
        key = lowered.get(name.lower())
        if key is None:
            continue
        value = tags.get(key)
        if isinstance(value, list):
            return str(value[0]) if value else ""
        return str(value)
    return ""


def clean_token(value: str) -> str:
    value = re.sub(r"[_~]+", " ", value)
    value = re.sub(r"^\s*\d+\s+", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" -_.,")


def norm(value: str) -> str:
    value = clean_token(value).casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def iter_audio_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
            yield path


def read_track(path: Path) -> TrackInfo:
    try:
        audio = MutagenFile(path, easy=True)
    except Exception:
        audio = None
    tags = audio.tags if audio else None
    duration = 0
    if audio and audio.info and getattr(audio.info, "length", None):
        duration = int(round(float(audio.info.length)))

    return TrackInfo(
        path=path,
        title=first_tag(tags, "title"),
        artist=first_tag(tags, "artist"),
        album=first_tag(tags, "album"),
        album_artist=first_tag(tags, "albumartist", "album artist"),
        track=first_tag(tags, "tracknumber", "track"),
        disc=first_tag(tags, "discnumber", "disc"),
        duration=duration,
    )


def unknown_album_candidates(tracks: list[TrackInfo], root: Path) -> list[dict[str, str]]:
    by_folder: dict[Path, list[TrackInfo]] = defaultdict(list)
    for track in tracks:
        by_folder[track.path.parent].append(track)

    rows: list[dict[str, str]] = []
    for folder, folder_tracks in sorted(by_folder.items()):
        if folder.name.casefold() != "unknown album" or len(folder_tracks) > 3:
            continue

        artist_folder = folder.parent.name
        for track in sorted(folder_tracks, key=lambda item: item.path.name):
            source_album = ""
            match = re.match(r"(.+?)\s+\[CD\s*\d+\]", track.title or track.path.stem, re.I)
            if match:
                source_album = clean_token(match.group(1))

            rows.append(
                {
                    "problem": "unknown_album_shard",
                    "path": str(track.path),
                    "artist_folder": artist_folder,
                    "file_count_in_folder": str(len(folder_tracks)),
                    "tag_title": track.title,
                    "tag_artist": track.artist,
                    "tag_album": track.album,
                    "tag_album_artist": track.album_artist,
                    "probable_source_album": source_album,
                    "probable_track_title": clean_token(track.artist or artist_folder),
                    "duration_seconds": str(track.duration),
                }
            )
    return rows


def malformed_album_rows(tracks: list[TrackInfo]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for track in tracks:
        if not track.album:
            continue
        if not re.match(rf"^{re.escape(track.album)}\s+\[CD\s*\d+\]\s+-\s+T", track.title, re.I):
            continue
        if track.album_artist and norm(track.album_artist) == norm(track.artist):
            rows.append(
                {
                    "problem": "malformed_album_track",
                    "path": str(track.path),
                    "artist_folder": track.path.parent.parent.name if len(track.path.parents) > 1 else "",
                    "file_count_in_folder": "",
                    "tag_title": track.title,
                    "tag_artist": track.artist,
                    "tag_album": track.album,
                    "tag_album_artist": track.album_artist,
                    "probable_source_album": track.album,
                    "probable_track_title": clean_token(track.artist),
                    "duration_seconds": str(track.duration),
                }
            )
    return rows


def duplicate_title_rows(tracks: list[TrackInfo]) -> list[dict[str, str]]:
    by_key: dict[tuple[str, int], list[TrackInfo]] = defaultdict(list)
    for track in tracks:
        title = norm(track.title or track.path.stem)
        if title and track.duration:
            by_key[(title, track.duration)].append(track)

    rows: list[dict[str, str]] = []
    for (_title, _duration), matches in by_key.items():
        if len(matches) < 2:
            continue
        albums = {norm(match.album) for match in matches if match.album}
        has_unknown = any(match.path.parent.name.casefold() == "unknown album" for match in matches)
        if not has_unknown or not albums:
            continue
        for match in sorted(matches, key=lambda item: str(item.path)):
            rows.append(
                {
                    "problem": "duration_title_duplicate",
                    "path": str(match.path),
                    "artist_folder": match.path.parent.parent.name if len(match.path.parents) > 1 else "",
                    "file_count_in_folder": "",
                    "tag_title": match.title,
                    "tag_artist": match.artist,
                    "tag_album": match.album,
                    "tag_album_artist": match.album_artist,
                    "probable_source_album": match.album,
                    "probable_track_title": match.title,
                    "duration_seconds": str(match.duration),
                }
            )
    return rows


def write_csv(rows: list[dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "problem",
        "path",
        "artist_folder",
        "file_count_in_folder",
        "tag_title",
        "tag_artist",
        "tag_album",
        "tag_album_artist",
        "probable_source_album",
        "probable_track_title",
        "duration_seconds",
    ]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output", type=Path, default=Path("reports/rose_library_album_shards.csv"))
    args = parser.parse_args()

    tracks = [read_track(path) for path in iter_audio_files(args.root)]
    rows = (
        unknown_album_candidates(tracks, args.root)
        + malformed_album_rows(tracks)
        + duplicate_title_rows(tracks)
    )

    write_csv(rows, args.output)
    counts = Counter(row["problem"] for row in rows)
    print(f"Scanned {len(tracks)} audio files under {args.root}")
    print(f"Wrote {len(rows)} findings to {args.output}")
    for problem, count in sorted(counts.items()):
        print(f"{problem}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
