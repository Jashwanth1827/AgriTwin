"""Feature engineering shared by yield-model training and inference.

The historical dataset is the public India district-level crop production
dataset (1997-2015).  ``Production`` is interpreted as tonnes and ``Area`` as
hectares; yield is converted to quintals per hectare (tonnes * 10 / hectares).
This interpretation was validated against agronomic plausibility for every
supported crop and is documented in docs/ML.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SUPPORTED_CROPS = [
    "Rice",
    "Wheat",
    "Maize",
    "Cotton",
    "Soyabean",
    "Groundnut",
    "Onion",
    "Tomato",
    "Potato",
    "Sugarcane",
    "Chickpea",
    "Mustard",
    "Chilli",
    "Banana",
]

CROP_ALIASES = {
    "rice": "Rice",
    "wheat": "Wheat",
    "maize": "Maize",
    "corn": "Maize",
    "cotton(lint)": "Cotton",
    "cotton": "Cotton",
    "soyabean": "Soyabean",
    "soybean": "Soyabean",
    "groundnut": "Groundnut",
    "onion": "Onion",
    "tomato": "Tomato",
    "potato": "Potato",
    "sugarcane": "Sugarcane",
    "gram": "Chickpea",
    "chickpea": "Chickpea",
    "rapeseed &mustard": "Mustard",
    "rapeseed & mustard": "Mustard",
    "mustard": "Mustard",
    "dry chillies": "Chilli",
    "chilli": "Chilli",
    "banana": "Banana",
}

SEASON_ALIASES = {
    "kharif": "Kharif",
    "rabi": "Rabi",
    "summer": "Summer",
    "whole year": "Whole Year",
    "winter": "Rabi",
    "autumn": "Kharif",
    "late kharif": "Late Kharif",
}

CATEGORICAL_FEATURES = ["crop", "season", "state"]
NUMERIC_FEATURES = [
    "area_ha",
    "log_area",
    "crop_state_hist_avg",
    "crop_hist_avg",
    "state_hist_avg",
]
FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERIC_FEATURES

MIN_VALID_YIELD = 0.3  # quintals/hectare
MAX_VALID_YIELD = 1500.0  # quintals/hectare (sugarcane/banana upper tail)


def _clean_text(value: Any) -> str:
    return " ".join(str(value).strip().split())


def clean_training_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalise, de-duplicate and validate the public production dataset."""
    required = {"State_Name", "District_Name", "Crop_Year", "Season", "Crop", "Area", "Production"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"Training CSV is missing columns: {sorted(missing)}")

    df = raw.copy()
    df["state"] = df["State_Name"].map(_clean_text)
    df["district"] = df["District_Name"].map(_clean_text)
    df["crop_raw"] = df["Crop"].map(_clean_text)
    df["crop"] = df["crop_raw"].str.lower().map(CROP_ALIASES)
    df["season"] = df["Season"].map(lambda v: SEASON_ALIASES.get(_clean_text(v).lower()))
    df["year"] = pd.to_numeric(df["Crop_Year"], errors="coerce")
    df["area_ha"] = pd.to_numeric(df["Area"], errors="coerce")
    df["production_tonnes"] = pd.to_numeric(df["Production"], errors="coerce")

    df = df.dropna(subset=["crop", "season", "year", "area_ha", "production_tonnes"])
    df = df[df["area_ha"] > 0]
    df = df[df["production_tonnes"] > 0]
    df["yield_q_per_ha"] = df["production_tonnes"] * 10.0 / df["area_ha"]
    df = df[(df["yield_q_per_ha"] >= MIN_VALID_YIELD) & (df["yield_q_per_ha"] <= MAX_VALID_YIELD)]

    # De-duplicate the natural key; inconsistent duplicates are averaged.
    grouped = (
        df.groupby(["state", "district", "crop", "season", "year"], as_index=False)
        .agg(
            area_ha=("area_ha", "sum"),
            production_tonnes=("production_tonnes", "sum"),
        )
        .reset_index(drop=True)
    )
    grouped["yield_q_per_ha"] = grouped["production_tonnes"] * 10.0 / grouped["area_ha"]
    grouped = grouped[
        (grouped["yield_q_per_ha"] >= MIN_VALID_YIELD)
        & (grouped["yield_q_per_ha"] <= MAX_VALID_YIELD)
    ]
    grouped["year"] = grouped["year"].astype(int)
    return grouped


def _smoothed_mean(sum_value: float, count: int, prior: float, strength: float = 10.0) -> float:
    return float((sum_value + strength * prior) / (count + strength))


@dataclass
class YieldFeatureBuilder:
    """Fitted feature builder persisted alongside the model artifact."""

    global_mean: float = 0.0
    crop_maps: dict[str, list[float]] = field(default_factory=dict)
    state_maps: dict[str, list[float]] = field(default_factory=dict)
    crop_state_maps: dict[str, list[float]] = field(default_factory=dict)
    preprocessor: ColumnTransformer | None = None
    feature_columns: list[str] = field(default_factory=lambda: list(FEATURE_COLUMNS))

    def fit(self, df: pd.DataFrame) -> "YieldFeatureBuilder":
        self.global_mean = float(df["yield_q_per_ha"].mean())
        self.crop_maps = _group_maps(df, ["crop"])
        self.state_maps = _group_maps(df, ["state"])
        self.crop_state_maps = _group_maps(df, ["crop", "state"])
        self.preprocessor = ColumnTransformer(
            transformers=[
                (
                    "cat",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                    CATEGORICAL_FEATURES,
                ),
                ("num", StandardScaler(), NUMERIC_FEATURES),
            ],
            remainder="drop",
        )
        frame = self._frame_from_rows(df.to_dict("records"))
        self.preprocessor.fit(frame)
        return self

    def _frame_from_rows(self, rows: list[dict[str, Any]]) -> pd.DataFrame:
        prepared = []
        for row in rows:
            prepared.append(
                {
                    "crop": row.get("crop", "Rice"),
                    "season": row.get("season", "Kharif"),
                    "state": row.get("state", "Maharashtra"),
                    "area_ha": float(row.get("area_ha") or 1.0),
                    "log_area": float(np.log1p(max(float(row.get("area_ha") or 1.0), 0.0))),
                    "crop_state_hist_avg": row.get("crop_state_hist_avg")
                    if row.get("crop_state_hist_avg") is not None
                    else self.global_mean,
                    "crop_hist_avg": row.get("crop_hist_avg")
                    if row.get("crop_hist_avg") is not None
                    else self.global_mean,
                    "state_hist_avg": row.get("state_hist_avg")
                    if row.get("state_hist_avg") is not None
                    else self.global_mean,
                }
            )
        return pd.DataFrame(prepared, columns=FEATURE_COLUMNS)

    def add_history_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Attach history features using maps fitted on the training period."""
        out = df.copy()
        out["crop_state_hist_avg"] = [
            _lookup(self.crop_state_maps, f"{c}|{s}", self.global_mean)
            for c, s in zip(out["crop"], out["state"])
        ]
        out["crop_hist_avg"] = [
            _lookup(self.crop_maps, c, self.global_mean) for c in out["crop"]
        ]
        out["state_hist_avg"] = [
            _lookup(self.state_maps, s, self.global_mean) for s in out["state"]
        ]
        return out

    def build_inference_frame(
        self, *, state: str, district: str, crop: str, season: str, area_ha: float
    ) -> pd.DataFrame:
        row = {
            "state": state,
            "district": district,
            "crop": crop,
            "season": season,
            "area_ha": area_ha,
            "crop_state_hist_avg": _lookup(
                self.crop_state_maps, f"{crop}|{state}", self.global_mean
            ),
            "crop_hist_avg": _lookup(self.crop_maps, crop, self.global_mean),
            "state_hist_avg": _lookup(self.state_maps, state, self.global_mean),
        }
        return self._frame_from_rows([row])

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        if self.preprocessor is None:
            raise RuntimeError("YieldFeatureBuilder has not been fitted")
        return self.preprocessor.transform(self._frame_from_rows(df.to_dict("records")))

    @property
    def encoded_feature_names(self) -> list[str]:
        if self.preprocessor is None:
            return []
        try:
            return [str(n) for n in self.preprocessor.get_feature_names_out()]
        except Exception:  # pragma: no cover - defensive
            return []


def _group_maps(df: pd.DataFrame, keys: list[str]) -> dict[str, list[float]]:
    grouped = df.groupby(keys)["yield_q_per_ha"].agg(["sum", "count"])
    maps: dict[str, list[float]] = {}
    for index, row in grouped.iterrows():
        key = index if isinstance(index, str) else "|".join(str(i) for i in index)
        maps[key] = [float(row["sum"]), int(row["count"])]
    return maps


def _lookup(maps: dict[str, list[float]], key: str, prior: float) -> float:
    entry = maps.get(key)
    if not entry:
        return prior
    return _smoothed_mean(entry[0], int(entry[1]), prior)


def _expanding_year_prior(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Mean yield from strictly earlier years for each key combination.

    Aggregating to one row per key/year before the cumulative sum prevents
    same-year observations from leaking into a row's own feature.
    """
    yearly = (
        df.groupby([*keys, "year"])["yield_q_per_ha"]
        .agg(["sum", "count"])
        .reset_index()
        .sort_values([*keys, "year"])
    )
    grouped = yearly.groupby(keys, dropna=False)
    yearly["_prior_sum"] = grouped["sum"].cumsum() - yearly["sum"]
    yearly["_prior_count"] = grouped["count"].cumsum() - yearly["count"]
    yearly["_prior"] = yearly["_prior_sum"] / yearly["_prior_count"].replace(0, np.nan)
    return yearly[[*keys, "year", "_prior"]]


def add_expanding_history_features(df: pd.DataFrame) -> pd.DataFrame:
    """Time-aware history features for training rows (no future leakage).

    For a row harvested in year Y, every feature uses only observations from
    years < Y.  The first year therefore falls back to the global prior.
    """
    out = df.copy()
    fallback = float(out["yield_q_per_ha"].mean())

    global_by_year = out.groupby("year")["yield_q_per_ha"].mean().sort_index().shift(1).ffill()
    global_by_year = global_by_year.fillna(fallback)
    out["_global_prior"] = out["year"].map(global_by_year).fillna(fallback)

    crop_state = _expanding_year_prior(out, ["crop", "state"]).rename(
        columns={"_prior": "_crop_state_prior"}
    )
    crop = _expanding_year_prior(out, ["crop"]).rename(columns={"_prior": "_crop_prior"})
    state = _expanding_year_prior(out, ["state"]).rename(columns={"_prior": "_state_prior"})

    out = out.merge(crop_state, on=["crop", "state", "year"], how="left")
    out = out.merge(crop, on=["crop", "year"], how="left")
    out = out.merge(state, on=["state", "year"], how="left")

    out["crop_state_hist_avg"] = out["_crop_state_prior"].fillna(out["_crop_prior"]).fillna(
        out["_state_prior"]
    ).fillna(out["_global_prior"])
    out["crop_hist_avg"] = out["_crop_prior"].fillna(out["_global_prior"])
    out["state_hist_avg"] = out["_state_prior"].fillna(out["_global_prior"])
    return out.drop(
        columns=["_crop_state_prior", "_crop_prior", "_state_prior", "_global_prior"]
    )
