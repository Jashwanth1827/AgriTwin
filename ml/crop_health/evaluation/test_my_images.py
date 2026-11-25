"""Test your own Google/farm leaf photos against the deployed AgriTwin model.

This is the practical companion to the cross-domain research: it loads the same
artifact the FastAPI service uses, predicts each image, and applies the decision
engine's confidence rule so you can see when the system would *trust* a prediction
and when it would route to INSPECT / manual verification.

Usage
-----
  # A folder of photos (any .jpg/.png/.webp ...):
  python ml/crop_health/evaluation/test_my_images.py --images path/to/folder

  # One photo:
  python ml/crop_health/evaluation/test_my_images.py --image path/to/photo.jpg

  # Compare a candidate model without touching the deployment:
  python ml/crop_health/evaluation/test_my_images.py --images path/to/folder \
      --artifact-dir backend/app/ml/artifacts/crop_health_candidate \
      --out my_results.csv --gradcam-dir my_gradcam

Verdict rule: confidence >= --threshold (default 0.55, the value in
backend/app/config/decision_policy.json) -> ACCEPT, otherwise INSPECT.
Low-confidence detections are discounted by services/decision/risk.py and trigger
the INSPECT rule in services/decision/engine.py.
"""

from __future__ import annotations

import argparse
import csv
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.ml.crop_health.service import CropHealthService  # noqa: E402

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
DEFAULT_ARTIFACTS = REPO_ROOT / "backend/app/ml/artifacts/crop_health"
DEFAULT_THRESHOLD = 0.55  # decision_policy.json -> inspect.min_health_confidence


def collect(paths: list[Path]) -> list[Path]:
    images: list[Path] = []
    for path in paths:
        if path.is_dir():
            images.extend(sorted(p for p in path.rglob("*") if p.suffix.lower() in IMAGE_EXTS))
        elif path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            images.append(path)
        else:
            print(f"WARNING skipping (not an image): {path}")
    return images


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--images", type=Path, nargs="+", help="image file(s) or folder(s)")
    group.add_argument("--image", type=Path, help="a single image file (alias for --images)")
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--out", type=Path, help="optional CSV report path")
    parser.add_argument("--gradcam-dir", type=Path, help="optional folder for Grad-CAM overlays")
    args = parser.parse_args()

    inputs = [args.image] if args.image else args.images
    images = collect(inputs)
    if not images:
        raise SystemExit("No images found. Check the path(s) and file extensions.")

    service = CropHealthService(args.artifact_dir)
    info = service.info()
    if not info.get("available"):
        raise SystemExit(f"Model unavailable: {info.get('message')}")
    print(f"Model: {info['model_version']} ({info['architecture']})")
    print(f"Classes: {len(info['classes'])} | threshold={args.threshold:.2f}")
    print(f"Testing {len(images)} image(s)\n")

    output_dir = args.gradcam_dir or Path(tempfile.mkdtemp(prefix="agritwin_gradcam_"))
    output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    header = f"{'file':<38}{'prediction':<34}{'conf':>7}{'severity':>10}{'verdict':>10}"
    print(header)
    print("-" * len(header))
    for index, image_path in enumerate(images):
        try:
            result = service.predict(
                image_path, output_dir=output_dir,
                explanation_stem=f"mine_{index:04d}_{image_path.stem}"[:80],
            )
        except Exception as exc:
            print(f"{image_path.name:<38}{'ERROR: ' + str(exc)[:40]:<34}")
            continue
        confidence = float(result["confidence"])
        verdict = "ACCEPT" if confidence >= args.threshold else "INSPECT"
        row = {
            "file": str(image_path),
            "label": result["label"],
            "display": result["display_label"],
            "crop": result["crop"],
            "healthy": result["is_healthy"],
            "confidence": round(confidence, 4),
            "severity": result["severity"],
            "verdict": verdict,
            "gradcam": result["gradcam_path"] or "",
        }
        rows.append(row)
        print(
            f"{image_path.name[:37]:<38}{result['display_label'][:33]:<34}"
            f"{confidence:>7.3f}{str(result['severity']):>10}{verdict:>10}"
        )

    accepted = sum(r["verdict"] == "ACCEPT" for r in rows)
    print(
        f"\nSummary: {accepted}/{len(rows)} accepted, "
        f"{len(rows) - accepted} sent to INSPECT, "
        f"mean confidence={sum(r['confidence'] for r in rows) / max(len(rows), 1):.3f}"
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["file"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"CSV: {args.out}")
    if args.gradcam_dir:
        print(f"Grad-CAM overlays: {args.gradcam_dir}")
    print("\nReminder: this is screening support, not a definitive diagnosis.")


if __name__ == "__main__":
    main()
