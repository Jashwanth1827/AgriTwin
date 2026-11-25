"""Extend the leakage-free manifest with CC BY 4.0 PlantTom training images.

PlantTom contains 8 tomato disease classes already present in the deployed
38-class label space. This script adds only its ``train`` split as extra
training images; the existing official PlantVillage/PlantDoc test split is
never modified.

Filters
-------
* YOLO images whose label file contains more than one class are skipped.
* Byte-identical copies of any existing image are skipped.
* Held-out test images are protected with 64-bit perceptual hash and
  difference hash comparisons (pHash <= 10 and dHash <= 11).
* Exact perceptual duplicates already accepted from PlantTom are skipped.

Usage
-----
    python ml/crop_health/training/prepare_planttom_manifest.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageOps

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BASE = REPO_ROOT / "ml/crop_health/data/field_robust/manifest_dedup.json"
DEFAULT_SOURCE = REPO_ROOT / "ml/crop_health/data/external/planttom/extracted/train"
DEFAULT_OUTPUT = REPO_ROOT / "ml/crop_health/data/field_robust/manifest_planttom.json"
DEFAULT_REPORT = REPO_ROOT / "ml/crop_health/evaluation/planttom_dedupe_report.json"
ARCHIVE = REPO_ROOT / "ml/crop_health/data/external/planttom/PlantTom.zip"

CLASS_ID_TO_LABEL = {
    "0": "Tomato___Bacterial_spot",
    "1": "Tomato___Early_blight",
    "2": "Tomato___Late_blight",
    "3": "Tomato___Leaf_Mold",
    "4": "Tomato___Tomato_mosaic_virus",
    "5": "Tomato___Septoria_leaf_spot",
    "6": "Tomato___Spider_mites_Two-spotted_spider_mite",
    "7": "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
}
SOURCE_CLASS_NAMES = {
    "0": "Bacterial Spot",
    "1": "Early Blight",
    "2": "Late Blight",
    "3": "Leaf Mold",
    "4": "Mosaic Virus",
    "5": "Septoria",
    "6": "Spider Mites",
    "7": "Yellow Leaf Curl Virus",
}
PHASH_THRESHOLD = 10
DHASH_THRESHOLD = 11
INTRA_PHASH_THRESHOLD = 0
INTRA_DHASH_THRESHOLD = 0


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def perceptual_hashes(path: Path) -> tuple[int, int]:
    """Return 64-bit pHash and dHash for near-duplicate detection."""
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
    gray = image.convert("L")

    pixels = np.asarray(gray.resize((32, 32), Image.Resampling.LANCZOS), dtype=np.float32)
    dct = cv2.dct(pixels)[:8, :8].copy()
    median = float(np.median(dct[1:]))
    phash_bits = (dct > median).flatten()[1:]
    phash = 0
    for bit in phash_bits:
        phash = (phash << 1) | int(bit)

    pixels = np.asarray(gray.resize((9, 8), Image.Resampling.LANCZOS), dtype=np.float32)
    dhash_bits = (pixels[:, 1:] > pixels[:, :-1]).flatten()
    dhash = 0
    for bit in dhash_bits:
        dhash = (dhash << 1) | int(bit)
    return phash, dhash


def hamming(left: int, right: int) -> int:
    return int((left ^ right).bit_count())


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-manifest", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--max-per-class", type=int, default=None,
                        help="cap accepted PlantTom images per tomato class (deterministic first N)")
    args = parser.parse_args()

    base = load_json(args.base_manifest)
    class_order = base["class_order"]
    label_index = {name: index for index, name in enumerate(class_order)}
    entries = list(base["entries"])

    existing_hashes: dict[str, dict[str, Any]] = {}
    held_out: list[tuple[int, int, dict[str, Any]]] = []
    for entry in entries:
        image_path = Path(entry["path"])
        if not image_path.is_absolute():
            image_path = REPO_ROOT / image_path
        digest = sha256_file(image_path)
        existing_hashes.setdefault(digest, entry)
        if entry["split"] == "test":
            held_out.append((*perceptual_hashes(image_path), entry))

    image_dir = args.source_dir / "images"
    label_dir = args.source_dir / "labels"
    if not image_dir.is_dir() or not label_dir.is_dir():
        raise SystemExit(f"PlantTom train folders not found under: {args.source_dir}")

    stats: Counter[str] = Counter()
    accepted: list[dict[str, Any]] = []
    accepted_hashes: dict[str, dict[str, Any]] = {}
    accepted_perceptual: list[tuple[int, int, dict[str, Any]]] = []
    skipped_details: list[dict[str, Any]] = []
    ambiguous_count = 0

    for label_file in sorted(label_dir.glob("*.txt")):
        stats["label_files"] += 1
        class_ids = {
            parts[0]
            for line in label_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and (parts := line.split())
        }
        if len(class_ids) != 1 or next(iter(class_ids)) not in CLASS_ID_TO_LABEL:
            ambiguous_count += 1
            continue
        class_id = next(iter(class_ids))
        image_path = image_dir / label_file.with_suffix(".jpg").name
        if not image_path.is_file():
            stats["missing_image"] += 1
            continue

        digest = sha256_file(image_path)
        if digest in existing_hashes or digest in accepted_hashes:
            stats["exact_duplicate"] += 1
            continue

        phash, dhash = perceptual_hashes(image_path)
        test_matches = [
            entry for test_phash, test_dhash, entry in held_out
            if hamming(phash, test_phash) <= PHASH_THRESHOLD
            and hamming(dhash, test_dhash) <= DHASH_THRESHOLD
        ]
        if test_matches:
            stats["near_test_duplicate"] += 1
            if len(skipped_details) < 100:
                skipped_details.append({
                    "reason": "near_test_duplicate",
                    "path": relative(image_path),
                    "label": CLASS_ID_TO_LABEL[class_id],
                    "matched_test": relative(Path(test_matches[0]["path"])),
                    "phash_distance": min(hamming(phash, tp) for tp, _, _ in held_out),
                    "dhash_distance": min(hamming(dhash, td) for _, td, _ in held_out),
                })
            continue

        source_duplicate = next(
            (
                entry for seen_phash, seen_dhash, entry in accepted_perceptual
                if hamming(phash, seen_phash) <= INTRA_PHASH_THRESHOLD
                and hamming(dhash, seen_dhash) <= INTRA_DHASH_THRESHOLD
            ),
            None,
        )
        if source_duplicate is not None:
            stats["intra_source_perceptual_duplicate"] += 1
            continue

        label = CLASS_ID_TO_LABEL[class_id]
        item = {
            "path": relative(image_path),
            "label": label,
            "label_index": label_index[label],
            "domain": "web",
            "split": "train",
            "source_class": f"PlantTom/{SOURCE_CLASS_NAMES[class_id]}",
        }
        accepted.append(item)
        accepted_hashes[digest] = item
        accepted_perceptual.append((phash, dhash, item))
        stats["accepted"] += 1

    if args.max_per_class is not None:
        counts: Counter[str] = Counter()
        capped: list[dict[str, Any]] = []
        for item in accepted:
            if counts[item["label"]] < args.max_per_class:
                capped.append(item)
                counts[item["label"]] += 1
        stats["capped_out"] = len(accepted) - len(capped)
        accepted = capped

    extended = dict(base)
    extended["extended_at"] = datetime.now(timezone.utc).isoformat()
    extended["extension_source"] = (
        "PlantTom (CC BY 4.0, Vaskor Mostafa), train split only; "
        "held-out test entries unchanged"
    )
    sources = dict(base.get("sources", {}))
    sources["web"] = (
        "ml/crop_health/data/external/planttom (CC BY 4.0, Vaskor Mostafa; "
        "tomato leaf disease images; PlantTom train split only)"
    )
    extended["sources"] = sources
    extended["entries"] = entries + accepted

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "name": "PlantTom Dataset for Tomato Leaf Disease Detection",
            "author": "Vaskor Mostafa",
            "license": "CC BY 4.0",
            "url": "https://huggingface.co/datasets/vaskormostafa/PlantTom",
            "archive": relative(ARCHIVE) if ARCHIVE.exists() else None,
            "archive_sha256": sha256_file(ARCHIVE) if ARCHIVE.exists() else None,
            "used_split": "train",
            "base_manifest": relative(args.base_manifest),
        },
        "filters": {
            "phash_threshold": PHASH_THRESHOLD,
            "dhash_threshold": DHASH_THRESHOLD,
            "intra_source_phash_threshold": INTRA_PHASH_THRESHOLD,
            "intra_source_dhash_threshold": INTRA_DHASH_THRESHOLD,
            "held_out_images_protected": len(held_out),
            "max_per_class": args.max_per_class,
        },
        "counts": {
            "base_entries": len(base["entries"]),
            "planttom_label_files": stats["label_files"],
            "ambiguous_multi_class_or_unmapped": ambiguous_count,
            "missing_image": stats["missing_image"],
            "exact_duplicate": stats["exact_duplicate"],
            "near_test_duplicate": stats["near_test_duplicate"],
            "intra_source_perceptual_duplicate": stats["intra_source_perceptual_duplicate"],
            "capped_out": stats["capped_out"],
            "accepted": len(accepted),
            "extended_entries": len(extended["entries"]),
        },
        "accepted_by_class": dict(sorted(Counter(e["label"] for e in accepted).items())),
        "skipped_examples": skipped_details,
    }

    write_json(args.output, extended)
    write_json(args.report, report)
    print(json.dumps(report["counts"], indent=2))
    print(f"Manifest: {args.output}")
    print(f"Report:   {args.report}")


if __name__ == "__main__":
    main()
