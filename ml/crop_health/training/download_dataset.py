"""Download the PlantVillage parquet shards used for crop-health training.

The Hugging Face dataset is ~1.1 GB across three shards.  Downloads are
resumable so a dropped connection does not lose progress.  Files are verified
by reading the parquet footer before the script reports success.

Usage:
    python ml/crop_health/training/download_dataset.py --out C:/temp/pv
"""

from __future__ import annotations

import argparse
import os
import time
import urllib.request
from pathlib import Path

BASE = "https://huggingface.co/datasets/Hemg/new-plant-diseases-dataset/resolve/main/data/"
FILES = [
    "train-00000-of-00003-4a092d89b97f4230.parquet",
    "train-00001-of-00003-d9f18f17c1302d3b.parquet",
    "train-00002-of-00003-30261853a702b231.parquet",
]
CHUNK = 1024 * 1024


def remote_size(url: str) -> int:
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "AgriTwin/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return int(response.headers["Content-Length"])


def _download_once(url: str, target: Path, expected: int) -> None:
    start = target.stat().st_size if target.exists() else 0
    if start > expected:
        target.unlink()
        start = 0
    headers = {"User-Agent": "AgriTwin/1.0"}
    if start:
        headers["Range"] = f"bytes={start}-"
        print(f"  resuming {target.name} at {start / 1e6:.0f}/{expected / 1e6:.0f} MB")
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=120) as response, target.open("ab") as handle:
        if start and response.status != 206:
            handle.seek(0)
            handle.truncate()
            start = 0
        downloaded = start
        last_report = time.time()
        while True:
            chunk = response.read(CHUNK)
            if not chunk:
                break
            handle.write(chunk)
            downloaded += len(chunk)
            if time.time() - last_report > 10:
                pct = downloaded / expected * 100 if expected else 0
                print(f"  {target.name}: {downloaded / 1e6:.0f}/{expected / 1e6:.0f} MB ({pct:.1f}%)")
                last_report = time.time()


def download(url: str, target: Path, attempts: int = 20) -> None:
    expected = remote_size(url)
    if target.exists() and target.stat().st_size == expected:
        print(f"  already complete: {target.name} ({expected / 1e6:.0f} MB)")
        return
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            _download_once(url, target, expected)
            final = target.stat().st_size
            if not expected or final == expected:
                return
            print(
                f"  attempt {attempt}: incomplete {final / 1e6:.0f}/"
                f"{expected / 1e6:.0f} MB, resuming..."
            )
        except Exception as exc:  # network drop: resume on the next attempt
            last_error = exc
            print(f"  attempt {attempt} failed: {exc}")
        time.sleep(2)
    raise RuntimeError(
        f"Incomplete download for {target.name} after {attempts} attempts: {last_error}"
    )


def verify(path: Path) -> None:
    import pyarrow.parquet as pq

    metadata = pq.ParquetFile(path).metadata
    print(f"  verified {path.name}: {metadata.num_rows:,} rows")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        target = args.out / name
        print(f"Downloading {name} ...")
        download(BASE + name, target)
        verify(target)
    print("All shards downloaded and verified.")


if __name__ == "__main__":
    main()
