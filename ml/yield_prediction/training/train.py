"""Train and evaluate the AgriTwin yield model.

Usage (from the repository root):
    python ml/yield_prediction/training/train.py --csv path/to/crop_production.csv

The script is intentionally reproducible: fixed seed, chronological split and
all preprocessing fitted only on the training period.  Metrics written to
``metadata.json`` are produced on a held-out future year and are never
hand-written.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import (
    ExtraTreesRegressor,
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.ml.yield_prediction.features import (  # noqa: E402
    FEATURE_COLUMNS,
    YieldFeatureBuilder,
    add_expanding_history_features,
    clean_training_frame,
)

DEFAULT_CSV = REPO_ROOT / "backend" / "app" / "data" / "crop_production.csv"
DEFAULT_ARTIFACT_DIR = REPO_ROOT / "backend" / "app" / "ml" / "artifacts" / "yield_prediction"
MODEL_VERSION = "yield-v1.0.0"


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = y_true != 0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
        "r2": round(float(r2_score(y_true, y_pred)), 4),
        "mape_pct": round(mape(y_true, y_pred), 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--train-sample", type=int, default=80000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if not args.csv.exists():
        raise SystemExit(f"Training CSV not found: {args.csv}")

    print(f"Loading {args.csv} ...")
    raw = pd.read_csv(args.csv)
    df = clean_training_frame(raw)
    print(f"Clean rows: {len(df):,}; crops: {df['crop'].nunique()}; years: {df['year'].min()}-{df['year'].max()}")

    train = df[df["year"] <= 2012].copy()
    val = df[(df["year"] >= 2013) & (df["year"] <= 2014)].copy()
    test = df[df["year"] >= 2015].copy()
    if len(train) > args.train_sample:
        train = train.sample(n=args.train_sample, random_state=args.seed)
    train = add_expanding_history_features(train)
    print(f"Train {len(train):,} | Val {len(val):,} | Test {len(test):,}")

    builder = YieldFeatureBuilder().fit(train)
    val = builder.add_history_features(val)
    test = builder.add_history_features(test)
    x_train, y_train = builder.transform(train), train["yield_q_per_ha"].to_numpy()
    x_val, y_val = builder.transform(val), val["yield_q_per_ha"].to_numpy()
    x_test, y_test = builder.transform(test), test["yield_q_per_ha"].to_numpy()

    candidates = {
        "DummyMean": DummyRegressor(strategy="mean"),
        "RandomForest": RandomForestRegressor(
            n_estimators=70, min_samples_leaf=2, n_jobs=-1, random_state=args.seed
        ),
        "ExtraTrees": ExtraTreesRegressor(
            n_estimators=70, min_samples_leaf=2, n_jobs=-1, random_state=args.seed
        ),
        "HistGradientBoosting": HistGradientBoostingRegressor(
            max_iter=250, learning_rate=0.08, random_state=args.seed
        ),
        "GradientBoosting": GradientBoostingRegressor(
            n_estimators=150, max_depth=3, random_state=args.seed
        ),
    }

    comparison: list[dict] = []
    fitted: dict[str, object] = {}
    for name, model in candidates.items():
        print(f"Training {name} ...")
        model.fit(x_train, y_train)
        val_metrics = metrics(y_val, model.predict(x_val))
        comparison.append({"model": name, "validation": val_metrics})
        fitted[name] = model
        print(f"  validation RMSE={val_metrics['rmse']} MAE={val_metrics['mae']}")

    comparison.sort(key=lambda item: item["validation"]["rmse"])
    best_name = comparison[0]["model"]
    best_model = fitted[best_name]
    print(f"Selected {best_name}")

    # Split-conformal calibration on the validation period (80% interval).
    val_pred = best_model.predict(x_val)
    residuals = np.abs(y_val - val_pred)
    conformal_half_width = float(np.quantile(residuals, 0.8))
    test_pred_before = best_model.predict(x_test)
    test_coverage_before = float(
        np.mean(np.abs(y_test - test_pred_before) <= conformal_half_width)
    )

    # Refit the selected model on train + validation for the final artifact.
    train_val = pd.concat([train, val], ignore_index=True)
    builder_final = YieldFeatureBuilder().fit(train_val)
    test_final = builder_final.add_history_features(test)
    x_train_val = builder_final.transform(train_val)
    x_test_final = builder_final.transform(test_final)

    final_model = _clone_model(best_name, args.seed)
    print("Refitting final model on train+validation ...")
    final_model.fit(x_train_val, train_val["yield_q_per_ha"].to_numpy())
    test_pred = final_model.predict(x_test_final)

    test_metrics = metrics(y_test, test_pred)
    test_coverage = float(np.mean(np.abs(y_test - test_pred) <= conformal_half_width))
    test_metrics["interval_coverage"] = round(test_coverage, 4)
    test_metrics["interval_half_width_q_per_ha"] = round(conformal_half_width, 4)
    test_metrics["interval_nominal_coverage"] = 0.8

    metadata = {
        "version": MODEL_VERSION,
        "model_name": best_name,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "dataset_provenance": (
            "India district-level crop production dataset (1997-2015), public mirror of "
            "data.world/thatzprem/agriculture-india. Production interpreted as tonnes; "
            "yield = production_tonnes * 10 / area_ha."
        ),
        "split": {
            "train": "years <= 2012",
            "validation": "2013-2014 (conformal calibration)",
            "test": "2015 (held-out future year)",
        },
        "training_rows": int(len(train)),
        "validation_rows": int(len(val)),
        "test_rows": int(len(test)),
        "features": FEATURE_COLUMNS,
        "metrics": test_metrics,
        "validation_metrics": comparison[0]["validation"],
        "model_comparison": comparison,
        "interval_method": "split_conformal_absolute_residual_q80",
        "is_experimental": True,
        "notes": (
            "Prediction intervals use split conformal calibration on 2013-2014. "
            "The model does not use soil or weather observations because the historical "
            "dataset has no paired soil/weather records. Metrics are from a held-out year "
            "and should not be read as a guarantee for an individual farm."
        ),
        "conformal_calibration_coverage": round(test_coverage_before, 4),
    }

    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model": final_model,
        "builder": builder_final,
        "metadata": metadata,
        "conformal_half_width": conformal_half_width,
    }
    joblib.dump(bundle, args.artifact_dir / "model.joblib")
    with (args.artifact_dir / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)

    print("\nFinal test metrics:")
    print(json.dumps(test_metrics, indent=2))
    print(f"Artifact written to {args.artifact_dir}")


def _clone_model(name: str, seed: int):
    if name == "RandomForest":
        return RandomForestRegressor(
            n_estimators=70, min_samples_leaf=2, n_jobs=-1, random_state=seed
        )
    if name == "ExtraTrees":
        return ExtraTreesRegressor(
            n_estimators=70, min_samples_leaf=2, n_jobs=-1, random_state=seed
        )
    if name == "HistGradientBoosting":
        return HistGradientBoostingRegressor(
            max_iter=250, learning_rate=0.08, random_state=seed
        )
    if name == "GradientBoosting":
        return GradientBoostingRegressor(n_estimators=150, max_depth=3, random_state=seed)
    return DummyRegressor(strategy="mean")


if __name__ == "__main__":
    main()
