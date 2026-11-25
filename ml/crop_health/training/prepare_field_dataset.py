"""Build a domain-robust crop-health dataset (PlantVillage + PlantDoc + your own web images).

WHY THIS EXISTS
---------------
The current AgriTwin model is trained only on PlantVillage: 1,900 leaves photographed
in a lab, face-up, on a uniform background. It scores ~0.94 there but collapses on
Google/field photographs because it learned the *background*, not the disease.

This script keeps the same 38-class output space as the deployed app, and adds
"in-the-wild" images from PlantDoc (https://github.com/pratikkayal/PlantDoc-Dataset,
CC BY 4.0) plus any web images you collected yourself. Every image is tagged with a
`domain` so the training script can measure the lab-to-field gap explicitly.

Usage
-----
1) Download PlantDoc once (choose ONE option):

   Option A -- git clone (recommended, ~few hundred MB):
       git clone --depth 1 https://github.com/pratikkayal/PlantDoc-Dataset.git \
           ml/crop_health/data/plantdoc

   Option B -- let this script try it:
       python ml/crop_health/training/prepare_field_dataset.py --download-plantdoc

   Option C -- Kaggle copy with cleaned filenames:
       https://www.kaggle.com/datasets/nirmalsankalana/plantdoc-dataset
       then pass --plantdoc-dir <extracted folder containing train/ and test/>

2) Build the manifest:

   python ml/crop_health/training/prepare_field_dataset.py \
       --plantdoc-dir ml/crop_health/data/plantdoc \
       --out ml/crop_health/data/field_robust/manifest.json

3) (Optional but strongly recommended for the paper) Put your failed Google images
   into class folders named with the EXACT 38 deployed label names, e.g.

       ml/crop_health/data/web_images/Tomato___Early_blight/IMG_001.jpg
       ml/crop_health/data/web_images/Tomato___Early_blight/IMG_002.jpg

   and pass --web-dir ml/crop_health/data/web_images. They are used as a
   test-only external domain -- precisely the images the old model got wrong.

Output: <out>/manifest.json with entries
    {path, label, label_index, domain, split, source_class}
where domain in {pv, pd, web} and split in {train, val, test}.

No images are copied; paths are stored relative to the repository root.
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PV_DIR = REPO_ROOT / "ml" / "crop_health" / "data" / "plantvillage_subset"
DEFAULT_PD_DIR = REPO_ROOT / "ml" / "crop_health" / "data" / "plantdoc"
DEFAULT_METADATA = REPO_ROOT / "backend" / "app" / "ml" / "artifacts" / "crop_health" / "metadata.json"
DEFAULT_OUT = REPO_ROOT / "ml" / "crop_health" / "data" / "field_robust" / "manifest.json"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# The official PlantDoc classification folder names -> the 38 deployed AgriTwin labels.
# All 28 folders map 1:1 onto existing classes, so the app needs no change.
PLANTDOC_TO_AGRITWIN = {
    "Apple Scab Leaf": "Apple___Apple_scab",
    "Apple leaf": "Apple___healthy",
    "Apple rust leaf": "Apple___Cedar_apple_rust",
    "Bell_pepper leaf spot": "Pepper_bell___Bacterial_spot",
    "Bell_pepper leaf": "Pepper_bell___healthy",
    "Blueberry leaf": "Blueberry___healthy",
    "Cherry leaf": "Cherry_including_sour___healthy",
    "Corn Gray leaf spot": "Corn_maize___Cercospora_leaf_spot_Gray_leaf_spot",
    "Corn leaf blight": "Corn_maize___Northern_Leaf_Blight",
    "Corn rust leaf": "Corn_maize___Common_rust_",
    "Peach leaf": "Peach___healthy",
    "Potato leaf early blight": "Potato___Early_blight",
    "Potato leaf late blight": "Potato___Late_blight",
    "Raspberry leaf": "Raspberry___healthy",
    "Soyabean leaf": "Soybean___healthy",
    "Squash Powdery mildew leaf": "Squash___Powdery_mildew",
    "Strawberry leaf": "Strawberry___healthy",
    "Tomato Early blight leaf": "Tomato___Early_blight",
    "Tomato Septoria leaf spot": "Tomato___Septoria_leaf_spot",
    "Tomato leaf bacterial spot": "Tomato___Bacterial_spot",
    "Tomato leaf late blight": "Tomato___Late_blight",
    "Tomato leaf mosaic virus": "Tomato___Tomato_mosaic_virus",
    "Tomato leaf yellow virus": "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato leaf": "Tomato___healthy",
    "Tomato mold leaf": "Tomato___Leaf_Mold",
    "Tomato two spotted spider mites leaf": "Tomato___Spider_mites_Two-spotted_spider_mite",
    "grape leaf black rot": "Grape___Black_rot",
    "grape leaf": "Grape___healthy",
}

# Fallback used only if the deployed metadata.json cannot be found.
FALLBACK_CLASS_ORDER = [
    "Apple___Apple_scab", "Apple___Black_rot", "Apple___Cedar_apple_rust", "Apple___healthy",
    "Blueberry___healthy", "Cherry_including_sour___healthy", "Cherry_including_sour___Powdery_mildew",
    "Corn_maize___Cercospora_leaf_spot_Gray_leaf_spot", "Corn_maize___Common_rust_",
    "Corn_maize___healthy", "Corn_maize___Northern_Leaf_Blight", "Grape___Black_rot",
    "Grape___Esca_Black_Measles", "Grape___healthy", "Grape___Leaf_blight_Isariopsis_Leaf_Spot",
    "Orange___Haunglongbing_Citrus_greening", "Peach___Bacterial_spot", "Peach___healthy",
    "Pepper_bell___Bacterial_spot", "Pepper_bell___healthy", "Potato___Early_blight",
    "Potato___healthy", "Potato___Late_blight", "Raspberry___healthy", "Soybean___healthy",
    "Squash___Powdery_mildew", "Strawberry___healthy", "Strawberry___Leaf_scorch",
    "Tomato___Bacterial_spot", "Tomato___Early_blight", "Tomato___healthy", "Tomato___Late_blight",
    "Tomato___Leaf_Mold", "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites_Two-spotted_spider_mite", "Tomato___Target_Spot",
    "Tomato___Tomato_mosaic_virus", "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
]


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def image_files(class_dir: Path) -> list[Path]:
    return sorted(
        p for p in class_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    )


def load_class_order(metadata_path: Path) -> list[str]:
    if metadata_path.exists():
        with metadata_path.open("r", encoding="utf-8") as handle:
            order = json.load(handle).get("classes")
        if order and len(order) == 38:
            return list(order)
    return list(FALLBACK_CLASS_ORDER)


def ensure_plantdoc(plantdoc_dir: Path) -> None:
    if (plantdoc_dir / "train").is_dir():
        return
    if shutil_git_available() is False:
        raise SystemExit(
            "git was not found. Download PlantDoc manually from "
            "https://github.com/pratikkayal/PlantDoc-Dataset and pass --plantdoc-dir."
        )
    plantdoc_dir.parent.mkdir(parents=True, exist_ok=True)
    print(f"Cloning PlantDoc into {plantdoc_dir} ...")
    subprocess.run(
        [
            "git", "clone", "--depth", "1",
            "https://github.com/pratikkayal/PlantDoc-Dataset.git",
            str(plantdoc_dir),
        ],
        check=True,
    )


def shutil_git_available() -> bool:
    import shutil
    return shutil.which("git") is not None


def split_plantvillage(pv_dir: Path, seed: int) -> list[tuple[Path, str, str, str]]:
    """Replicate the existing train.py 70/15/15 split so baseline numbers stay comparable."""
    rng = random.Random(seed)
    rows: list[tuple[Path, str, str, str]] = []
    for class_dir in sorted(p for p in pv_dir.iterdir() if p.is_dir()):
        files = image_files(class_dir)
        rng.shuffle(files)
        n_test = max(1, int(len(files) * 0.15))
        n_val = max(1, int(len(files) * 0.15))
        for path in files[:n_test]:
            rows.append((path, class_dir.name, "pv", "test"))
        for path in files[n_test:n_test + n_val]:
            rows.append((path, class_dir.name, "pv", "val"))
        for path in files[n_test + n_val:]:
            rows.append((path, class_dir.name, "pv", "train"))
    return rows


def split_plantdoc(pd_dir: Path, seed: int) -> list[tuple[Path, str, str, str]]:
    """Use the official test split as an external domain; carve 15% of train for validation."""
    rng = random.Random(seed + 1)
    rows: list[tuple[Path, str, str, str]] = []
    unmatched: set[str] = set()

    for split_name in ("train", "test"):
        split_dir = pd_dir / split_name
        if not split_dir.is_dir():
            continue
        for class_dir in sorted(p for p in split_dir.iterdir() if p.is_dir()):
            mapped = PLANTDOC_TO_AGRITWIN.get(class_dir.name)
            if mapped is None:
                unmatched.add(class_dir.name)
                continue
            files = image_files(class_dir)
            rng.shuffle(files)
            if split_name == "test":
                for path in files:
                    rows.append((path, mapped, "pd", "test"))
            else:
                n_val = max(1, int(len(files) * 0.15))
                for path in files[:n_val]:
                    rows.append((path, mapped, "pd", "val"))
                for path in files[n_val:]:
                    rows.append((path, mapped, "pd", "train"))

    if unmatched:
        print(f"WARNING unmapped PlantDoc folders (ignored): {sorted(unmatched)}")
    return rows


def collect_web(web_dir: Path | None, class_order: list[str]) -> list[tuple[Path, str, str, str]]:
    if web_dir is None:
        return []
    if not web_dir.is_dir():
        raise SystemExit(f"Web image directory not found: {web_dir}")
    rows: list[tuple[Path, str, str, str]] = []
    valid = set(class_order)
    for class_dir in sorted(p for p in web_dir.iterdir() if p.is_dir()):
        if class_dir.name not in valid:
            print(f"WARNING unknown web class folder (ignored): {class_dir.name}")
            continue
        for path in image_files(class_dir):
            rows.append((path, class_dir.name, "web", "test"))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pv-dir", type=Path, default=DEFAULT_PV_DIR)
    parser.add_argument("--plantdoc-dir", type=Path, default=DEFAULT_PD_DIR)
    parser.add_argument("--download-plantdoc", action="store_true")
    parser.add_argument("--web-dir", type=Path, default=None)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    class_order = load_class_order(args.metadata)
    class_to_index = {name: index for index, name in enumerate(class_order)}

    if args.download_plantdoc:
        ensure_plantdoc(args.plantdoc_dir)

    if not args.pv_dir.is_dir():
        raise SystemExit(f"PlantVillage subset not found: {args.pv_dir}")

    rows: list[tuple[Path, str, str, str]] = []
    rows += split_plantvillage(args.pv_dir, args.seed)

    if (args.plantdoc_dir / "train").is_dir():
        rows += split_plantdoc(args.plantdoc_dir, args.seed)
    else:
        print("PlantDoc not found -> manifest will contain PlantVillage only. "
              "See this file's docstring for download options.")

    rows += collect_web(args.web_dir, class_order)

    entries = []
    for path, label, domain, split in rows:
        entries.append(
            {
                "path": relative(path),
                "label": label,
                "label_index": class_to_index[label],
                "domain": domain,
                "split": split,
                "source_class": path.parent.name,
            }
        )

    entries.sort(key=lambda e: (e["domain"], e["split"], e["label"], e["path"]))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "class_order": class_order,
        "num_classes": len(class_order),
        "sources": {
            "pv": relative(args.pv_dir) + " (controlled lab images, 38 classes)",
            "pd": relative(args.plantdoc_dir)
            + " (PlantDoc, CC BY 4.0, in-the-wild internet images, 28 folders mapped)",
            "web": relative(args.web_dir) if args.web_dir else None,
        },
        "entries": entries,
    }
    with args.out.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    by_domain_split = Counter((e["domain"], e["split"]) for e in entries)
    print(f"Wrote {len(entries)} entries to {args.out}")
    for (domain, split), count in sorted(by_domain_split.items()):
        print(f"  {domain:>3s} / {split:<5s}: {count}")
    if not any(e["domain"] == "pd" for e in entries):
        print("\nIMPORTANT: PlantDoc is missing. Without it this is still the old lab-only "
              "dataset and the model will still fail on Google images.")


if __name__ == "__main__":
    main()
