# Copyright 2026 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""LangChain tools for the ERCOT Forecast agent.

These tools give the agent access to historical ERCOT day-ahead market (DAM)
prices from the configured DataRobot AI Catalog dataset, run time-series
forecasts against the configured deployment, and compute forecast accuracy
metrics.
"""

from __future__ import annotations

import io
import logging
import math
import os
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, cast

import pandas as pd
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

HUBS = ["HB_HOUSTON", "HB_NORTH", "HB_SOUTH", "HB_WEST"]
PRICE_COL = "dam_price_usd_mwh"
HUB_COL = "hub_name"
TS_COL = "timestamp_utc"
FORECAST_HORIZON_HOURS = 24


def _dataset_id() -> str:
    return os.getenv("ERCOT_DATASET_ID", "698dfe27b04f8da88246bc28")


def _deployment_id() -> str | None:
    return os.getenv("ERCOT_DEPLOYMENT_ID") or None


def _client():
    import datarobot as dr

    endpoint = os.getenv("DATAROBOT_ENDPOINT")
    token = os.getenv("DATAROBOT_API_TOKEN")
    if endpoint and token:
        return dr.Client(endpoint=endpoint, token=token)
    return dr.Client()


@lru_cache(maxsize=2)
def _load_dataset(dataset_id: str) -> pd.DataFrame:
    """Download the AI Catalog dataset as a DataFrame (cached)."""
    client = _client()
    resp = client.get(f"datasets/{dataset_id}/file/")
    df = pd.read_csv(io.BytesIO(resp.content))
    df.columns = [str(c).strip() for c in df.columns]
    if TS_COL in df.columns:
        df[TS_COL] = pd.to_datetime(df[TS_COL], utc=True, errors="coerce")
    return df


def _frame() -> pd.DataFrame:
    return _load_dataset(_dataset_id()).copy()


def _normalize_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return cast(datetime, pd.to_datetime(value, utc=True).to_pydatetime())
    except Exception:
        return None


def _to_dr_datetime(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_float(value: Any) -> float | None:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _detect_prediction_column(preds_df: pd.DataFrame) -> str:
    for candidate in (
        f"{PRICE_COL} (actual)_PREDICTION",
        f"{PRICE_COL}_PREDICTION",
        "PREDICTION",
        "prediction",
        "Prediction",
    ):
        if candidate in preds_df.columns:
            return candidate
    for col in preds_df.columns:
        if str(col).endswith("_PREDICTION"):
            return str(col)
    for col in preds_df.columns:
        if pd.api.types.is_numeric_dtype(preds_df[col]):
            return str(col)
    raise ValueError("Could not locate prediction column in deployment output.")


def _hub_frame(hub: str) -> pd.DataFrame:
    raw = _load_dataset(_dataset_id())
    sub = raw[raw[HUB_COL].astype(str).str.upper() == hub.upper()].copy()
    return sub.sort_values(TS_COL) if TS_COL in sub.columns else sub


def _resolve_forecast_window(
    sub: pd.DataFrame, forecast_origin_date: str | None
) -> tuple[datetime, datetime]:
    """Return [start, end] timestamps for a 24-hour forward forecast window."""
    if sub.empty or TS_COL not in sub.columns:
        raise ValueError("No data available for the requested hub in ERCOT_DATASET_ID.")

    ts = pd.to_datetime(sub[TS_COL], utc=True, errors="coerce")

    if forecast_origin_date:
        day = _normalize_date(forecast_origin_date)
        if day is None:
            raise ValueError(
                f"Invalid forecast_origin_date {forecast_origin_date!r}; use YYYY-MM-DD."
            )
        day_start = pd.Timestamp(day).tz_convert("UTC")
        day_end = day_start + timedelta(days=1)
        on_day = sub[(ts >= day_start) & (ts < day_end)]
        if on_day.empty:
            raise ValueError(
                f"No rows for hub on {forecast_origin_date}. "
                "Pick a date that exists in ERCOT_DATASET_ID."
            )
        day_ts = pd.to_datetime(on_day[TS_COL], utc=True, errors="coerce")
        window_start = cast(datetime, day_ts.min().to_pydatetime())
        window_end = cast(datetime, day_ts.max().to_pydatetime())
    else:
        data_end = ts.max()
        if pd.isna(data_end):
            raise ValueError("Could not determine latest timestamp in dataset.")
        window_end = cast(datetime, data_end.to_pydatetime())
        window_start = cast(
            datetime, (data_end - pd.Timedelta(hours=FORECAST_HORIZON_HOURS - 1)).to_pydatetime()
        )

    if window_end <= window_start:
        window_end = window_start + timedelta(hours=1)
    return window_start, window_end


def _format_ts_for_scoring(df: pd.DataFrame) -> bytes:
    out = df.copy()
    out[TS_COL] = (
        pd.to_datetime(out[TS_COL], utc=True, errors="coerce")
        .dt.tz_localize(None)
        .dt.strftime("%Y-%m-%d %H:%M:%S")
    )
    return out.to_csv(index=False).encode("utf-8")


def _run_ts_batch_prediction(
    sub: pd.DataFrame,
    *,
    predictions_start: datetime,
    predictions_end: datetime,
) -> pd.DataFrame:
    deployment_id = _deployment_id()
    if not deployment_id:
        raise ValueError(
            "ERCOT_DEPLOYMENT_ID is not set. Configure it in .env before forecasting."
        )

    import datarobot as dr
    from datarobot import BatchPredictionJob

    _client()
    csv_in = _format_ts_for_scoring(sub)
    ts_settings: dict[str, Any] = {
        "type": "historical",
        "relax_known_in_advance_features_check": True,
        "predictions_start_date": _to_dr_datetime(predictions_start),
        "predictions_end_date": _to_dr_datetime(predictions_end),
    }

    job = BatchPredictionJob.score(
        deployment=deployment_id,
        intake_settings={"type": "localFile", "file": io.BytesIO(csv_in)},  # type: ignore[arg-type]
        output_settings={"type": "localFile", "path": None},  # type: ignore[arg-type]
        timeseries_settings=ts_settings,  # type: ignore[arg-type]
    )
    job.wait_for_completion()
    buf = io.BytesIO()
    job.download(buf)
    buf.seek(0)
    return pd.read_csv(buf)


def _predictions_from_batch(
    preds_df: pd.DataFrame,
    hub: str,
    *,
    origin: datetime | None = None,
    forecast_distances: range | None = None,
) -> list[dict[str, Any]]:
    pred_col = _detect_prediction_column(preds_df)
    df = preds_df.copy()
    df["_ts"] = pd.to_datetime(df[TS_COL], utc=True, errors="coerce")

    if forecast_distances is not None and "FORECAST_DISTANCE" in df.columns:
        df = df[df["FORECAST_DISTANCE"].isin(list(forecast_distances))]
        if origin is not None:
            origin_ts = pd.Timestamp(origin).tz_convert("UTC")
            if "FORECAST_POINT" in df.columns:
                df["_origin"] = pd.to_datetime(df["FORECAST_POINT"], utc=True, errors="coerce")
                df = df[df["_origin"] == origin_ts]
            else:
                window_end = origin_ts + pd.Timedelta(hours=max(forecast_distances))
                df = df[(df["_ts"] > origin_ts) & (df["_ts"] <= window_end)]

    df = df.sort_values(
        ["FORECAST_DISTANCE", "_ts"] if "FORECAST_DISTANCE" in df.columns else ["_ts"]
    )

    result: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        ts = row["_ts"]
        predicted = _to_float(row.get(pred_col))
        if predicted is None:
            continue
        entry: dict[str, Any] = {
            TS_COL: ts.isoformat() if pd.notna(ts) else None,
            HUB_COL: hub,
            "predicted_dam_price_usd_mwh": predicted,
        }
        if "FORECAST_DISTANCE" in df.columns and pd.notna(row.get("FORECAST_DISTANCE")):
            entry["forecast_distance"] = int(row["FORECAST_DISTANCE"])
        result.append(entry)
    return result


@tool
def get_dam_prices(
    hubs: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve historical ERCOT day-ahead market prices and weather/grid
    features from the DataRobot AI Catalog dataset.

    Args:
        hubs: Trading hub names to include (HB_HOUSTON, HB_NORTH, HB_SOUTH,
            HB_WEST). Omit or pass an empty list for all hubs.
        start_date: ISO date (YYYY-MM-DD). Defaults to 30 days before end_date.
        end_date: ISO date (YYYY-MM-DD). Defaults to the latest available date.

    Returns a list of records with timestamp_utc, hub_name, dam_price_usd_mwh,
    and available weather/grid features.
    """
    df = _frame()
    if hubs:
        wanted = {h.upper() for h in hubs}
        df = df[df[HUB_COL].astype(str).str.upper().isin(wanted)]

    end_dt = pd.to_datetime(end_date, utc=True) if end_date else None
    if end_dt is None and TS_COL in df.columns and not df.empty:
        end_dt = df[TS_COL].max()
    start_dt = pd.to_datetime(start_date, utc=True) if start_date else None
    if start_dt is None and end_dt is not None:
        start_dt = end_dt - timedelta(days=30)

    if TS_COL in df.columns:
        if start_dt is not None:
            df = df[df[TS_COL] >= start_dt]
        if end_dt is not None:
            df = df[df[TS_COL] <= end_dt]
        df = df.sort_values(TS_COL)
        df[TS_COL] = df[TS_COL].apply(lambda v: v.isoformat() if pd.notna(v) else None)

    df = df.where(pd.notna(df), None)
    return cast(list[dict[str, Any]], df.to_dict(orient="records"))


@tool
def predict_dam_prices(
    hub: str,
    forecast_origin_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Run the configured ERCOT time-series deployment to produce DAM price
    forecasts for one hub.

    Use this tool for ALL forward-looking price requests. Do not call Global MCP
    prediction tools for ERCOT DAM forecasting.

    Modes:
    - **24-hour ahead (default):** Omit start_date/end_date. Returns 24 hourly
      1-step-ahead predictions either for forecast_origin_date (all hours that day
      in ERCOT_DATASET_ID) or, if omitted, the most recent 24 hours in the data.
    - **Historical backtest:** Provide start_date and end_date (YYYY-MM-DD) to
      return 1-step-ahead (FORECAST_DISTANCE=1) predictions across that window
      for accuracy comparison with get_dam_prices actuals.

    Args:
        hub: Trading hub (HB_HOUSTON, HB_NORTH, HB_SOUTH, HB_WEST).
        forecast_origin_date: Optional ISO date for the 24h-ahead origin (uses
            the last hour on that date in the dataset).
        start_date: Optional backtest window start (YYYY-MM-DD).
        end_date: Optional backtest window end (YYYY-MM-DD).

    Returns a dict with hub_name, forecast_origin_utc, deployment_id, dataset_id,
    mode ('forward_24h' or 'backtest'), and predictions list.
    """
    hub = hub.upper()
    if hub not in HUBS:
        raise ValueError(f"Invalid hub {hub!r}; expected one of {HUBS}.")

    sub = _hub_frame(hub)
    if sub.empty:
        return {
            "hub_name": hub,
            "mode": "forward_24h",
            "predictions": [],
            "error": f"No rows for {hub} in dataset {_dataset_id()}.",
        }

    deployment_id = _deployment_id()
    dataset_id = _dataset_id()

    try:
        if start_date or end_date:
            ts = pd.to_datetime(sub[TS_COL], utc=True, errors="coerce")
            data_end = ts.max()
            end_dt = _normalize_date(end_date) or (
                data_end.to_pydatetime() if pd.notna(data_end) else None
            )
            start_dt = _normalize_date(start_date)
            if start_dt is None and end_dt is not None:
                start_dt = end_dt - timedelta(days=30)
            if start_dt is None or end_dt is None:
                raise ValueError("Could not resolve backtest date window.")

            preds_df = _run_ts_batch_prediction(
                sub, predictions_start=start_dt, predictions_end=end_dt
            )
            if "FORECAST_DISTANCE" in preds_df.columns:
                preds_df = preds_df[preds_df["FORECAST_DISTANCE"] == 1]

            predictions = _predictions_from_batch(preds_df, hub)
            return {
                "hub_name": hub,
                "mode": "backtest",
                "deployment_id": deployment_id,
                "dataset_id": dataset_id,
                "predictions_start_date": start_date,
                "predictions_end_date": end_date,
                "predictions": predictions,
            }

        window_start, window_end = _resolve_forecast_window(sub, forecast_origin_date)
        preds_df = _run_ts_batch_prediction(
            sub, predictions_start=window_start, predictions_end=window_end
        )
        if "FORECAST_DISTANCE" in preds_df.columns:
            preds_df = preds_df[preds_df["FORECAST_DISTANCE"] == 1]

        predictions = _predictions_from_batch(preds_df, hub)[-FORECAST_HORIZON_HOURS:]

        return {
            "hub_name": hub,
            "mode": "forward_24h",
            "deployment_id": deployment_id,
            "dataset_id": dataset_id,
            "predictions_start_utc": pd.Timestamp(window_start).tz_convert("UTC").isoformat(),
            "predictions_end_utc": pd.Timestamp(window_end).tz_convert("UTC").isoformat(),
            "forecast_origin_date": forecast_origin_date,
            "predictions": predictions,
        }
    except Exception as exc:
        logger.exception("predict_dam_prices failed for hub=%s", hub)
        return {
            "hub_name": hub,
            "mode": "forward_24h" if not (start_date or end_date) else "backtest",
            "deployment_id": deployment_id,
            "dataset_id": dataset_id,
            "predictions": [],
            "error": str(exc),
        }


@tool
def compute_accuracy_metrics(
    actuals: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute forecast accuracy metrics (RMSE, MAE, Max Error) and a per-point
    error series comparing predicted vs. actual DAM prices.

    Args:
        actuals: Records with timestamp_utc, hub_name, dam_price_usd_mwh.
        predictions: Records with timestamp_utc, hub_name,
            predicted_dam_price_usd_mwh.

    Returns a dict with a 'metrics' dict (rmse, mae, max_error) and an
    'error_series' list including a 90% confidence interval per point.
    """
    a = pd.DataFrame(actuals)
    p = pd.DataFrame(predictions)
    empty = {
        "metrics": {"rmse": None, "mae": None, "max_error": None},
        "error_series": [],
    }
    if a.empty or p.empty:
        return empty

    merged = a.merge(p, on=[TS_COL, HUB_COL], how="inner", suffixes=("", "_pred"))
    merged["actual"] = pd.to_numeric(merged[PRICE_COL], errors="coerce")
    merged["predicted"] = pd.to_numeric(
        merged["predicted_dam_price_usd_mwh"], errors="coerce"
    )
    merged = merged.dropna(subset=["actual", "predicted"])
    if merged.empty:
        return empty

    merged["error"] = merged["predicted"] - merged["actual"]
    merged["abs_error"] = merged["error"].abs()

    rmse = float(math.sqrt((merged["error"] ** 2).mean()))
    mae = float(merged["abs_error"].mean())
    max_error = float(merged["abs_error"].max())
    resid_std = float(merged["error"].std(ddof=1)) if len(merged) > 1 else 0.0
    half_width = 1.645 * resid_std

    merged = merged.sort_values(TS_COL)
    series = [
        {
            TS_COL: row[TS_COL],
            HUB_COL: row[HUB_COL],
            "actual": float(row["actual"]),
            "predicted": float(row["predicted"]),
            "error": float(row["error"]),
            "abs_error": float(row["abs_error"]),
            "ci_lower": float(row["predicted"] - half_width),
            "ci_upper": float(row["predicted"] + half_width),
        }
        for _, row in merged.iterrows()
    ]
    return {
        "metrics": {"rmse": rmse, "mae": mae, "max_error": max_error},
        "error_series": series,
    }


@tool
def analyze_forecast_miss(
    timestamp_utc: str,
    hub_name: str,
    actual: float | None = None,
    predicted: float | None = None,
    action: str | None = None,
) -> dict[str, Any]:
    """Classify a forecast miss and return narrative plus recommended follow-up actions.

    Use when the user asks why a forecast was wrong, or to drill into drivers.
    Optional action values: compare_hubs, driver_window, start_retrain, focus_wind.

    Args:
        timestamp_utc: ISO timestamp of the forecast point.
        hub_name: Trading hub (e.g. HB_HOUSTON).
        actual: Observed DAM price ($/MWh), if known.
        predicted: Model prediction ($/MWh), if known.
        action: Optional follow-up action id from a prior recommended_actions list.
    """
    from agent.miss_analysis import (
        ERROR_MODES,
        _driver_summary,
        build_narrative,
        classify_miss,
        compare_hubs_at_timestamp,
        driver_window,
        recommended_actions,
        retrain_recommendations,
    )

    df = _frame()
    subset = df[df[HUB_COL].astype(str).str.upper() == hub_name.upper()]
    target = pd.to_datetime(timestamp_utc, utc=True, errors="coerce")
    if subset.empty or pd.isna(target) or TS_COL not in subset.columns:
        return {
            "timestamp_utc": timestamp_utc,
            "hub_name": hub_name,
            "error_mode": "mixed_drivers",
            "error_mode_label": ERROR_MODES["mixed_drivers"],
            "narrative": ["No matching dataset row for this hub and timestamp."],
            "recommended_actions": recommended_actions("mixed_drivers"),
            "driver_summary": {},
        }
    subset = subset.assign(_delta=(subset[TS_COL] - target).abs()).sort_values("_delta")
    row = subset.iloc[0].drop(labels=["_delta"]).to_dict()

    drivers = _driver_summary(row)
    error_mode = classify_miss(actual=actual, predicted=predicted, drivers=drivers)
    narrative = build_narrative(
        hub_name=hub_name,
        timestamp_utc=timestamp_utc,
        actual=actual,
        predicted=predicted,
        error_mode=error_mode,
        drivers=drivers,
    )
    actions = recommended_actions(error_mode)

    action_result: dict[str, Any] | None = None
    if action == "compare_hubs":
        action_result = {
            "type": "compare_hubs",
            "hubs": compare_hubs_at_timestamp(df, timestamp_utc, hub_name),
        }
    elif action == "driver_window":
        action_result = {
            "type": "driver_window",
            "series": driver_window(df, timestamp_utc, hub_name),
        }
    elif action in ("start_retrain", "recommend_retrain"):
        from agent.retrain_service import start_retrain
        import os

        action_result = start_retrain(
            endpoint=os.getenv("DATAROBOT_ENDPOINT", "https://app.datarobot.com/api/v2"),
            token=os.getenv("DATAROBOT_API_TOKEN", ""),
            dataset_id=os.getenv("ERCOT_DATASET_ID"),
            deployment_id=os.getenv("ERCOT_DEPLOYMENT_ID"),
            hub_name=hub_name,
            error_mode=error_mode,
        )
        if action == "recommend_retrain":
            action_result["recommendations"] = retrain_recommendations(error_mode, hub_name)
    elif action == "focus_wind":
        wind = drivers.get("wind") or {}
        lines = []
        if wind.get("actual_mw") is not None and wind.get("forecast_mw") is not None:
            lines.append(
                f"Wind forecast error: {wind.get('delta_mw', 0):+.0f} MW "
                f"(actual {wind['actual_mw']:.0f} vs forecast {wind['forecast_mw']:.0f})."
            )
        action_result = {"type": "focus_wind", "wind": wind, "narrative": lines}

    return {
        "timestamp_utc": timestamp_utc,
        "hub_name": hub_name,
        "error_mode": error_mode,
        "error_mode_label": ERROR_MODES.get(error_mode, error_mode),
        "narrative": narrative,
        "recommended_actions": actions,
        "driver_summary": drivers,
        "action_result": action_result,
    }


@tool
def investigate_forecast_error(timestamp_utc: str, hub_name: str) -> dict[str, Any]:
    """Gather feature context for a specific forecast point to support a
    root-cause investigation into weather, grid, renewable generation, and load.

    Args:
        timestamp_utc: ISO timestamp of the forecast point to investigate.
        hub_name: Trading hub name.

    Returns the nearest dataset row's weather/grid/renewable/load feature values
    for the point, which the agent can interpret alongside external context.
    """
    df = _frame()
    subset = df[df[HUB_COL].astype(str).str.upper() == hub_name.upper()]
    target = pd.to_datetime(timestamp_utc, utc=True, errors="coerce")
    if subset.empty or pd.isna(target) or TS_COL not in subset.columns:
        return {
            "timestamp_utc": timestamp_utc,
            "hub_name": hub_name,
            "context_features": {},
        }
    subset = subset.assign(_delta=(subset[TS_COL] - target).abs()).sort_values("_delta")
    row = subset.iloc[0].drop(labels=["_delta"]).to_dict()
    hints = (
        "temperature",
        "humidity",
        "precipitation",
        "windspeed",
        "solar_actual_mw",
        "solar_forecast_mw",
        "wind_forecast_mw",
        "load_forecast_mw",
        PRICE_COL,
    )
    context = {
        k: (float(v) if isinstance(v, (int, float)) and pd.notna(v) else v)
        for k, v in row.items()
        if any(h in str(k) for h in hints)
    }
    return {
        "timestamp_utc": timestamp_utc,
        "hub_name": hub_name,
        "context_features": context,
    }


ERCOT_TOOLS = [
    get_dam_prices,
    predict_dam_prices,
    compute_accuracy_metrics,
    analyze_forecast_miss,
    investigate_forecast_error,
]
