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
"""Rule-based forecast miss analysis and recommended agentic follow-ups."""

from __future__ import annotations

from typing import Any

import pandas as pd

HUB_COL = "hub_name"
TS_COL = "timestamp_utc"
PRICE_COL = "dam_price_usd_mwh"

ERROR_MODES = {
    "renewable_shortfall": "Renewable generation shortfall",
    "load_surprise": "Load above day-ahead forecast",
    "price_spike": "Supply stack / scarcity pricing",
    "model_bias": "Systematic under- or over-prediction",
    "mixed_drivers": "Multiple contributing drivers",
}


def _to_float(value: Any) -> float | None:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _pick(row: dict[str, Any], *needles: str) -> tuple[str | None, float | None]:
    for key, raw in row.items():
        key_l = str(key).lower()
        if any(n in key_l for n in needles):
            val = _to_float(raw)
            if val is not None:
                return str(key), val
    return None, None


def _driver_summary(row: dict[str, Any]) -> dict[str, Any]:
    wind_f_key, wind_f = _pick(row, "wind_forecast")
    wind_a_key, wind_a = _pick(row, "wind_actual")
    solar_f_key, solar_f = _pick(row, "solar_forecast")
    solar_a_key, solar_a = _pick(row, "solar_actual")
    load_f_key, load_f = _pick(row, "load_forecast")
    load_a_key, load_a = _pick(row, "load_actual")

    summary: dict[str, Any] = {}
    if wind_a is not None or wind_f is not None:
        summary["wind"] = {
            "actual_mw": wind_a,
            "forecast_mw": wind_f,
            "delta_mw": (wind_a - wind_f) if wind_a is not None and wind_f is not None else None,
        }
    if solar_a is not None or solar_f is not None:
        summary["solar"] = {
            "actual_mw": solar_a,
            "forecast_mw": solar_f,
            "delta_mw": (solar_a - solar_f) if solar_a is not None and solar_f is not None else None,
        }
    if load_a is not None or load_f is not None:
        summary["load"] = {
            "actual_mw": load_a,
            "forecast_mw": load_f,
            "delta_mw": (load_a - load_f) if load_a is not None and load_f is not None else None,
        }
    return summary


def classify_miss(
    *,
    actual: float | None,
    predicted: float | None,
    drivers: dict[str, Any],
) -> str:
    error = (predicted - actual) if actual is not None and predicted is not None else None
    wind = drivers.get("wind") or {}
    load = drivers.get("load") or {}
    wind_delta = wind.get("delta_mw")
    load_delta = load.get("delta_mw")

    if error is not None and actual and abs(error) / max(abs(actual), 1.0) > 0.25:
        if wind_delta is not None and wind_delta < -500 and error > 0:
            return "renewable_shortfall"
        if load_delta is not None and load_delta > 300 and error > 0:
            return "load_surprise"
        if actual > (predicted or 0) + 15:
            return "price_spike"

    if error is not None and abs(error) > 10:
        return "model_bias"
    return "mixed_drivers"


def build_narrative(
    *,
    hub_name: str,
    timestamp_utc: str,
    actual: float | None,
    predicted: float | None,
    error_mode: str,
    drivers: dict[str, Any],
) -> list[str]:
    mode_label = ERROR_MODES.get(error_mode, error_mode)
    lines = [
        f"Investigating the forecast miss at {hub_name} ({timestamp_utc})…",
        f"Classification: {mode_label}.",
    ]

    if actual is not None and predicted is not None:
        err = predicted - actual
        pct = (err / actual * 100) if actual else 0
        lines.append(
            f"Price gap: actual ${actual:.2f}/MWh vs predicted ${predicted:.2f}/MWh "
            f"({err:+.2f}, {pct:+.1f}%)."
        )

    wind = drivers.get("wind")
    if wind and wind.get("actual_mw") is not None and wind.get("forecast_mw") is not None:
        lines.append(
            f"Wind: actual {wind['actual_mw']:.0f} MW vs forecast "
            f"{wind['forecast_mw']:.0f} MW "
            f"({wind.get('delta_mw', 0):+.0f} MW)."
        )
    load = drivers.get("load")
    if load and load.get("actual_mw") is not None and load.get("forecast_mw") is not None:
        lines.append(
            f"Load: actual {load['actual_mw']:.0f} MW vs forecast "
            f"{load['forecast_mw']:.0f} MW "
            f"({load.get('delta_mw', 0):+.0f} MW)."
        )
    solar = drivers.get("solar")
    if solar and solar.get("actual_mw") is not None:
        lines.append(
            f"Solar: {solar['actual_mw']:.0f} MW actual"
            + (
                f" vs {solar['forecast_mw']:.0f} MW forecast"
                if solar.get("forecast_mw") is not None
                else ""
            )
            + "."
        )

    if error_mode == "renewable_shortfall":
        lines.append(
            "Conclusion: Lower-than-forecast renewable output likely removed cheap supply "
            "and pushed clearing prices above the model's prediction."
        )
    elif error_mode == "load_surprise":
        lines.append(
            "Conclusion: Demand ran hotter than the day-ahead load forecast, tightening "
            "reserves and lifting prices above prediction."
        )
    elif error_mode == "price_spike":
        lines.append(
            "Conclusion: A scarcity-style price move suggests marginal units were higher "
            "on the supply stack than the model expected."
        )
    else:
        lines.append(
            "Conclusion: Review driver features and neighboring hubs to isolate the "
            "primary contributor before changing the model."
        )
    return lines


def recommended_actions(error_mode: str) -> list[dict[str, str]]:
    actions = [
        {
            "id": "compare_hubs",
            "label": "Compare other hubs at this hour",
            "description": "See whether the miss is hub-specific or system-wide.",
        },
        {
            "id": "driver_window",
            "label": "Show ±6h driver trend",
            "description": "Plot wind, solar, and load around the miss.",
        },
        {
            "id": "start_retrain",
            "label": "Start retrain in DataRobot",
            "description": "Launch Autopilot on ERCOT_DATASET_ID (opens platform if API unavailable).",
        },
    ]
    if error_mode == "renewable_shortfall":
        actions.insert(
            0,
            {
                "id": "focus_wind",
                "label": "Deep-dive wind forecast error",
                "description": "Quantify wind forecast bias for this hub and week.",
            },
        )
    return actions


def retrain_recommendations(error_mode: str, hub_name: str) -> list[str]:
    base = [
        f"Backtest {hub_name} evening and peak hours separately — errors often cluster by time of day.",
        "Review known-in-advance renewable and load features for stale or biased day-ahead forecasts.",
        f"Open a Workbench experiment on ERCOT_DATASET_ID with recent weeks held out for validation.",
    ]
    if error_mode == "renewable_shortfall":
        base.insert(
            0,
            "Add or refresh wind forecast error features (actual minus day-ahead wind forecast).",
        )
    elif error_mode == "load_surprise":
        base.insert(0, "Segment model performance when load_actual exceeds load_forecast by >300 MW.")
    return base


def compare_hubs_at_timestamp(
    df: pd.DataFrame, timestamp_utc: str, primary_hub: str
) -> list[dict[str, Any]]:
    target = pd.to_datetime(timestamp_utc, utc=True, errors="coerce")
    if pd.isna(target) or TS_COL not in df.columns:
        return []
    window = df[(df[TS_COL] - target).abs() <= pd.Timedelta(hours=1)]
    rows: list[dict[str, Any]] = []
    for hub, grp in window.groupby(df[HUB_COL].astype(str).str.upper()):
        row = grp.sort_values((grp[TS_COL] - target).abs()).iloc[0]
        price = _to_float(row.get(PRICE_COL))
        rows.append(
            {
                "hub_name": hub,
                "timestamp_utc": row[TS_COL].isoformat() if pd.notna(row[TS_COL]) else None,
                "dam_price_usd_mwh": price,
                "is_primary": hub == primary_hub.upper(),
            }
        )
    return sorted(rows, key=lambda r: r.get("dam_price_usd_mwh") or 0, reverse=True)


def driver_window(
    df: pd.DataFrame, timestamp_utc: str, hub_name: str, hours: int = 6
) -> list[dict[str, Any]]:
    target = pd.to_datetime(timestamp_utc, utc=True, errors="coerce")
    if pd.isna(target):
        return []
    sub = df[df[HUB_COL].astype(str).str.upper() == hub_name.upper()].copy()
    if sub.empty or TS_COL not in sub.columns:
        return []
    mask = (sub[TS_COL] >= target - pd.Timedelta(hours=hours)) & (
        sub[TS_COL] <= target + pd.Timedelta(hours=hours)
    )
    window = sub[mask].sort_values(TS_COL)
    out: list[dict[str, Any]] = []
    for _, row in window.iterrows():
        row_dict = row.to_dict()
        ts = row_dict.get(TS_COL)
        entry: dict[str, Any] = {
            TS_COL: ts.isoformat() if isinstance(ts, pd.Timestamp) and pd.notna(ts) else ts,
            PRICE_COL: _to_float(row_dict.get(PRICE_COL)),
        }
        entry.update(_driver_summary(row_dict))
        out.append(entry)
    return out
