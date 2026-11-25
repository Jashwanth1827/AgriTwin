"""Market price forecasting with chronological validation.

Models are deliberately simple and interpretable: seasonal naive, moving
average, linear trend with weekly seasonality, random forest and gradient
boosting on lag features.  The best model is selected on a held-out tail of the
series and then refitted on the full history.  No future observation is used in
training or validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

LAGS = [1, 2, 3, 7, 14, 21, 28]
MIN_OBSERVATIONS = 21


class InsufficientMarketData(RuntimeError):
    pass


@dataclass
class ForecastResult:
    model_name: str
    expected_price: float
    lower_bound: float
    upper_bound: float
    points: list[dict[str, Any]]
    metrics: dict[str, float]
    comparison: list[dict[str, Any]]
    interval_method: str
    latest_date: date
    horizon_days: int


def prepare_series(points: list[tuple[date, float]]) -> pd.Series:
    if not points:
        raise InsufficientMarketData("No price observations are available")
    frame = pd.DataFrame(points, columns=["date", "price"])
    frame["date"] = pd.to_datetime(frame["date"])
    frame["price"] = pd.to_numeric(frame["price"], errors="coerce")
    frame = frame.dropna()
    frame = frame[frame["price"] > 0]
    if frame.empty:
        raise InsufficientMarketData("No valid positive prices are available")
    series = frame.groupby("date")["price"].mean().sort_index()
    full_index = pd.date_range(series.index.min(), series.index.max(), freq="D")
    series = series.reindex(full_index)
    # Short gaps are interpolated; longer gaps remain missing and are dropped.
    series = series.interpolate(method="time", limit=7, limit_area="inside")
    series = series.dropna()
    if len(series) < MIN_OBSERVATIONS:
        raise InsufficientMarketData(
            f"At least {MIN_OBSERVATIONS} daily observations are required; found {len(series)}"
        )
    return series


def _supervised_frame(series: pd.Series) -> tuple[pd.DataFrame, pd.Series]:
    frame = pd.DataFrame({"y": series.values}, index=series.index)
    for lag in LAGS:
        frame[f"lag_{lag}"] = frame["y"].shift(lag)
    frame["dow"] = frame.index.dayofweek
    frame["month"] = frame.index.month
    frame["trend"] = np.arange(len(frame))
    frame = frame.dropna()
    return frame.drop(columns=["y"]), frame["y"]


def _recursive_predict(model, series: pd.Series, horizon: int) -> np.ndarray:
    history = list(series.values)
    predictions: list[float] = []
    start_index = len(series)
    for step in range(horizon):
        features: dict[str, float] = {}
        for lag in LAGS:
            features[f"lag_{lag}"] = history[-lag] if len(history) >= lag else history[-1]
        future_date = series.index[-1] + timedelta(days=step + 1)
        features["dow"] = future_date.dayofweek
        features["month"] = future_date.month
        features["trend"] = start_index + step
        x = pd.DataFrame([features])[list(_supervised_frame(series)[0].columns)]
        value = float(model.predict(x)[0])
        value = max(value, 1.0)
        predictions.append(value)
        history.append(value)
    return np.array(predictions)


def _seasonal_naive(series: pd.Series, horizon: int) -> np.ndarray:
    history = list(series.values)
    predictions: list[float] = []
    for _ in range(horizon):
        value = history[-7] if len(history) >= 7 else history[-1]
        predictions.append(float(value))
        history.append(float(value))
    return np.array(predictions)


def _moving_average(series: pd.Series, horizon: int) -> np.ndarray:
    history = list(series.values)
    predictions: list[float] = []
    for _ in range(horizon):
        value = float(np.mean(history[-7:]))
        predictions.append(value)
        history.append(value)
    return np.array(predictions)


def _linear_trend(series: pd.Series, horizon: int) -> np.ndarray:
    frame = pd.DataFrame({"y": series.values}, index=series.index)
    frame["trend"] = np.arange(len(frame))
    frame["dow"] = frame.index.dayofweek
    design = pd.get_dummies(frame[["trend", "dow"]], columns=["dow"], drop_first=True)
    model = LinearRegression().fit(design, frame["y"])
    future_dates = pd.date_range(series.index[-1] + timedelta(days=1), periods=horizon, freq="D")
    future = pd.DataFrame({"trend": np.arange(len(frame), len(frame) + horizon)}, index=future_dates)
    future["dow"] = future_dates.dayofweek
    future_design = pd.get_dummies(future[["trend", "dow"]], columns=["dow"], drop_first=True)
    future_design = future_design.reindex(columns=design.columns, fill_value=0)
    return np.clip(model.predict(future_design), 1.0, None)


def _fit_ml_model(name: str, series: pd.Series):
    x, y = _supervised_frame(series)
    if name == "RandomForest":
        model = RandomForestRegressor(
            n_estimators=140, min_samples_leaf=2, n_jobs=-1, random_state=42
        )
    else:
        model = GradientBoostingRegressor(n_estimators=180, max_depth=3, random_state=42)
    model.fit(x, y)
    return model


def _evaluate(
    name: str,
    train: pd.Series,
    actual: np.ndarray,
    predictions: np.ndarray,
) -> dict[str, float]:
    mask = actual != 0
    return {
        "model": name,
        "mae": round(float(mean_absolute_error(actual, predictions)), 3),
        "rmse": round(float(np.sqrt(mean_squared_error(actual, predictions))), 3),
        "mape_pct": round(
            float(np.mean(np.abs((actual[mask] - predictions[mask]) / actual[mask])) * 100), 2
        ),
    }


def _predict_with_model(name: str, series: pd.Series, horizon: int) -> np.ndarray:
    if name == "SeasonalNaive":
        return _seasonal_naive(series, horizon)
    if name == "MovingAverage":
        return _moving_average(series, horizon)
    if name == "LinearTrendWeekly":
        return _linear_trend(series, horizon)
    model = _fit_ml_model(name, series)
    return _recursive_predict(model, series, horizon)


def forecast_prices(
    points: list[tuple[date, float]], horizon_days: int = 14
) -> ForecastResult:
    if horizon_days < 1 or horizon_days > 120:
        raise ValueError("horizon_days must be between 1 and 120")
    series = prepare_series(points)

    test_days = min(max(7, len(series) // 5), 21, len(series) - 14)
    if test_days < 7:
        raise InsufficientMarketData("Not enough history for chronological validation")
    train = series.iloc[:-test_days]
    actual = series.iloc[-test_days:].to_numpy()

    candidate_names = [
        "SeasonalNaive",
        "MovingAverage",
        "LinearTrendWeekly",
        "RandomForest",
        "GradientBoosting",
    ]
    comparison: list[dict[str, float]] = []
    predictions_by_model: dict[str, np.ndarray] = {}
    for name in candidate_names:
        try:
            predictions = _predict_with_model(name, train, test_days)
            predictions_by_model[name] = predictions
            comparison.append(_evaluate(name, train, actual, predictions))
        except Exception as exc:  # pragma: no cover - defensive for tiny series
            comparison.append({"model": name, "mae": float("inf"), "error": str(exc)})

    valid = [row for row in comparison if np.isfinite(row.get("mae", float("inf")))]
    if not valid:
        raise InsufficientMarketData("All forecasting candidates failed")
    comparison.sort(key=lambda row: row["mae"])
    best_name = comparison[0]["model"]

    residuals = np.abs(actual - predictions_by_model[best_name])
    global_q = float(np.quantile(residuals, 0.8)) if len(residuals) else 0.0
    step_quantiles = {
        step + 1: float(np.quantile(np.abs(actual[: step + 1] - predictions_by_model[best_name][: step + 1]), 0.8))
        for step in range(len(actual))
    }

    full_forecast = _predict_with_model(best_name, series, horizon_days)
    last_date = series.index[-1].date()
    result_points: list[dict[str, Any]] = []
    for step, value in enumerate(full_forecast, start=1):
        base_q = step_quantiles.get(step, step_quantiles.get(len(actual), global_q))
        if step > len(actual):
            base_q = step_quantiles.get(len(actual), global_q) * float(
                np.sqrt(step / max(len(actual), 1))
            )
        expected = max(float(value), 1.0)
        result_points.append(
            {
                "date": last_date + timedelta(days=step),
                "expected_price": round(expected, 2),
                "lower_bound": round(max(expected - base_q, 1.0), 2),
                "upper_bound": round(expected + base_q, 2),
            }
        )

    metrics = {k: v for k, v in comparison[0].items() if k != "model"}
    metrics["validation_days"] = test_days
    metrics["observations"] = len(series)
    return ForecastResult(
        model_name=best_name,
        expected_price=result_points[0]["expected_price"],
        lower_bound=result_points[0]["lower_bound"],
        upper_bound=result_points[0]["upper_bound"],
        points=result_points,
        metrics=metrics,
        comparison=comparison,
        interval_method="empirical_absolute_residual_q80_widened_by_sqrt_step",
        latest_date=last_date,
        horizon_days=horizon_days,
    )
