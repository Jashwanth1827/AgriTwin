"""Measure crop-conditioned inference on the held-out PV and PD test splits.

The serving app already asks the user to select a farm crop.  This script asks
whether that external crop hint can improve the deployed classifier by softly
reweighting the 38 probabilities toward classes of the selected crop.  It uses
the exact ``apply_crop_prior`` helper called by serving, so evaluation and
deployment cannot drift.

"oracle" hints are derived from the true label and are therefore an upper bound.
The noisy settings simulate a wrong user selection by replacing the hint at the
given rate with a random other trained crop.

Usage
-----
  python ml/crop_health/evaluation/crop_prior_eval.py --device cuda
  python ml/crop_health/evaluation/crop_prior_eval.py --device cpu --wrong-rates 0,0.05
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
from datetime import datetime, timezone

import torch
from PIL import Image
from sklearn.metrics import precision_recall_fscore_support

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.ml.crop_health.labels import class_crop, supported_crops  # noqa: E402
from app.ml.crop_health.service import (  # noqa: E402
    apply_crop_prior,
    build_architecture,
    tta_probabilities,
)

DEFAULT_ARTIFACTS = REPO_ROOT / "backend/app/ml/artifacts/crop_health"
MANIFEST = REPO_ROOT / "ml/crop_health/data/field_robust/manifest_dedup.json"
DEFAULT_OUTPUT = (
    REPO_ROOT / "ml/crop_health/evaluation/tta/crop_prior_convnext_results.json"
)


def _parse_floats(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def _score(predictions: list[int], truths: list[int]) -> dict:
    precision, recall, f1, _ = precision_recall_fscore_support(
        truths, predictions, average="macro", zero_division=0
    )
    accuracy = sum(int(p == t) for p, t in zip(predictions, truths)) / len(truths)
    return {
        "accuracy": round(accuracy, 4),
        "precision_macro": round(float(precision), 4),
        "recall_macro": round(float(recall), 4),
        "f1_macro": round(float(f1), 4),
        "support": len(truths),
    }


def _noisy_hints(truths: list[int], classes: list[str], wrong_rate: float, seed: int) -> list[str]:
    all_crops = supported_crops()
    rng = random.Random(seed)
    hints: list[str] = []
    for index in truths:
        true_crop = class_crop(classes[index])
        alternatives = [crop for crop in all_crops if crop != true_crop]
        if wrong_rate > 0 and rng.random() < wrong_rate and alternatives:
            hints.append(rng.choice(alternatives))
        else:
            hints.append(true_crop)
    return hints


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=pathlib.Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--manifest", type=pathlib.Path, default=MANIFEST)
    parser.add_argument("--views", type=int, default=4)
    parser.add_argument("--alphas", default="0,0.75,0.9,0.95,1.0")
    parser.add_argument("--wrong-rates", default="0,0.05,0.1,0.2")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    alphas = _parse_floats(args.alphas)
    wrong_rates = _parse_floats(args.wrong_rates)
    device = torch.device(args.device)

    metadata = json.loads((args.artifact_dir / "metadata.json").read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    classes = metadata["classes"]
    model = build_architecture(metadata["architecture"], len(classes))
    model.load_state_dict(
        torch.load(args.artifact_dir / "model.pt", map_location="cpu", weights_only=True)
    )
    model = model.to(device).eval()

    saved: dict = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "artifact": str(args.artifact_dir),
        "manifest": str(args.manifest),
        "model_version": metadata.get("version"),
        "views": args.views,
        "device": str(device),
        "alphas": alphas,
        "wrong_rates": wrong_rates,
        "note": (
            "Oracle hints use the true crop label; noisy hints simulate a wrong "
            "user crop selection. Metrics use the serving apply_crop_prior helper."
        ),
        "domains": {},
    }

    for domain in ("pd", "pv"):
        entries = [
            entry
            for entry in manifest["entries"]
            if entry["domain"] == domain and entry["split"] == "test"
        ]
        probabilities: list[torch.Tensor] = []
        truths: list[int] = []
        for entry in entries:
            with Image.open(REPO_ROOT / entry["path"]) as image:
                probs, _ = tta_probabilities(
                    model, metadata, image.convert("RGB"), args.views, device
                )
            probabilities.append(probs)
            truths.append(int(entry["label_index"]))

        saved["domains"][domain] = {}
        for wrong_rate in wrong_rates:
            hints = _noisy_hints(truths, classes, wrong_rate, seed=42)
            rows: list[dict] = []
            for alpha in alphas:
                predictions = [
                    int(
                        apply_crop_prior(prob, classes, hint, alpha)[0].argmax()
                    )
                    for prob, hint in zip(probabilities, hints)
                ]
                rows.append({"alpha": alpha, **_score(predictions, truths)})
            saved["domains"][domain][f"wrong_{wrong_rate:g}"] = rows
            baseline = next(row for row in rows if row["alpha"] == 0)
            print(f"{domain} wrong={wrong_rate:g}: " + "  ".join(
                f"a={row['alpha']:g} acc={row['accuracy']:.4f}" for row in rows
            ))
            print(
                "  best="
                f"{max(rows, key=lambda row: row['accuracy'])['accuracy']:.4f}; "
                f"baseline={baseline['accuracy']:.4f}"
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(saved, indent=2), encoding="utf-8")
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
