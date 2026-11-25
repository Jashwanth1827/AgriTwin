"""Build a leakage-free variant of the cross-domain manifest.

The original manifest keeps PlantDoc's official test split untouched, but a small
number of byte-identical images also appear in train/val — sometimes under a
different mapped class (e.g. maize northern leaf blight vs grey leaf spot).
That leaks test images into training and teaches contradictory labels.

Rules
-----
* Test entries are never removed (the held-out set stays comparable).
* A train/val entry whose bytes match any test entry is removed.
* Within a duplicate group without a test entry, one image is kept: train over
  val, then the first path in manifest order.

Usage
-----
    python ml/crop_health/training/dedupe_manifest.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST = REPO_ROOT / "ml/crop_health/data/field_robust/manifest.json"
DEFAULT_OUTPUT = REPO_ROOT / "ml/crop_health/data/field_robust/manifest_dedup.json"
DEFAULT_REPORT = REPO_ROOT / "ml/crop_health/evaluation/duplicate_images_report.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dedupe(manifest: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in manifest["entries"]:
        path = Path(entry["path"])
        resolved = path if path.is_absolute() else REPO_ROOT / path
        groups[sha256(resolved)].append(entry)

    keep: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    for _digest, entries in groups.items():
        if len(entries) == 1:
            keep.append(entries[0])
            continue
        has_test = any(entry["split"] == "test" for entry in entries)
        if has_test:
            # Keep every test image for a comparable held-out set; drop all
            # duplicated train/val views of it.
            for entry in entries:
                (keep if entry["split"] == "test" else removed).append(entry)
            continue
        candidates = sorted(entries, key=lambda e: (e["split"] != "train", e["path"]))
        keep.append(candidates[0])
        removed.extend(candidates[1:])

    order = {id(entry): index for index, entry in enumerate(manifest["entries"])}
    keep.sort(key=lambda entry: order[id(entry)])
    result = dict(manifest)
    result["entries"] = keep
    result["deduplicated_at"] = datetime.now(timezone.utc).isoformat()
    result["deduplication_source"] = "sha256 byte-identical images"
    return result, removed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    cleaned, removed = dedupe(manifest)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(cleaned, indent=2), encoding="utf-8")

    report = {
        "source_manifest": str(args.manifest),
        "output_manifest": str(args.out),
        "original_entries": len(manifest["entries"]),
        "cleaned_entries": len(cleaned["entries"]),
        "removed_entries": len(removed),
        "removed": removed,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"Manifest de-duplicated: {len(manifest['entries'])} -> "
        f"{len(cleaned['entries'])} entries ({len(removed)} removed)"
    )
    print(f"  cleaned: {args.out}")
    print(f"  report:  {args.report}")


if __name__ == "__main__":
    main()
