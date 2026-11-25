"""Prepare the public datasets used by AgriTwin.

Downloads:
  * India district-level crop production 1997-2015 (public data.world mirror)
  * Daily Agmarknet mandi price archive (CC BY 4.0 GitHub mirror of the
    Government of India OGD feed)

Outputs (committed, small curated slices):
  backend/app/data/crop_production.csv
  backend/app/data/historical_yield_sample.csv
  backend/app/data/market_prices.csv
  backend/app/data/DATASETS.md

Run from the repository root:
    python scripts/prepare_datasets.py
"""

from __future__ import annotations

import io
import json
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "backend" / "app" / "data"
CROP_URL = (
    "https://raw.githubusercontent.com/Vishnukurra101/crop-production-india/main/crop_production.csv"
)
MANDI_REPO_API = "https://api.github.com/repos/kunal-rajput-317/mandi-data/contents/data"
MANDI_RAW = "https://raw.githubusercontent.com/kunal-rajput-317/mandi-data/main"
MANDI_SNAPSHOT_URL = (
    "https://raw.githubusercontent.com/herrrickshaw/agri-commodity-tracker/main/"
    "data/mandi_prices_snapshot.csv"
)

CROP_MAP = {
    "rice": "Rice",
    "wheat": "Wheat",
    "maize": "Maize",
    "cotton": "Cotton",
    "cotton(lint)": "Cotton",
    "soyabean": "Soyabean",
    "soybean": "Soyabean",
    "groundnut": "Groundnut",
    "onion": "Onion",
    "tomato": "Tomato",
    "potato": "Potato",
    "sugarcane": "Sugarcane",
    "gram": "Chickpea",
    "bengal gram(gram)(whole)": "Chickpea",
    "chickpea": "Chickpea",
    "mustard": "Mustard",
    "rapeseed &mustard": "Mustard",
    "chilli": "Chilli",
    "green chilli": "Chilli",
    "dry chillies": "Chilli",
    "banana": "Banana",
}


def _get(url: str, timeout: int = 60) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "AgriTwin-dataset-prep/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def prepare_crop_production() -> None:
    target = DATA_DIR / "crop_production.csv"
    if not target.exists():
        print("Downloading crop production dataset ...")
        target.write_bytes(_get(CROP_URL, timeout=180))
    df = pd.read_csv(target)
    print(f"Crop production: {df.shape[0]:,} rows")

    df["Crop_norm"] = df["Crop"].astype(str).str.strip().str.lower().map(CROP_MAP)
    sample = df[(df["Crop_norm"].notna()) & (df["Crop_Year"] >= 2010)].copy()
    sample = sample.rename(
        columns={
            "State_Name": "state",
            "District_Name": "district",
            "Crop_Year": "year",
            "Season": "season",
            "Crop": "crop_raw",
            "Area": "area_hectares",
            "Production": "production_tonnes",
            "Crop_norm": "crop",
        }
    )
    sample["season"] = (
        sample["season"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map(
            {
                "kharif": "Kharif",
                "rabi": "Rabi",
                "summer": "Summer",
                "whole year": "Whole Year",
                "winter": "Rabi",
                "autumn": "Kharif",
            }
        )
    )
    sample = sample.dropna(subset=["season"])
    sample["state"] = sample["state"].astype(str).str.strip()
    sample["district"] = sample["district"].astype(str).str.strip()
    sample = sample[sample["area_hectares"] > 0]
    sample = sample[sample["production_tonnes"] > 0]
    sample["yield_per_hectare"] = sample["production_tonnes"] * 10.0 / sample["area_hectares"]
    sample = sample[sample["yield_per_hectare"].between(0.3, 1500)]
    sample = sample.sample(n=min(3000, len(sample)), random_state=42).sort_values(
        ["state", "district", "crop", "year"]
    )
    sample["source"] = "india_crop_production_1997_2015"
    columns = [
        "state",
        "district",
        "crop",
        "season",
        "year",
        "area_hectares",
        "production_tonnes",
        "yield_per_hectare",
        "source",
    ]
    sample[columns].to_csv(DATA_DIR / "historical_yield_sample.csv", index=False)
    print(f"Historical yield sample: {len(sample):,} rows")


def _list_mandi_files() -> list[str]:
    files: list[str] = []
    for year, month in [(2026, 7), (2026, 8), (2026, 9), (2026, 10), (2026, 11)]:
        try:
            payload = json.loads(_get(f"{MANDI_REPO_API}/{year}/{month:02d}"))
        except Exception as exc:
            print(f"  month {year}-{month:02d} unavailable: {exc}")
            continue
        for item in payload:
            if item.get("name", "").endswith(".csv"):
                files.append(item["name"])
    return sorted(set(files))


def _download_mandi(name: str) -> pd.DataFrame | None:
    url = f"{MANDI_RAW}/data/{name[:4]}/{name[5:7]}/{name}"
    try:
        frame = pd.read_csv(io.BytesIO(_get(url, timeout=90)))
    except Exception as exc:
        print(f"  skip {name}: {exc}")
        return None
    frame["commodity_norm"] = (
        frame["commodity"].astype(str).str.strip().str.lower().map(CROP_MAP)
    )
    frame = frame[frame["commodity_norm"].notna()]
    if frame.empty:
        return None
    return frame[
        [
            "date",
            "state",
            "district",
            "market",
            "commodity",
            "commodity_norm",
            "variety",
            "grade",
            "min_price",
            "max_price",
            "modal_price",
        ]
    ]


def _load_mandi_snapshot() -> pd.DataFrame | None:
    """Larger CC BY 4.0 Agmarknet snapshot (July-August 2026)."""
    try:
        frame = pd.read_csv(io.BytesIO(_get(MANDI_SNAPSHOT_URL, timeout=180)))
    except Exception as exc:
        print(f"  snapshot unavailable: {exc}")
        return None
    frame = frame.rename(columns={"arrival_date": "date"})
    frame["commodity_norm"] = (
        frame["commodity"].astype(str).str.strip().str.lower().map(CROP_MAP)
    )
    frame = frame[frame["commodity_norm"].notna()]
    if frame.empty:
        return None
    return frame[
        [
            "date",
            "state",
            "district",
            "market",
            "commodity",
            "commodity_norm",
            "variety",
            "grade",
            "min_price",
            "max_price",
            "modal_price",
        ]
    ]


def prepare_market_prices() -> None:
    target = DATA_DIR / "market_prices.csv"
    if target.exists():
        print("Market price slice already exists; skipping download.")
        return
    files = _list_mandi_files()
    print(f"Downloading {len(files)} daily mandi files ...")
    frames: list[pd.DataFrame] = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        for frame in executor.map(_download_mandi, files):
            if frame is not None:
                frames.append(frame)
    snapshot = _load_mandi_snapshot()
    if snapshot is not None:
        print(f"Adding mandi snapshot: {len(snapshot):,} rows")
        frames.append(snapshot)
    if not frames:
        print("No market data downloaded; the app will run with an empty market table.")
        return
    df = pd.concat(frames, ignore_index=True)
    # The daily archive uses ISO dates while the snapshot uses dd/mm/yyyy.
    # ``dayfirst=True`` alone would mis-read ISO strings as year-day-month,
    # so parse each format explicitly.
    raw_dates = df["date"].astype(str).str.strip()
    iso = pd.to_datetime(raw_dates, format="%Y-%m-%d", errors="coerce")
    dmy = pd.to_datetime(raw_dates, format="%d/%m/%Y", errors="coerce")
    df["date"] = iso.fillna(dmy).dt.date
    for col in ["min_price", "max_price", "modal_price"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["date", "min_price", "max_price", "modal_price"])
    df = df[(df["modal_price"] > 0) & (df["min_price"] > 0)]
    df = df[df["min_price"] <= df["max_price"]]
    df = df[df["modal_price"].between(df["min_price"], df["max_price"])]

    # Keep the three markets with the most complete daily history per crop.
    selected: list[pd.DataFrame] = []
    for crop, group in df.groupby("commodity_norm"):
        counts = group.groupby("market")["date"].nunique().sort_values(ascending=False)
        markets = counts[counts >= 45].head(3).index.tolist()
        if not markets:
            markets = counts.head(2).index.tolist()
        subset = group[group["market"].isin(markets)]
        subset = (
            subset.groupby(
                ["date", "state", "district", "market", "commodity_norm", "variety", "grade"],
                as_index=False,
            )
            .agg(
                min_price=("min_price", "mean"),
                max_price=("max_price", "mean"),
                modal_price=("modal_price", "mean"),
            )
        )
        selected.append(subset)
        print(f"  {crop}: markets={markets}, rows={len(subset)}")
    out = pd.concat(selected, ignore_index=True)
    out = out.rename(columns={"date": "price_date", "commodity_norm": "crop"})
    out["unit"] = "INR/quintal"
    out["source"] = "agmarknet_archive_2026"
    out["state"] = out["state"].astype(str).str.strip()
    out["district"] = out["district"].astype(str).str.strip()
    out["market"] = out["market"].astype(str).str.strip()
    out["variety"] = out["variety"].fillna("Other").astype(str).str.strip().replace("", "Other")
    out["grade"] = out["grade"].fillna("FAQ").astype(str).str.strip().replace("", "FAQ")
    out = out.sort_values(["crop", "market", "price_date"])
    out[
        [
            "crop",
            "market",
            "state",
            "district",
            "variety",
            "grade",
            "price_date",
            "min_price",
            "max_price",
            "modal_price",
            "unit",
            "source",
        ]
    ].to_csv(target, index=False)
    print(f"Market price slice: {len(out):,} rows, {out['crop'].nunique()} crops")


def write_manifest() -> None:
    (DATA_DIR / "DATASETS.md").write_text(
        "# Bundled datasets\n\n"
        "These files are curated slices of public datasets. They are real observations,\n"
        "not synthetic values.\n\n"
        "## crop_production.csv\n\n"
        "- Source: India district-level crop production (1997-2015), public mirror of\n"
        "  `data.world/thatzprem/agriculture-india` (Kaggle `abhinand05/crop-production-in-india`).\n"
        "- Columns: state, district, year, season, crop, area (ha), production (tonnes).\n"
        "- Used for: yield-model training and historical yield records.\n\n"
        "## historical_yield_sample.csv\n\n"
        "- A 3,000-row sample of the above for 2010-2015 and the 14 supported crops.\n"
        "- Used for: regional yield comparisons in the UI and seed records.\n\n"
        "## market_prices.csv\n\n"
        "- Source: Agmarknet daily mandi prices, CC BY 4.0 archive maintained at\n"
        "  `github.com/kunal-rajput-317/mandi-data`, derived from the Government of India\n"
        "  Open Government Data feed (resource `9ef84268-d588-465a-a308-a864a43d0070`).\n"
        "- Scope: three markets per supported crop, daily observations from 2026-07 onward.\n"
        "- Prices are INR per quintal. Original source attribution is preserved in the\n"
        "  `source` column.\n"
        "- Limitation: the archive window is short (about four months); forecasts are\n"
        "  short-horizon and labelled experimental.\n\n"
        "## PlantVillage subset (not committed)\n\n"
        "- Source: `Hemg/new-plant-diseases-dataset` on Hugging Face (PlantVillage,\n"
        "  CC BY-SA / public research dataset).\n"
        "- The training script downloads a balanced subset; model weights are kept under\n"
        "  `backend/app/ml/artifacts/` and excluded from git by default.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    prepare_crop_production()
    prepare_market_prices()
    write_manifest()
    print("Dataset preparation complete.")
