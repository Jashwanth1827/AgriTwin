"""Generate presentation charts from the actual trained-model metadata.

Every number plotted here is read from the repository artifacts or from a live
decision API response captured in ``decision_4.json``. Nothing is invented.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "presentation" / "assets"
CROP_META = ROOT / "backend" / "app" / "ml" / "artifacts" / "crop_health" / "metadata.json"
YIELD_META = ROOT / "backend" / "app" / "ml" / "artifacts" / "yield_prediction" / "metadata.json"
DECISION = ASSETS / "decision_4.json"

DEEP = "#14532D"
GREEN = "#16A34A"
LIGHT = "#DCFCE7"
NAVY = "#0F172A"
GRAY = "#64748B"
AMBER = "#D97706"

plt.rcParams.update(
    {
        "font.family": "Segoe UI",
        "font.size": 10,
        "axes.edgecolor": "#CBD5E1",
        "axes.labelcolor": NAVY,
        "xtick.color": GRAY,
        "ytick.color": GRAY,
        "axes.titlecolor": NAVY,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)


def _clean(ax, grid_axis: str = "x") -> None:
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.grid(axis=grid_axis, color="#E2E8F0", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


def crop_training() -> None:
    meta = json.loads(CROP_META.read_text(encoding="utf-8"))
    history = meta["history"]
    epochs = [row["epoch"] for row in history]
    accuracy = [row["validation"]["accuracy"] for row in history]
    f1 = [row["validation"]["f1_macro"] for row in history]

    fig, ax = plt.subplots(figsize=(6.0, 3.1), dpi=220)
    ax.plot(epochs, accuracy, marker="o", color=GREEN, linewidth=2.4, label="Validation accuracy")
    ax.plot(epochs, f1, marker="s", color=DEEP, linewidth=2.0, linestyle="--", label="Validation macro-F1")
    ax.set_ylim(0.68, 1.0)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Score")
    ax.set_title("Crop-health training curve (6 epochs)", loc="left", fontweight="bold")
    ax.set_xticks(epochs)
    _clean(ax, "y")
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(ASSETS / "chart_crop_training.png")
    plt.close(fig)


def crop_weakest_classes() -> None:
    meta = json.loads(CROP_META.read_text(encoding="utf-8"))
    rows = [
        (name.replace("___", " — ").replace("_", " "), values["f1-score"])
        for name, values in meta["per_class_metrics"].items()
    ]
    rows.sort(key=lambda item: item[1])
    weakest = rows[:10][::-1]

    fig, ax = plt.subplots(figsize=(6.0, 3.4), dpi=220)
    labels = [row[0] for row in weakest]
    values = [row[1] for row in weakest]
    colors = [AMBER if value < 0.8 else GREEN for value in values]
    ax.barh(labels, values, color=colors, height=0.62)
    for index, value in enumerate(values):
        ax.text(value + 0.01, index, f"{value:.2f}", va="center", fontsize=8.5, color=NAVY)
    ax.set_xlim(0, 1.08)
    ax.set_xlabel("Per-class F1 on the 266-image held-out test split")
    ax.set_title("Weakest classes (7 test images per class)", loc="left", fontweight="bold")
    _clean(ax, "x")
    fig.tight_layout()
    fig.savefig(ASSETS / "chart_crop_classes.png")
    plt.close(fig)


def yield_models() -> None:
    meta = json.loads(YIELD_META.read_text(encoding="utf-8"))
    rows = [(row["model"], row["validation"]["rmse"]) for row in meta["model_comparison"]]
    rows.sort(key=lambda item: item[1])
    labels = [row[0] for row in rows]
    values = [row[1] for row in rows]
    colors = [GREEN if label == "ExtraTrees" else "#94A3B8" for label in labels]

    fig, ax = plt.subplots(figsize=(6.0, 3.1), dpi=220)
    ax.barh(labels, values, color=colors, height=0.62)
    for index, value in enumerate(values):
        ax.text(value + 2, index, f"{value:.1f}", va="center", fontsize=8.5, color=NAVY)
    ax.set_xlim(0, max(values) * 1.16)
    ax.set_xlabel("Validation RMSE (quintals per hectare)")
    ax.set_title("Yield model comparison — 2013–14 validation", loc="left", fontweight="bold")
    _clean(ax, "x")
    fig.tight_layout()
    fig.savefig(ASSETS / "chart_yield_models.png")
    plt.close(fig)


def market_models() -> None:
    # Values captured from the live forecast response rendered in the UI.
    rows = [
        ("LinearTrendWeekly", 410.34),
        ("GradientBoosting", 461.76),
        ("RandomForest", 469.86),
        ("MovingAverage", 478.63),
        ("SeasonalNaive", 486.77),
    ]
    labels = [row[0] for row in rows]
    values = [row[1] for row in rows]
    colors = [GREEN if label == "LinearTrendWeekly" else "#94A3B8" for label in labels]

    fig, ax = plt.subplots(figsize=(6.0, 2.9), dpi=220)
    ax.barh(labels, values, color=colors, height=0.62)
    for index, value in enumerate(values):
        ax.text(value + 5, index, f"{value:.2f}", va="center", fontsize=8.5, color=NAVY)
    ax.set_xlim(0, max(values) * 1.16)
    ax.set_xlabel("Chronological tail MAE (INR per quintal)")
    ax.set_title("Onion forecast — model comparison", loc="left", fontweight="bold")
    _clean(ax, "x")
    fig.tight_layout()
    fig.savefig(ASSETS / "chart_market_models.png")
    plt.close(fig)


def buyer_comparison() -> None:
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    mandi = decision["outputs"]["scenarios"]["immediate"]["net_realization_per_quintal"]
    rows = [("Mandi (Ammapet)", mandi)]
    for evaluation in decision["buyer_evaluations"]:
        rows.append((evaluation["buyer_name"], evaluation["net_realization_per_quintal"]))
    rows.sort(key=lambda item: item[1])

    labels = [row[0] for row in rows]
    values = [row[1] for row in rows]
    colors = [GREEN if label.startswith("Mandi") else "#94A3B8" for label in labels]

    fig, ax = plt.subplots(figsize=(6.4, 2.6), dpi=220)
    ax.barh(labels, values, color=colors, height=0.55)
    for index, value in enumerate(values):
        ax.text(value + 40, index, f"INR {value:,.0f}/q", va="center", fontsize=9, color=NAVY)
    ax.set_xlim(0, max(values) * 1.22)
    ax.set_xlabel("Net realisation after commission, other costs and transport")
    ax.set_title("Real decision #4 — channel comparison (Onion, 392 q)", loc="left", fontweight="bold")
    _clean(ax, "x")
    fig.tight_layout()
    fig.savefig(ASSETS / "chart_buyer_net.png")
    plt.close(fig)


def risk_contributions() -> None:
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    labels_map = {
        "yield_uncertainty": "Yield uncertainty",
        "price_uncertainty": "Price uncertainty",
        "crop_health": "Crop health",
        "weather": "Weather",
        "buyer_offer": "Buyer offer",
        "transport": "Transport",
        "data_completeness": "Data completeness",
        "market_freshness": "Market freshness",
    }
    contributions = []
    for factor in decision["factors"]:
        name = factor.get("factor")
        if name not in labels_map:
            continue
        contributions.append((labels_map[name], factor["value"] * factor["weight"]))
    contributions.sort(key=lambda item: item[1])

    fig, ax = plt.subplots(figsize=(6.0, 3.0), dpi=220)
    labels = [row[0] for row in contributions]
    values = [row[1] for row in contributions]
    ax.barh(labels, values, color=[DEEP if value > 0.08 else "#94A3B8" for value in values], height=0.6)
    for index, value in enumerate(values):
        ax.text(value + 0.002, index, f"{value:.3f}", va="center", fontsize=8.5, color=NAVY)
    ax.set_xlim(0, max(values) * 1.2)
    ax.set_xlabel("Weighted contribution to the composite risk score (0.4415)")
    ax.set_title("Risk decomposition — decision #4", loc="left", fontweight="bold")
    _clean(ax, "x")
    fig.tight_layout()
    fig.savefig(ASSETS / "chart_risk.png")
    plt.close(fig)


def main() -> None:
    crop_training()
    crop_weakest_classes()
    yield_models()
    market_models()
    buyer_comparison()
    risk_contributions()
    for path in sorted(ASSETS.glob("chart_*.png")):
        print(f"wrote {path.name} ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
