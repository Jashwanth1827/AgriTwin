"""Build a balanced PlantVillage subset from the Hugging Face parquet shards.

Usage:
    python ml/crop_health/training/prepare_dataset.py \
        --parquet-dir C:/path/to/shards --out ml/crop_health/data/plantvillage_subset --per-class 40

Download the three parquet shards from:
    https://huggingface.co/datasets/Hemg/new-plant-diseases-dataset

The dataset is ordered by class, so the shards are streamed in order and the
first ``per_class`` images of each class are retained.  This keeps the demo
subset small (about 1,500 images) while covering all 38 classes.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pyarrow.parquet as pq
from PIL import Image

CLASS_NAMES = [
    "Apple___Apple_scab",
    "Apple___Black_rot",
    "Apple___Cedar_apple_rust",
    "Apple___healthy",
    "Blueberry___healthy",
    "Cherry_(including_sour)___Powdery_mildew",
    "Cherry_(including_sour)___healthy",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "Corn_(maize)___Common_rust_",
    "Corn_(maize)___Northern_Leaf_Blight",
    "Corn_(maize)___healthy",
    "Grape___Black_rot",
    "Grape___Esca_(Black_Measles)",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)",
    "Grape___healthy",
    "Orange___Haunglongbing_(Citrus_greening)",
    "Peach___Bacterial_spot",
    "Peach___healthy",
    "Pepper,_bell___Bacterial_spot",
    "Pepper,_bell___healthy",
    "Potato___Early_blight",
    "Potato___Late_blight",
    "Potato___healthy",
    "Raspberry___healthy",
    "Soybean___healthy",
    "Squash___Powdery_mildew",
    "Strawberry___Leaf_scorch",
    "Strawberry___healthy",
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite",
    "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    "Tomato___Tomato_mosaic_virus",
    "Tomato___healthy",
]


def _safe(name: str) -> str:
    return name.replace(" ", "_").replace(",", "").replace("(", "").replace(")", "")


def _decode_image(value) -> Image.Image:
    if isinstance(value, dict):
        data = value.get("bytes")
        if data:
            from io import BytesIO

            return Image.open(BytesIO(data)).convert("RGB")
        path = value.get("path")
        if path:
            return Image.open(path).convert("RGB")
    raise ValueError("Unsupported image representation in parquet shard")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parquet-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("ml/crop_health/data/plantvillage_subset"))
    parser.add_argument("--per-class", type=int, default=40)
    args = parser.parse_args()

    shards = sorted(args.parquet_dir.glob("*.parquet"))
    if not shards:
        raise SystemExit(f"No parquet shards found in {args.parquet_dir}")

    counts = {name: 0 for name in CLASS_NAMES}
    args.out.mkdir(parents=True, exist_ok=True)
    total = len(CLASS_NAMES) * args.per_class
    written = 0

    for shard in shards:
        parquet = pq.ParquetFile(shard)
        print(f"Streaming {shard.name} ...")
        for batch in parquet.iter_batches(batch_size=64, columns=["image", "label"]):
            images = batch.column("image").to_pylist()
            labels = batch.column("label").to_pylist()
            for image_value, label_index in zip(images, labels):
                if label_index is None or label_index >= len(CLASS_NAMES):
                    continue
                name = CLASS_NAMES[int(label_index)]
                if counts[name] >= args.per_class:
                    continue
                try:
                    image = _decode_image(image_value)
                except Exception as exc:
                    print(f"  skip image: {exc}")
                    continue
                class_dir = args.out / _safe(name)
                class_dir.mkdir(parents=True, exist_ok=True)
                image.save(class_dir / f"{counts[name]:04d}.jpg", quality=92)
                counts[name] += 1
                written += 1
            if written >= total:
                break
        if written >= total:
            break

    missing = {name: count for name, count in counts.items() if count == 0}
    print(f"Wrote {written} images to {args.out}")
    if missing:
        print(f"Classes with no images: {sorted(missing)}")
    for name, count in counts.items():
        print(f"  {count:3d}  {name}")


if __name__ == "__main__":
    main()
