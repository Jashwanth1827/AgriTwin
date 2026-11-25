"""Measure whether test-time augmentation improves field accuracy (no retraining).

Compares single-view inference against averaging several views of the same photo.
Run this before enabling TTA in the serving layer so any gain is measured, not assumed.

Usage
-----
  python ml/crop_health/evaluation/tta_eval.py
  python ml/crop_health/evaluation/tta_eval.py --artifact-dir <dir> --views 4
"""

from __future__ import annotations

import argparse
import json
import pathlib
from datetime import datetime, timezone
import sys
from pathlib import Path

import torch
from PIL import Image
from sklearn.metrics import precision_recall_fscore_support

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.ml.crop_health.service import build_architecture, tta_view_probabilities  # noqa: E402

DEFAULT_ARTIFACTS = REPO_ROOT / "backend/app/ml/artifacts/crop_health"
MANIFEST = REPO_ROOT / "ml/crop_health/data/field_robust/manifest.json"


def build(model: torch.nn.Module, model_meta: dict, views: int, device: torch.device):
    """Use the serving implementation so evaluation and inference cannot drift."""

    def views_for(image: Image.Image) -> list[torch.Tensor]:
        probabilities, _ = tta_view_probabilities(
            model, model_meta, image, views, device
        )
        return probabilities

    return views_for


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--manifest", type=Path, default=MANIFEST,
                        help="split manifest (use manifest_dedup.json for leakage-free splits)")
    parser.add_argument("--views", type=int, choices=[1, 2, 4], default=2)
    parser.add_argument("--domain", choices=["pd", "pv", "both"], default="pd")
    parser.add_argument("--detail", action="store_true", help="break gains down by confidence")
    parser.add_argument("--output", type=Path, default=None, help="save machine-readable results JSON")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto",
                        help="evaluation device (auto uses CUDA when it is usable)")
    args = parser.parse_args()

    meta = json.loads((args.artifact_dir / "metadata.json").read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.device == "cuda" or (args.device == "auto" and torch.cuda.is_available()):
        device = torch.device("cuda")
        try:
            probe = torch.ones(1, device=device)
            _ = (probe * probe).item()
        except Exception:
            device = torch.device("cpu")
    else:
        device = torch.device("cpu")
    model = build_architecture(meta["architecture"], len(meta["classes"]))
    model.load_state_dict(torch.load(args.artifact_dir / "model.pt", map_location="cpu", weights_only=True))
    model = model.to(device)
    model.eval()
    views_for = build(model, meta, args.views, device)

    domains = ("pd", "pv") if args.domain == "both" else (args.domain,)
    if args.views <= 1:
        description = "original only"
    elif args.views == 2:
        description = "original + horizontal flip"
    else:
        description = "original + horizontal flip at scales 1.0 and 0.9"
    saved: dict = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "artifact": str(args.artifact_dir),
        "model_version": meta.get("version"),
        "views": args.views,
        "view_description": f"{description} ({args.views} view(s)); first view is baseline",
        "device": str(device),
        "domains": {},
    }
    for domain in domains:
        items = [e for e in manifest["entries"] if e["domain"] == domain and e["split"] == "test"]
        base_correct = tta_correct = 0
        detail: list[tuple[float, bool, bool]] = []
        y_true: list[int] = []
        y_tta: list[int] = []
        for entry in items:
            with Image.open(REPO_ROOT / entry["path"]) as image:
                probs = views_for(image.convert("RGB"))
            base = int(probs[0].argmax())
            ensemble = int(torch.stack(probs).mean(dim=0).argmax())
            base_ok = base == entry["label_index"]
            tta_ok = ensemble == entry["label_index"]
            base_correct += int(base_ok)
            tta_correct += int(tta_ok)
            detail.append((float(probs[0].max()), base_ok, tta_ok))
            y_true.append(int(entry["label_index"]))
            y_tta.append(ensemble)
        n = len(items)
        print(
            f"{domain}: n={n}  single={base_correct / n:.4f}  "
            f"tta({args.views})={tta_correct / n:.4f}  "
            f"delta={(tta_correct - base_correct) / n:+.4f}"
        )
        record: dict = {
            "n": n,
            "single_view_accuracy": round(base_correct / n, 4),
            f"tta_{args.views}_view_accuracy": round(tta_correct / n, 4),
            "delta": round((tta_correct - base_correct) / n, 4),
            "net_correct_images": tta_correct - base_correct,
        }
        if args.detail:
            gained = sum(1 for _, b, t in detail if not b and t)
            lost = sum(1 for _, b, t in detail if b and not t)
            low = [d for d in detail if d[0] < 0.55]
            high = [d for d in detail if d[0] >= 0.55]
            print(f"  flips: fixed={gained} broken={lost}")
            record["flips_fixed"] = gained
            record["flips_broken"] = lost
            for label, group in (("low_confidence", low), ("high_confidence", high)):
                if group:
                    b = sum(d[1] for d in group) / len(group)
                    t = sum(d[2] for d in group) / len(group)
                    print(f"  {label}: n={len(group)} single={b:.4f} tta={t:.4f} delta={t - b:+.4f}")
                    record[label] = {
                        "n": len(group),
                        "single_view_accuracy": round(b, 4),
                        "tta_accuracy": round(t, 4),
                        "delta": round(t - b, 4),
                    }
        # Match train_field_robust.evaluate(): macro averages over classes that
        # actually appear in y_true/y_pred, not the 11 unseen PlantDoc classes.
        labels = sorted(set(y_true) | set(y_tta))
        macro = precision_recall_fscore_support(
            y_true, y_tta, labels=labels, average="macro", zero_division=0
        )
        weighted = precision_recall_fscore_support(
            y_true, y_tta, labels=labels, average="weighted", zero_division=0
        )
        record["tta_metrics"] = {
            "accuracy": round(tta_correct / n, 4),
            "precision_macro": round(float(macro[0]), 4),
            "recall_macro": round(float(macro[1]), 4),
            "f1_macro": round(float(macro[2]), 4),
            "f1_weighted": round(float(weighted[2]), 4),
            "support": n,
            "views": args.views,
        }
        saved["domains"][domain] = record

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(saved, indent=2) + "\n", encoding="utf-8")
        print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
