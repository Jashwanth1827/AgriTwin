"""Promote a v4 candidate only after matched-protocol TTA and crop-prior checks.

The v3 deployed model uses 4-view TTA and a soft crop prior. A raw training
candidate does not carry those serving settings, so this script merges them
forward after verifying that:

* the candidate class order is identical to the deployed one;
* the official PlantDoc test entries are byte-identical to the previous set;
* candidate unconstrained 4-view field accuracy strictly beats 0.7161;
* the crop prior was re-measured on the candidate with alpha=0.95.

Use without ``--apply`` for a dry run.

Usage
-----
    python ml/crop_health/evaluation/promote_candidate_v4.py \
        --candidate backend/app/ml/artifacts/crop_health_v4 \
        --tta-results ml/crop_health/evaluation/planttom/tta_4view_v4_results.json \
        --crop-prior-results ml/crop_health/evaluation/planttom/crop_prior_v4_results.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.ml.crop_health.service import CropHealthService  # noqa: E402

DEFAULT_DEPLOYED = REPO_ROOT / "backend/app/ml/artifacts/crop_health"
DEFAULT_BASE_MANIFEST = REPO_ROOT / "ml/crop_health/data/field_robust/manifest_dedup.json"
DEFAULT_CANDIDATE_MANIFEST = REPO_ROOT / "ml/crop_health/data/field_robust/manifest_planttom.json"
FULL_RESULTS = REPO_ROOT / "ml/crop_health/evaluation/cross_domain_results_all.json"
BACKUP_ROOT = Path(r"C:\Users\arvap\AppData\Local\Temp\opencode")
BASELINE_FIELD_TTA = 0.7161
EXPECTED_ALPHA = 0.95
EXPECTED_TEST_COUNT = 236


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"Required JSON not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def test_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [e for e in manifest["entries"] if e["split"] == "test"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--deployed", type=Path, default=DEFAULT_DEPLOYED)
    parser.add_argument("--tta-results", type=Path, required=True)
    parser.add_argument("--crop-prior-results", type=Path, required=True)
    parser.add_argument("--base-manifest", type=Path, default=DEFAULT_BASE_MANIFEST)
    parser.add_argument("--candidate-manifest", type=Path, default=DEFAULT_CANDIDATE_MANIFEST)
    parser.add_argument("--baseline-accuracy", type=float, default=BASELINE_FIELD_TTA)
    parser.add_argument("--min-delta", type=float, default=0.0)
    parser.add_argument("--backup-dir", type=Path, default=None)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    candidate = args.candidate.resolve()
    deployed = args.deployed.resolve()
    if candidate == deployed:
        raise SystemExit("Candidate and deployed artefact are the same directory.")

    current = read_json(deployed / "metadata.json")
    proposed = read_json(candidate / "metadata.json")
    tta = read_json(args.tta_results)
    prior = read_json(args.crop_prior_results)

    if proposed.get("classes") != current.get("classes"):
        raise SystemExit("REJECT — candidate class order differs from deployed class order.")
    if proposed.get("version") == current.get("version"):
        raise SystemExit("REJECT — candidate version is not newer than the deployed model.")

    base_tests = test_entries(read_json(args.base_manifest))
    candidate_tests = test_entries(read_json(args.candidate_manifest))
    if len(base_tests) != EXPECTED_TEST_COUNT or base_tests != candidate_tests:
        raise SystemExit("REJECT — official held-out test entries changed.")

    tta_record = (tta.get("domains") or {}).get("pd") or {}
    tta_metrics = tta_record.get("tta_metrics") or {}
    if int(tta.get("views", 0)) != 4:
        raise SystemExit("REJECT — TTA evidence is not the deployed 4-view protocol.")
    if int(tta_metrics.get("support", 0)) != EXPECTED_TEST_COUNT:
        raise SystemExit("REJECT — TTA evidence does not cover all 236 held-out field images.")
    if tta.get("model_version") != proposed.get("version"):
        raise SystemExit("REJECT — TTA evidence belongs to a different candidate version.")

    field = float(tta_metrics["accuracy"])
    single_view = float(tta_record["single_view_accuracy"])
    if int(prior.get("views", 0)) != 4:
        raise SystemExit("REJECT — crop-prior evidence is not the deployed 4-view protocol.")
    if prior.get("model_version") != proposed.get("version"):
        raise SystemExit("REJECT — crop-prior evidence belongs to a different candidate version.")
    if EXPECTED_ALPHA not in (prior.get("alphas") or []):
        raise SystemExit("REJECT — crop prior was not re-measured at alpha=0.95.")

    def prior_row(domain: str, wrong_rate: float, alpha: float) -> dict[str, Any]:
        rows = (prior.get("domains") or {}).get(domain, {}).get(f"wrong_{wrong_rate:g}", [])
        match = next((row for row in rows if float(row.get("alpha", -1)) == alpha), None)
        if match is None:
            raise SystemExit(
                f"REJECT — missing crop-prior evidence for {domain}, wrong={wrong_rate:g}, alpha={alpha:g}."
            )
        return match

    prior_results = {
        "field_baseline": prior_row("pd", 0.0, 0.0)["accuracy"],
        "field_correct_crop_hint": prior_row("pd", 0.0, EXPECTED_ALPHA)["accuracy"],
        "field_5pct_wrong_hint": prior_row("pd", 0.05, EXPECTED_ALPHA)["accuracy"],
        "field_10pct_wrong_hint": prior_row("pd", 0.1, EXPECTED_ALPHA)["accuracy"],
        "field_20pct_wrong_hint": prior_row("pd", 0.2, EXPECTED_ALPHA)["accuracy"],
        "lab_baseline": prior_row("pv", 0.0, 0.0)["accuracy"],
        "lab_correct_crop_hint": prior_row("pv", 0.0, EXPECTED_ALPHA)["accuracy"],
        "alpha": EXPECTED_ALPHA,
    }

    print("Current deployed (unconstrained TTA)")
    print(f"  version={current.get('version')} field={args.baseline_accuracy:.4f}")
    print("Candidate (unconstrained TTA)")
    print(f"  version={proposed.get('version')} field={field:.4f} single={single_view:.4f}")
    print(f"Field delta: {field - args.baseline_accuracy:+.4f}")
    print("Crop prior re-measurement")
    for key in (
        "field_baseline", "field_correct_crop_hint", "field_5pct_wrong_hint",
        "field_10pct_wrong_hint", "field_20pct_wrong_hint", "lab_correct_crop_hint",
    ):
        if key in prior_results:
            print(f"  {key}={prior_results[key]}")

    if field - args.baseline_accuracy <= args.min_delta:
        print("DECISION: REJECT — unconstrained field accuracy did not strictly improve. "
              "Deployed artefact unchanged.")
        return

    print(f"Held-out set: {len(base_tests)} test entries identical to previous protocol.")
    print("Class order: identical.")
    print("DECISION: PROMOTE" + (" (dry run)" if not args.apply else ""))
    if not args.apply:
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup = args.backup_dir or (BACKUP_ROOT / f"crop_health_backup_v4_{timestamp}")
    backup.mkdir(parents=True, exist_ok=False)
    for name in ("model.pt", "metadata.json"):
        source = deployed / name
        if source.exists():
            shutil.copy2(source, backup / name)
    print(f"Backup written to {backup}")

    single_view_metrics = dict(proposed.get("metrics") or {})
    merged = dict(proposed)
    merged["version"] = proposed["version"]
    merged["metrics"] = {
        **tta_metrics,
        "source": relative(args.tta_results),
        "view_description": tta.get("view_description"),
    }
    merged["single_view_metrics"] = single_view_metrics
    merged["tta_views"] = 4
    merged["tta_validation"] = {
        "source": relative(args.tta_results),
        "device": tta.get("device"),
        "gpu_result": tta_metrics,
        "baseline_unconstrained_accuracy": args.baseline_accuracy,
        "decision": (
            f"Promoted because unconstrained field accuracy improved from "
            f"{args.baseline_accuracy:.4f} to {field:.4f} on the unchanged held-out set."
        ),
    }
    merged["crop_prior_alpha"] = EXPECTED_ALPHA
    merged["crop_prior_validation"] = {
        "source": relative(args.crop_prior_results),
        **prior_results,
        "decision": "Re-measured after v4 training; soft prior retained as a serving option.",
    }

    if FULL_RESULTS.exists():
        full = read_json(FULL_RESULTS)
        if len(full.get("summary", [])) == 4:
            merged["cross_domain_summary"] = full["summary"]
            merged["cross_domain_summary_source"] = relative(FULL_RESULTS)

    merged["deployed_model_rerun"] = {
        "source": relative(candidate),
        "summary": [{
            "experiment": proposed.get("training_mode"),
            "pv_accuracy": float(
                ((proposed.get("evaluation_by_domain") or {}).get("pv") or {})
                .get("metrics", {}).get("accuracy", 0.0)
            ),
            "pd_accuracy_single_view": single_view,
            "pd_accuracy_tta_4view": field,
        }],
        "explanation": (
            "Promoted after a strict improvement in unconstrained 4-view field accuracy "
            "on the unchanged held-out PlantDoc set; crop prior re-measured separately."
        ),
    }
    merged["notes"] = (
        "Field-robust ConvNeXt-Tiny trained with PlantVillage + PlantDoc + deduplicated "
        "PlantTom images. Serving applies 4-view TTA and a separately measured soft crop "
        "prior. Results are screening support, not a definitive diagnosis."
    )

    shutil.copy2(candidate / "model.pt", deployed / "model.pt")
    (deployed / "metadata.json").write_text(
        json.dumps(merged, indent=2) + "\n", encoding="utf-8"
    )

    info = CropHealthService(deployed).info()
    if not info.get("available"):
        raise SystemExit(f"POST-DEPLOY CHECK FAILED: {info.get('message')}")
    if info.get("model_version") != proposed.get("version"):
        raise SystemExit("POST-DEPLOY CHECK FAILED: wrong model version after swap.")
    if float(info.get("crop_prior_alpha", -1)) != EXPECTED_ALPHA:
        raise SystemExit("POST-DEPLOY CHECK FAILED: crop prior alpha was not preserved.")
    print(f"POST-DEPLOY CHECK OK: {info['model_version']}")
    print(f"DECISION: PROMOTED. Field TTA {args.baseline_accuracy:.4f} -> {field:.4f}.")


if __name__ == "__main__":
    main()
