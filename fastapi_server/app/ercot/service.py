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
"""Data-access and analytics service for the ERCOT Forecast Agent App.

Responsibilities:
- Load historical ERCOT day-ahead market (DAM) price + feature data from the
  configured DataRobot AI Catalog dataset.
- Obtain day-ahead price predictions from the DataRobot model deployment.
- Compute forecast accuracy metrics (RMSE, MAE, Max Error) and per-point error
  series with a 90% confidence interval.
- Run an AI-driven root-cause investigation for a forecast point using dataset
  features plus optional external web/news context via Tavily.
"""

from __future__ import annotations

import io
import logging
import math
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, cast

import pandas as pd

from app.ercot.miss_analysis import (
    ERROR_MODES,
    _driver_summary,
    build_narrative,
    classify_miss,
    compare_hubs_at_timestamp,
    driver_window,
    recommended_actions,
    retrain_recommendations,
)
from app.ercot.retrain_service import start_retrain

logger = logging.getLogger(__name__)

HUBS = ["HB_HOUSTON", "HB_NORTH", "HB_SOUTH", "HB_WEST"]
PRICE_COL = "dam_price_usd_mwh"
HUB_COL = "hub_name"
TS_COL = "timestamp_utc"

# Columns treated as contextual features for root-cause analysis.
CONTEXT_FEATURE_HINTS = (
    "temperature",
    "humidity",
    "precipitation",
    "windspeed",
    "solar_actual_mw",
    "solar_forecast_mw",
    "wind_forecast_mw",
    "load_forecast_mw",
)


class ErcotDataError(RuntimeError):
    """Raised when ERCOT data or predictions cannot be retrieved."""


@lru_cache(maxsize=4)
def _load_dataset_cached(dataset_id: str, endpoint: str, token: str) -> pd.DataFrame:
    """Load the AI Catalog dataset into a DataFrame (cached by dataset id).

    Uses the DataRobot client to download the dataset as CSV. Cached to avoid
    re-downloading on every request; the app process is restarted on redeploy.
    """
    import datarobot as dr

    client = dr.Client(endpoint=endpoint, token=token)
    # Download the dataset file content via the public API.
    resp = client.get(f"datasets/{dataset_id}/file/")
    df = pd.read_csv(io.BytesIO(resp.content))
    df.columns = [str(c).strip() for c in df.columns]
    if TS_COL in df.columns:
        df[TS_COL] = pd.to_datetime(df[TS_COL], utc=True, errors="coerce")
    return df


def _normalize_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return cast(datetime, pd.to_datetime(value, utc=True).to_pydatetime())
    except Exception:
        return None


def _end_of_date_exclusive(end_dt: datetime) -> pd.Timestamp:
    """Treat YYYY-MM-DD end dates as inclusive through 23:59:59 UTC."""
    ts = pd.Timestamp(end_dt)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts + pd.Timedelta(days=1)


class ErcotService:
    """Service wrapper bound to the app configuration."""

    def __init__(
        self,
        dataset_id: str | None,
        deployment_id: str | None,
        datarobot_endpoint: str,
        datarobot_api_token: str,
        default_tavily_api_key: str | None = None,
    ) -> None:
        self.dataset_id = dataset_id
        self.deployment_id = deployment_id
        self.datarobot_endpoint = datarobot_endpoint
        self.datarobot_api_token = datarobot_api_token
        self.default_tavily_api_key = default_tavily_api_key

    # ---- data access -----------------------------------------------------
    def _dataframe(self) -> pd.DataFrame:
        if not self.dataset_id:
            raise ErcotDataError(
                "No ERCOT dataset configured (set ERCOT_DATASET_ID runtime parameter)."
            )
        try:
            return _load_dataset_cached(
                self.dataset_id, self.datarobot_endpoint, self.datarobot_api_token
            ).copy()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to load ERCOT dataset")
            raise ErcotDataError(f"Failed to load ERCOT dataset: {exc}") from exc

    def get_prices(
        self,
        hubs: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return historical DAM prices + features filtered by hub and date."""
        df = self._dataframe()

        if hubs:
            wanted = {h.upper() for h in hubs}
            df = df[df[HUB_COL].astype(str).str.upper().isin(wanted)]

        end_dt = _normalize_date(end_date)
        if end_dt is None and TS_COL in df.columns and not df.empty:
            end_dt = df[TS_COL].max().to_pydatetime()
        start_dt = _normalize_date(start_date)
        if start_dt is None and end_dt is not None:
            start_dt = end_dt - timedelta(days=30)

        if TS_COL in df.columns:
            if start_dt is not None:
                df = df[df[TS_COL] >= pd.Timestamp(start_dt)]
            if end_dt is not None:
                df = df[df[TS_COL] < _end_of_date_exclusive(end_dt)]
            df = df.sort_values(TS_COL)

        return self._records(df)

    @staticmethod
    def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
        out = df.copy()
        if TS_COL in out.columns:
            out[TS_COL] = out[TS_COL].apply(
                lambda v: v.isoformat() if pd.notna(v) else None
            )
        out = out.where(pd.notna(out), None)
        return cast(list[dict[str, Any]], out.to_dict(orient="records"))

    # ---- predictions (time-series historical backtest) -------------------
    def predict_history(
        self,
        hub: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """Run a historical time-series backtest for one hub.

        The deployment is a multiseries 24h-ahead forecast model (feature
        derivation window -168h, forecast window +1..24h). To compare forecasts
        against actuals, we submit the hub's full history and request historical
        predictions across the requested date range, then keep the 1-step-ahead
        (FORECAST_DISTANCE == 1) prediction per timestamp.
        """
        if not self.deployment_id:
            raise ErcotDataError(
                "No ERCOT deployment configured (set ERCOT_DEPLOYMENT_ID runtime parameter)."
            )

        # Preserve original timestamp strings for the model's expected format.
        raw = _load_dataset_cached(
            self.dataset_id or "",
            self.datarobot_endpoint,
            self.datarobot_api_token,
        )
        hub_mask = raw[HUB_COL].astype(str).str.upper() == hub.upper()
        sub = raw[hub_mask].copy()
        if sub.empty:
            return []

        # Determine the historical prediction window (default: last 30 days of data).
        ts = pd.to_datetime(sub[TS_COL], utc=True, errors="coerce")
        data_end = ts.max()
        end_dt = _normalize_date(end_date) or (
            data_end.to_pydatetime() if pd.notna(data_end) else None
        )
        start_dt = _normalize_date(start_date)
        if start_dt is None and end_dt is not None:
            start_dt = end_dt - timedelta(days=30)

        try:
            import datarobot as dr
            from datarobot import BatchPredictionJob

            dr.Client(endpoint=self.datarobot_endpoint, token=self.datarobot_api_token)

            # Send timestamps in the exact format the model was trained on
            # ("%Y-%m-%d %H:%M:%S", no timezone offset). The cached loader parses
            # timestamps to datetimes, so reformat them back to naive strings.
            sub_out = sub.copy()
            sub_out[TS_COL] = (
                pd.to_datetime(sub_out[TS_COL], utc=True, errors="coerce")
                .dt.tz_localize(None)
                .dt.strftime("%Y-%m-%d %H:%M:%S")
            )
            csv_in = sub_out.to_csv(index=False).encode("utf-8")

            ts_settings: dict[str, Any] = {
                "type": "historical",
                "relax_known_in_advance_features_check": True,
            }
            if start_dt is not None:
                ts_settings["predictions_start_date"] = _to_dr_datetime(start_dt)
            if end_dt is not None:
                last_hour = _end_of_date_exclusive(end_dt) - pd.Timedelta(hours=1)
                ts_settings["predictions_end_date"] = _to_dr_datetime(
                    last_hour.to_pydatetime()
                )

            job = BatchPredictionJob.score(
                deployment=self.deployment_id,
                intake_settings={"type": "localFile", "file": io.BytesIO(csv_in)},  # type: ignore[arg-type]
                output_settings={"type": "localFile", "path": None},  # type: ignore[arg-type]
                timeseries_settings=ts_settings,  # type: ignore[arg-type]
            )
            job.wait_for_completion()
            buf = io.BytesIO()
            job.download(buf)
            buf.seek(0)
            preds_df = pd.read_csv(buf)
        except Exception as exc:  # noqa: BLE001
            logger.exception("ERCOT time-series prediction failed")
            raise ErcotDataError(f"Deployment prediction failed: {exc}") from exc

        pred_col = self._detect_prediction_column(preds_df)
        # Keep 1-step-ahead forecast per timestamp for a clean vs-actual line.
        if "FORECAST_DISTANCE" in preds_df.columns:
            preds_df = preds_df[preds_df["FORECAST_DISTANCE"] == 1]

        preds_df = preds_df.copy()
        preds_df["_join_ts"] = pd.to_datetime(
            preds_df[TS_COL], utc=True, errors="coerce"
        )

        # Keep only the requested comparison window (batch output can be wider).
        if start_dt is not None:
            preds_df = preds_df[preds_df["_join_ts"] >= pd.Timestamp(start_dt)]
        if end_dt is not None:
            preds_df = preds_df[preds_df["_join_ts"] < _end_of_date_exclusive(end_dt)]
        preds_df = preds_df.drop_duplicates(subset=["_join_ts"], keep="first")

        result: list[dict[str, Any]] = []
        for _, row in preds_df.iterrows():
            join_ts = row["_join_ts"]
            result.append(
                {
                    TS_COL: join_ts.isoformat() if pd.notna(join_ts) else None,
                    HUB_COL: hub,
                    "predicted_dam_price_usd_mwh": _to_float(row.get(pred_col)),
                }
            )
        return result

    @staticmethod
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
        # Fall back to any column ending in _PREDICTION, then first numeric.
        for col in preds_df.columns:
            if str(col).endswith("_PREDICTION"):
                return str(col)
        for col in preds_df.columns:
            if pd.api.types.is_numeric_dtype(preds_df[col]):
                return str(col)
        raise ErcotDataError("Could not locate prediction column in deployment output.")

    # ---- accuracy metrics ------------------------------------------------
    def accuracy_metrics(
        self,
        actuals: list[dict[str, Any]],
        predictions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Compute RMSE/MAE/Max Error and a per-point error series with 90% CI."""
        a = pd.DataFrame(actuals)
        p = pd.DataFrame(predictions)
        if a.empty or p.empty:
            return {
                "metrics": {"rmse": None, "mae": None, "max_error": None},
                "error_series": [],
            }

        # Normalize timestamps to a common UTC key so ISO strings with/without
        # offsets join correctly.
        a["_join_ts"] = pd.to_datetime(a[TS_COL], utc=True, errors="coerce")
        p["_join_ts"] = pd.to_datetime(p[TS_COL], utc=True, errors="coerce")
        a["_hub"] = a[HUB_COL].astype(str).str.upper()
        p["_hub"] = p[HUB_COL].astype(str).str.upper()

        merged = a.merge(
            p[["_join_ts", "_hub", "predicted_dam_price_usd_mwh"]],
            on=["_join_ts", "_hub"],
            how="inner",
        )
        merged = merged.drop_duplicates(subset=["_join_ts", "_hub"], keep="first")
        merged["actual"] = merged[PRICE_COL].apply(_to_float)
        merged["predicted"] = merged["predicted_dam_price_usd_mwh"].apply(_to_float)
        merged = merged.dropna(subset=["actual", "predicted"])
        if merged.empty:
            return {
                "metrics": {"rmse": None, "mae": None, "max_error": None},
                "error_series": [],
            }

        merged["error"] = merged["predicted"] - merged["actual"]
        merged["abs_error"] = merged["error"].abs()

        rmse = float(math.sqrt((merged["error"] ** 2).mean()))
        mae = float(merged["abs_error"].mean())
        max_error = float(merged["abs_error"].max())

        # 90% CI band around the prediction using +/- 1.645 * residual std.
        resid_std = float(merged["error"].std(ddof=1)) if len(merged) > 1 else 0.0
        half_width = 1.645 * resid_std

        merged = merged.sort_values("_join_ts")
        series: list[dict[str, Any]] = []
        for _, row in merged.iterrows():
            series.append(
                {
                    TS_COL: row["_join_ts"].isoformat()
                    if pd.notna(row["_join_ts"])
                    else None,
                    HUB_COL: row[HUB_COL],
                    "actual": _to_float(row["actual"]),
                    "predicted": _to_float(row["predicted"]),
                    "error": _to_float(row["error"]),
                    "abs_error": _to_float(row["abs_error"]),
                    "ci_lower": _to_float(row["predicted"] - half_width),
                    "ci_upper": _to_float(row["predicted"] + half_width),
                }
            )
        return {
            "metrics": {"rmse": rmse, "mae": mae, "max_error": max_error},
            "error_series": series,
        }

    def get_forecast_vs_actual(
        self,
        hub: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """End-to-end: fetch actuals, run TS backtest, and compute metrics."""
        actuals = self.get_prices([hub], start_date, end_date)
        predictions = self.predict_history(hub, start_date, end_date)
        if not actuals or not predictions:
            return {
                "metrics": {"rmse": None, "mae": None, "max_error": None},
                "error_series": [],
            }
        return self.accuracy_metrics(actuals, predictions)

    # ---- root cause ------------------------------------------------------
    def investigate(
        self,
        timestamp_utc: str,
        hub_name: str,
        tavily_api_key: str | None = None,
        actual: float | None = None,
        predicted: float | None = None,
        action: str | None = None,
    ) -> dict[str, Any]:
        """Gather feature context, classify the miss, and return agentic follow-ups."""
        df = self._dataframe()
        point = self._nearest_point(df, timestamp_utc, hub_name)
        context_features = {
            k: _to_float(v) if isinstance(v, (int, float)) else v
            for k, v in point.items()
            if any(hint in k for hint in CONTEXT_FEATURE_HINTS)
        }

        drivers = _driver_summary(point)
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
            action_result = start_retrain(
                endpoint=self.datarobot_endpoint,
                token=self.datarobot_api_token,
                dataset_id=self.dataset_id,
                deployment_id=self.deployment_id,
                hub_name=hub_name,
                error_mode=error_mode,
            )
            if action == "recommend_retrain":
                action_result["recommendations"] = retrain_recommendations(
                    error_mode, hub_name
                )
        elif action == "focus_wind":
            wind = drivers.get("wind") or {}
            lines = []
            if wind.get("actual_mw") is not None and wind.get("forecast_mw") is not None:
                lines.append(
                    f"Wind forecast error: {wind.get('delta_mw', 0):+.0f} MW "
                    f"(actual {wind['actual_mw']:.0f} vs forecast {wind['forecast_mw']:.0f})."
                )
            action_result = {"type": "focus_wind", "wind": wind, "narrative": lines}

        factors: list[dict[str, Any]] = []
        key = tavily_api_key or self.default_tavily_api_key
        if key:
            try:
                from tavily import TavilyClient

                client = TavilyClient(api_key=key)
                query = (
                    f"ERCOT {hub_name} day-ahead electricity price drivers "
                    f"weather grid renewable generation around {timestamp_utc}"
                )
                resp = client.search(query=query, max_results=5, topic="news")
                for item in resp.get("results", []):
                    factors.append(
                        {
                            "factor": item.get("title", "News"),
                            "evidence": item.get("content", "")[:400],
                            "source_url": item.get("url"),
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Tavily search failed: %s", exc)

        return {
            "timestamp_utc": timestamp_utc,
            "hub_name": hub_name,
            "context_features": context_features,
            "contributing_factors": factors,
            "error_mode": error_mode,
            "error_mode_label": ERROR_MODES.get(error_mode, error_mode),
            "narrative": narrative,
            "recommended_actions": actions,
            "driver_summary": drivers,
            "action_result": action_result,
        }

    @staticmethod
    def _nearest_point(
        df: pd.DataFrame, timestamp_utc: str, hub_name: str
    ) -> dict[str, Any]:
        subset = df[df[HUB_COL].astype(str).str.upper() == hub_name.upper()]
        target = _normalize_date(timestamp_utc)
        if subset.empty or target is None or TS_COL not in subset.columns:
            return {}
        subset = subset.assign(
            _delta=(subset[TS_COL] - pd.Timestamp(target)).abs()
        ).sort_values("_delta")
        row = subset.iloc[0].drop(labels=["_delta"]).to_dict()
        if isinstance(row.get(TS_COL), pd.Timestamp):
            row[TS_COL] = row[TS_COL].isoformat()
        return cast(dict[str, Any], row)


def _to_dr_datetime(dt: datetime) -> str:
    """Format a datetime for DataRobot time-series prediction date bounds."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_float(value: Any) -> float | None:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
