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
import logging
from typing import Any

from datarobot.auth.session import AuthCtx
from datarobot.auth.typing import Metadata
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.auth.ctx import must_get_auth_ctx
from app.ercot.service import HUBS, ErcotDataError, ErcotService

logger = logging.getLogger(__name__)
ercot_router = APIRouter(tags=["ERCOT"], prefix="/ercot")


def _service(request: Request) -> ErcotService:
    config = request.app.state.deps.config
    return ErcotService(
        dataset_id=config.ercot_dataset_id,
        deployment_id=config.ercot_deployment_id,
        datarobot_endpoint=config.datarobot_endpoint,
        datarobot_api_token=config.datarobot_api_token,
        default_tavily_api_key=config.tavily_api_key,
    )


class PriceResponse(BaseModel):
    hubs: list[str]
    records: list[dict[str, Any]]


class ForecastVsActualResponse(BaseModel):
    hub: str
    metrics: dict[str, float | None]
    error_series: list[dict[str, Any]]


class InvestigateRequest(BaseModel):
    timestamp_utc: str
    hub_name: str
    tavily_api_key: str | None = None
    actual: float | None = None
    predicted: float | None = None
    action: str | None = None


class RecommendedAction(BaseModel):
    id: str
    label: str
    description: str


class InvestigateResponse(BaseModel):
    timestamp_utc: str
    hub_name: str
    context_features: dict[str, Any]
    contributing_factors: list[dict[str, Any]]
    error_mode: str
    error_mode_label: str
    narrative: list[str]
    recommended_actions: list[RecommendedAction]
    driver_summary: dict[str, Any]
    action_result: dict[str, Any] | None = None


@ercot_router.get("/hubs")
async def list_hubs(
    auth_ctx: AuthCtx[Metadata] = Depends(must_get_auth_ctx),
) -> list[str]:
    """Return the available ERCOT trading hubs."""
    return HUBS


@ercot_router.get("/prices")
async def get_prices(
    request: Request,
    hubs: list[str] | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    auth_ctx: AuthCtx[Metadata] = Depends(must_get_auth_ctx),
) -> PriceResponse:
    """Historical DAM prices + features for the given hubs and date range."""
    try:
        records = _service(request).get_prices(hubs, start_date, end_date)
    except ErcotDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return PriceResponse(hubs=hubs or HUBS, records=records)


@ercot_router.get("/forecast-vs-actual")
async def forecast_vs_actual(
    request: Request,
    hub: str = Query(...),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    auth_ctx: AuthCtx[Metadata] = Depends(must_get_auth_ctx),
) -> ForecastVsActualResponse:
    """Forecast vs actual prices + accuracy metrics for a single hub."""
    try:
        result = _service(request).get_forecast_vs_actual(hub, start_date, end_date)
    except ErcotDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ForecastVsActualResponse(
        hub=hub,
        metrics=result["metrics"],
        error_series=result["error_series"],
    )


@ercot_router.post("/investigate")
async def investigate(
    request: Request,
    body: InvestigateRequest,
    auth_ctx: AuthCtx[Metadata] = Depends(must_get_auth_ctx),
) -> InvestigateResponse:
    """Root-cause investigation and agentic follow-ups for a forecast miss."""
    try:
        result = _service(request).investigate(
            body.timestamp_utc,
            body.hub_name,
            tavily_api_key=body.tavily_api_key,
            actual=body.actual,
            predicted=body.predicted,
            action=body.action,
        )
    except ErcotDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return InvestigateResponse(**result)
