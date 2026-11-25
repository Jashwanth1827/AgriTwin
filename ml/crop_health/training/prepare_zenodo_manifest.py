"""Extend the leakage-free manifest with Zenodo multi-crop training images.

Source: Crop Health Monitoring Dataset (DOI 10.5281/zenodo.10628735), CC BY 4.0.
Only folders that map unambiguously onto the deployed 38-class label space are
used. The official PlantVillage/PlantDoc test split is never modified.

Filters
-------
* Byte-identical copies of any existing image are skipped.
* Held-out test images are protected with 64-bit pHash and dHash comparisons
  (pHash <= 10 and dHash <= 11).
* Exact perceptual duplicates inside the new source are skipped.

Usage
-----
    python ml/crop_health/training/prepare_zenodo_manifest.py
    python ml/crop_health/training/prepare_zenodo_manifest.py --max-per-class 300
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
DEFAULT_SOURCE = REPO_ROOT / "ml/crop_health/data/external/zenodo_multicrop/extracted/dataset"
DEFAULT_OUTPUT = REPO_ROOT / "ml/crop_health/data/field_robust/manifest_zenodo.json"
DEFAULT_REPORT = REPO_ROOT / "ml/crop_health/evaluation/zenodo_dedupe_report.json"
ARCHIVE = REPO_ROOT / "ml/crop_health/data/external/zenodo_multicrop/dataset.zip"

SOURCE_TO_LABEL = {
    ("apple", "Apple_black_rot"): "Apple___Black_rot",
    ("apple", "Apple_cedar_rust"): "Apple___Cedar_apple_rust",
    ("apple", "Healthy leaves"): "Apple___healthy",
    ("maize", "Common_Rust"): "Corn_maize___Common_rust_",
    ("maize", "Gray_Leaf_Spot"): "Corn_maize___Cercospora_leaf_spot_Gray_leaf_spot",
    ("maize", "Healthy"): "Corn_maize___healthy",
    ("tomatoes", "Tomato___Bacterial_spot"): "Tomato___Bacterial_spot",
    ("tomatoes", "Tomato___Early_blight"): "Tomato___Early_blight",
    ("tomatoes", "Tomato___healthy"): "Tomato___healthy",
}

PHASH_THRESHOLD = 10
DHASH_THRESHOLD = 11
INTRA_PHASH_THRESHOLD = 0
INTRA_DHASH_THRESHOLD = 0
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


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
                        help="cap accepted images per deployed class (deterministic first N)")
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

    if not args.source_dir.is_dir():
        raise SystemExit(f"Zenodo dataset folder not found: {args.source_dir}")

    stats: Counter[str] = Counter()
    accepted: list[dict[str, Any]] = []
    accepted_hashes: dict[str, dict[str, Any]] = {}
    accepted_perceptual: list[tuple[int, int, dict[str, Any]]] = []
    skipped_details: list[dict[str, Any]] = []
    unmapped_by_folder: Counter[str] = Counter()

    image_paths = sorted(
        path for path in args.source_dir.rglob("*")
        if path.suffix.lower() in IMAGE_SUFFIXES
    )

    for image_path in image_paths:
        stats["image_files"] += 1
        parts = image_path.relative_to(args.source_dir).parts
        if len(parts) < 3:
            stats["unexpected_layout"] += 1
            continue
        crop, folder = parts[0], parts[1]
        key = (crop, folder)
        if key not in SOURCE_TO_LABEL:
            unmapped_by_folder[str(Path(crop) / folder)] += 1
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
                    "label": SOURCE_TO_LABEL[key],
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

        label = SOURCE_TO_LABEL[key]
        item = {
            "path": relative(image_path),
            "label": label,
            "label_index": label_index[label],
            "domain": "web",
            "split": "train",
            "source_class": f"Zenodo/{crop}/{folder}",
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
        "Zenodo Crop Health Monitoring Dataset (CC BY 4.0, Gibson and Förster), "
        "deduplicated folders mapped onto the deployed 38-class label space; "
        "held-out test entries unchanged"
    )
    sources = dict(base.get("sources", {}))
    sources["web"] = (
        "ml/crop_health/data/external/zenodo_multicrop (CC BY 4.0, Gibson and Förster; "
        "multi-crop disease images; unambiguous 38-class folders only)"
    )
    extended["sources"] = sources
    extended["entries"] = entries + accepted

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "name": "Crop Health Monitoring Dataset: Disease Classification in Maize, Tea, Tomatoes, Apples, and Beans",
            "authors": ["Kimutai Gibson", "Anna Förster"],
            "license": "CC BY 4.0",
            "doi": "10.5281/zenodo.10628735",
            "url": "https://zenodo.org/records/10628735",
            "direct_download": "https://zenodo.org/api/records/10628735/files/dataset.zip/content",
            "archive": relative(ARCHIVE) if ARCHIVE.exists() else None,
            "archive_sha256": sha256_file(ARCHIVE) if ARCHIVE.exists() else None,
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
            "zenodo_image_files": stats["image_files"],
            "unexpected_layout": stats["unexpected_layout"],
            "exact_duplicate": stats["exact_duplicate"],
            "near_test_duplicate": stats["near_test_duplicate"],
            "intra_source_perceptual_duplicate": stats["intra_source_perceptual_duplicate"],
            "capped_out": stats["capped_out"],
            "accepted": len(accepted),
            "extended_entries": len(extended["entries"]),
        },
        "unmapped_by_folder": dict(sorted(unmapped_by_folder.items())),
        "accepted_by_class": dict(sorted(Counter(e["label"] for e in accepted).items())),
        "skipped_examples": skipped_details,
    }

    write_json(args.output, extended)
    write_json(args.report, report)
    print(json.dumps(report["counts"], indent=2))
    print("Accepted by class:", json.dumps(report["accepted_by_class"], indent=2))
    print(f"Manifest: {args.output}")
    print(f"Report:   {args.report}")


if __name__ == "__main__":
    main()
