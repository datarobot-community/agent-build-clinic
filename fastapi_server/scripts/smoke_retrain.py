"""Smoke-test retrain_service without printing secrets."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.ercot.retrain_service import start_retrain  # noqa: E402

if __name__ == "__main__":
    result = start_retrain(
        endpoint=os.environ["DATAROBOT_ENDPOINT"],
        token=os.environ["DATAROBOT_API_TOKEN"],
        dataset_id=os.environ.get("ERCOT_DATASET_ID"),
        deployment_id=os.environ.get("ERCOT_DEPLOYMENT_ID"),
        hub_name="HB_HOUSTON",
        error_mode="renewable_shortfall",
    )
    safe = {k: v for k, v in result.items() if k != "links"}
    safe["link_keys"] = list((result.get("links") or {}).keys())
    print(safe)
