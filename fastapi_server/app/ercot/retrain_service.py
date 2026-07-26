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
"""Start ERCOT model retraining and build DataRobot platform deep links."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_DATETIME_PARTITION_KEYS = (
    "useTimeSeries",
    "multiseriesIdColumns",
    "datetimePartitionColumn",
    "featureDerivationWindowStart",
    "featureDerivationWindowEnd",
    "forecastWindowStart",
    "forecastWindowEnd",
    "windowsBasisUnit",
    "gapDuration",
    "validationDuration",
    "numberOfBacktests",
    "featureSettings",
    "treatAsExponential",
    "autopilotDataSelectionMethod",
    "defaultToAPriori",
    "defaultToDoNotDerive",
    "useCrossSeriesFeatures",
    "allowPartialHistoryTimeSeriesPredictions",
)


def platform_base_url(datarobot_endpoint: str) -> str:
    return datarobot_endpoint.rstrip("/").removesuffix("/api/v2")


def build_platform_links(
    *,
    base_url: str,
    dataset_id: str | None,
    deployment_id: str | None,
    project_id: str | None = None,
) -> dict[str, str]:
    links: dict[str, str] = {}
    if dataset_id:
        links["dataset"] = f"{base_url}/ai-catalog/{dataset_id}"
    if deployment_id:
        links["deployment"] = f"{base_url}/console-nextgen/deployments/{deployment_id}/overview"
        links["deployment_retraining"] = (
            f"{base_url}/console-nextgen/deployments/{deployment_id}/retraining"
        )
    if project_id:
        links["project"] = f"{base_url}/projects/{project_id}/models"
    return links


def _client(endpoint: str, token: str):
    import datarobot as dr

    return dr.Client(endpoint=endpoint, token=token)


def _deployment_context(client, deployment_id: str) -> dict[str, Any]:
    deployment = client.get(f"deployments/{deployment_id}/").json()
    model = deployment.get("model") or {}
    return {
        "deployment_id": deployment_id,
        "deployment_label": deployment.get("label"),
        "model_id": model.get("id"),
        "project_id": model.get("projectId"),
        "project_name": model.get("projectName"),
        "target": model.get("targetName"),
    }


def _dataset_column_name(name: str) -> str:
    """Map champion project feature names back to AI Catalog dataset columns."""
    return name.replace(" (actual)", "").strip()


def _remap_partition_spec_for_dataset(spec: dict[str, Any]) -> dict[str, Any]:
    remapped = dict(spec)
    if remapped.get("datetimePartitionColumn"):
        remapped["datetimePartitionColumn"] = _dataset_column_name(
            str(remapped["datetimePartitionColumn"])
        )
    if remapped.get("multiseriesIdColumns"):
        remapped["multiseriesIdColumns"] = [
            _dataset_column_name(str(col)) for col in remapped["multiseriesIdColumns"]
        ]
    if remapped.get("featureSettings"):
        remapped["featureSettings"] = [
            {
                **entry,
                "featureName": _dataset_column_name(str(entry.get("featureName", ""))),
            }
            for entry in _sanitize_feature_settings(remapped["featureSettings"])
        ]
    return remapped


def _sanitize_feature_settings(settings: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for item in settings or []:
        entry = {k: v for k, v in item.items() if v is not None}
        if entry.get("knownInAdvance") and entry.get("aPriori"):
            entry.pop("aPriori", None)
        cleaned.append(entry)
    return cleaned


def _clone_datetime_partitioning(client, source_project_id: str) -> dict[str, Any]:
    payload = client.get(f"projects/{source_project_id}/datetimePartitioning/").json()
    spec = {k: payload[k] for k in _DATETIME_PARTITION_KEYS if k in payload}
    if "featureSettings" in spec:
        spec["featureSettings"] = _sanitize_feature_settings(spec["featureSettings"])
    return spec


def _wait_for_project_ready(client, project_id: str, timeout_sec: int = 300) -> None:
    """Wait until project EDA completes and modeling can start."""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        proj = client.get(f"projects/{project_id}/").json()
        stage = str(proj.get("stage") or "").lower()
        status = str(proj.get("status") or "").lower()
        if stage in {"aim", "modeling"} and status not in {"inprogress", "in_progress"}:
            return
        if proj.get("canSetTarget") is True:
            return
        time.sleep(5)
    raise TimeoutError(f"Project {project_id} did not become ready within {timeout_sec}s")


def _create_project_from_dataset(
    client,
    *,
    endpoint: str,
    token: str,
    dataset_id: str,
    project_name: str,
) -> str:
    """Create a project from AI Catalog dataset, bypassing invalid default use-case context."""
    import datarobot as dr
    from datarobot.context import Context

    dr.Client(endpoint=endpoint, token=token)
    saved_use_case = Context._use_case  # noqa: SLF001
    Context.use_case = None
    try:
        project = dr.Project.create_from_dataset(
            dataset_id,
            project_name=project_name,
            use_case=None,
        )
        return project.id
    finally:
        Context.use_case = saved_use_case


def _start_autopilot(
    client,
    *,
    project_id: str,
    champion_project_id: str,
    target: str,
) -> None:
    partition_spec = _remap_partition_spec_for_dataset(
        _clone_datetime_partitioning(client, champion_project_id)
    )
    project_meta = client.get(f"projects/{champion_project_id}/").json()
    partition = project_meta.get("partition") or {}
    if partition.get("datetimePartitionColumn"):
        partition_spec["datetimePartitionColumn"] = _dataset_column_name(
            str(partition["datetimePartitionColumn"])
        )
    if partition_spec.get("useTimeSeries"):
        client.post(
            f"projects/{project_id}/datetimePartitioning/",
            json=partition_spec,
        )
    client.post(
        f"projects/{project_id}/autopilots/",
        json={
            "target": _dataset_column_name(target),
            "mode": "quick",
            "blendBestModels": False,
        },
    )


def start_retrain(
    *,
    endpoint: str,
    token: str,
    dataset_id: str | None,
    deployment_id: str | None,
    hub_name: str,
    error_mode: str,
) -> dict[str, Any]:
    """Kick off retraining via Autopilot project creation (preferred) or policy run."""
    base_url = platform_base_url(endpoint)
    links = build_platform_links(
        base_url=base_url,
        dataset_id=dataset_id,
        deployment_id=deployment_id,
    )
    if not dataset_id:
        return {
            "type": "start_retrain",
            "status": "links_only",
            "message": "ERCOT_DATASET_ID is not configured — open the deployment to retrain manually.",
            "links": links,
        }
    if not deployment_id:
        return {
            "type": "start_retrain",
            "status": "links_only",
            "message": "ERCOT_DEPLOYMENT_ID is not configured — open the dataset to start a new project.",
            "links": links,
        }

    client = _client(endpoint, token)
    try:
        ctx = _deployment_context(client, deployment_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to load deployment context")
        return {
            "type": "start_retrain",
            "status": "failed",
            "message": f"Could not load deployment: {exc}",
            "links": links,
        }

    champion_project_id = ctx.get("project_id")
    target = ctx.get("target") or "dam_price_usd_mwh (actual)"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    project_name = f"ABC Forecast retrain — {hub_name} — {stamp}"

    # Primary path: new modeling project cloned from champion TS settings + Autopilot.
    project_id: str | None = None
    if champion_project_id:
        links["champion_project"] = f"{base_url}/projects/{champion_project_id}/models"
        try:
            project_id = _create_project_from_dataset(
                client,
                endpoint=endpoint,
                token=token,
                dataset_id=dataset_id,
                project_name=project_name,
            )
            _wait_for_project_ready(client, project_id)
            _start_autopilot(
                client,
                project_id=project_id,
                champion_project_id=champion_project_id,
                target=target,
            )
            project_links = build_platform_links(
                base_url=base_url,
                dataset_id=dataset_id,
                deployment_id=deployment_id,
                project_id=project_id,
            )
            project_links["champion_project"] = links["champion_project"]
            return {
                "type": "start_retrain",
                "status": "started",
                "method": "autopilot_project",
                "message": (
                    f"Started Autopilot on new project '{project_name}'. "
                    "Monitor progress in DataRobot — deploy the recommended model when complete."
                ),
                "project_id": project_id,
                "project_name": project_name,
                "target": _dataset_column_name(target),
                "links": project_links,
            }
        except Exception as exc:  # noqa: BLE001
            logger.exception("Autopilot project retrain failed")
            autopilot_error = str(exc)
            if project_id:
                project_links = build_platform_links(
                    base_url=base_url,
                    dataset_id=dataset_id,
                    deployment_id=deployment_id,
                    project_id=project_id,
                )
                project_links["champion_project"] = links["champion_project"]
                return {
                    "type": "start_retrain",
                    "status": "project_created",
                    "method": "autopilot_project",
                    "message": (
                        f"Created project '{project_name}'. "
                        "Open it in DataRobot to confirm time-series settings and start Autopilot."
                    ),
                    "project_id": project_id,
                    "project_name": project_name,
                    "target": _dataset_column_name(target),
                    "links": project_links,
                    "autopilot_error": autopilot_error,
                }
    else:
        autopilot_error = "Champion project id not found on deployment."

    return {
        "type": "start_retrain",
        "status": "links_only",
        "message": (
            "Could not start Autopilot automatically. "
            "Use the links below to open the dataset, champion project, or deployment retraining page."
        ),
        "links": links,
        "autopilot_error": autopilot_error,
    }
