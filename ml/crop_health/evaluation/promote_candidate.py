"""Safely promote a trained candidate to the deployed crop-health artefact.

A candidate is promoted only when its measured PlantDoc (field) accuracy is strictly
greater than the currently deployed artefact's. Lab accuracy is reported but never
used as the promotion criterion: the whole point of the cross-domain study is to
avoid optimising for the controlled domain.

The script never deletes anything: the current artefact is copied to a timestamped
backup before the candidate weights are installed. Use --apply to perform the swap;
without it the script only prints a decision report.

Usage
-----
  python ml/crop_health/evaluation/promote_candidate.py \
      --candidate backend/app/ml/artifacts/crop_health_candidate

  python ml/crop_health/evaluation/promote_candidate.py \
      --candidate backend/app/ml/artifacts/crop_health_exg --apply
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.ml.crop_health.service import CropHealthService  # noqa: E402

DEFAULT_DEPLOYED = REPO_ROOT / "backend/app/ml/artifacts/crop_health"
FULL_RESULTS = REPO_ROOT / "ml/crop_health/evaluation/cross_domain_results_all.json"
BACKUP_ROOT = Path(r"C:\Users\arvap\AppData\Local\Temp\opencode")


def read_metadata(artifact: Path) -> dict:
    path = artifact / "metadata.json"
    if not path.exists():
        raise SystemExit(f"metadata.json missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def field_accuracy(metadata: dict) -> float:
    metrics = metadata.get("metrics") or {}
    value = metrics.get("accuracy")
    if value is None:
        raise SystemExit("metadata has no metrics.accuracy; cannot compare candidates")
    return float(value)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--deployed", type=Path, default=DEFAULT_DEPLOYED)
    parser.add_argument("--min-delta", type=float, default=0.0,
                        help="minimum field-accuracy improvement required (default: any)")
    parser.add_argument("--backup-dir", type=Path, default=None)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    candidate = args.candidate.resolve()
    deployed = args.deployed.resolve()
    if candidate == deployed:
        raise SystemExit("Candidate and deployed artefact are the same directory.")

    current = read_metadata(deployed)
    proposed = read_metadata(candidate)
    current_pd, proposed_pd = field_accuracy(current), field_accuracy(proposed)

    def lab_accuracy(metadata: dict) -> float:
        by_domain = metadata.get("evaluation_by_domain") or {}
        pv = (by_domain.get("pv") or {}).get("metrics") or {}
        return float(pv.get("accuracy", 0.0))

    print("Current deployed artefact")
    print(f"  version={current.get('version')} mode={current.get('training_mode')}")
    print(f"  field={current_pd:.4f} lab={lab_accuracy(current):.4f}")
    print("Candidate artefact")
    print(f"  version={proposed.get('version')} mode={proposed.get('training_mode')}")
    print(f"  field={proposed_pd:.4f} lab={lab_accuracy(proposed):.4f}")

    delta = proposed_pd - current_pd
    print(f"Field delta: {delta:+.4f}")
    if delta <= args.min_delta:
        print(f"DECISION: REJECT — improvement must exceed {args.min_delta:+.4f}. "
              "Deployed artefact unchanged.")
        return

    # Extra guard: the candidate's class order must be byte-identical to the deployed one.
    if proposed.get("classes") != current.get("classes"):
        raise SystemExit("REJECT — candidate class order differs from the deployed artefact.")
    print("Class order: identical (38 classes).")

    if not args.apply:
        print("DECISION: PROMOTE (dry run). Re-run with --apply to install.")
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup = args.backup_dir or (BACKUP_ROOT / f"crop_health_backup_{timestamp}")
    backup.mkdir(parents=True, exist_ok=False)
    for name in ("model.pt", "metadata.json"):
        source = deployed / name
        if source.exists():
            shutil.copy2(source, backup / name)
    print(f"Backup written to {backup}")

    # Install candidate weights.
    shutil.copy2(candidate / "model.pt", deployed / "model.pt")

    # Install candidate metadata but preserve the authoritative four-experiment table.
    metadata = dict(proposed)
    if FULL_RESULTS.exists():
        full = json.loads(FULL_RESULTS.read_text(encoding="utf-8"))
        if len(full.get("summary", [])) == 4:
            metadata["cross_domain_summary"] = full["summary"]
            metadata["cross_domain_summary_source"] = str(
                FULL_RESULTS.relative_to(REPO_ROOT)
            )
    metadata["deployed_model_rerun"] = {
        "source": str(candidate.relative_to(REPO_ROOT)) if candidate.is_relative_to(REPO_ROOT) else str(candidate),
        "summary": [{
            "experiment": proposed.get("training_mode"),
            "pv_accuracy": lab_accuracy(proposed),
            "pd_accuracy": proposed_pd,
        }],
        "explanation": (
            "Deployed checkpoint promoted after a measured field-accuracy improvement over "
            "the previous artefact; see the candidate evaluation directory for full metrics."
        ),
    }
    metadata["notes"] = (
        "Field-robust model selected by PlantDoc test accuracy. Lab and field metrics are "
        "reported separately; results are screening support, not a definitive diagnosis."
    )
    (deployed / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    service = CropHealthService(deployed)
    info = service.info()
    if not info.get("available"):
        raise SystemExit(f"POST-DEPLOY CHECK FAILED: {info.get('message')}")
    print(f"POST-DEPLOY CHECK OK: {info['model_version']} (mode={info['mode']})")
    print(f"DECISION: PROMOTED. Field accuracy {current_pd:.4f} -> {proposed_pd:.4f}.")


if __name__ == "__main__":
    main()
