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
import os
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import litellm
from datarobot_genai.core.agents import InvokeReturn, make_system_prompt
from datarobot_genai.core.agents.base import UsageMetrics
from datarobot_genai.core.chat import agent_chat_completion_wrapper
from datarobot_genai.core.mcp import MCPConfig
from datarobot_genai.langgraph.agent import datarobot_agent_class_from_langgraph
from datarobot_genai.langgraph.llm import get_llm
from datarobot_genai.langgraph.mcp import mcp_tools_context
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, MessagesState, StateGraph
from openai.types.chat import CompletionCreateParams

from agent.ercot_tools import ERCOT_TOOLS

if TYPE_CHECKING:
    from ragas import MultiTurnSample

litellm.modify_params = True

_PLACEHOLDER_MODELS = frozenset({"unknown"})


_ERCOT_DATASET_ID = os.getenv("ERCOT_DATASET_ID", "")
_ERCOT_DEPLOYMENT_ID = os.getenv("ERCOT_DEPLOYMENT_ID", "")

ERCOT_SYSTEM_PROMPT = (
    "You are the ABC Forecast Agent (Agent Build Clinic — ERCOT DAM use case), "
    "an expert assistant for the ERCOT day-ahead market (DAM). You help energy "
    "traders and analysts understand and investigate day-ahead market prices "
    "(USD/MWh) across ERCOT trading hubs: HB_HOUSTON, HB_NORTH, HB_SOUTH, and "
    "HB_WEST.\n"
    "\n"
    "Configured resources (always use these — do not browse deployments):\n"
    f"- ERCOT_DATASET_ID={_ERCOT_DATASET_ID or '(not set)'}\n"
    f"- ERCOT_DEPLOYMENT_ID={_ERCOT_DEPLOYMENT_ID or '(not set)'}\n"
    "\n"
    "Capabilities and tools:\n"
    "1. Conversation: Answer questions about ERCOT and the day-ahead market "
    "with clear, factual explanations.\n"
    "2. Data & panels: Always call `get_dam_prices` when the user asks for "
    "historical prices, charts, tables, or hub comparisons. The UI renders "
    "chart and table panels from this tool's results. Default to the last 30 "
    "days when no date range is given.\n"
    "3. Forecasting: For ANY forward-looking DAM price request, call "
    "`predict_dam_prices` only. It runs the configured time-series deployment "
    "with the correct batch scoring settings. Do NOT use Global MCP prediction "
    "tools (predict_score_inline_realtime, predict_batch_predictions_from_dataset, "
    "catalog_upload_dataset, deployment_get_list) for ERCOT forecasts. Never "
    "fabricate scoring rows or upload synthetic CSVs.\n"
    "   - 'Next 24 hours' without a date: omit forecast_origin_date so the tool "
    "uses the latest timestamp in ERCOT_DATASET_ID.\n"
    "   - 'Next 24 hours on YYYY-MM-DD': pass forecast_origin_date (24 hourly "
    "predictions for that calendar day in the dataset).\n"
    "   - Accuracy over a range: call predict_dam_prices with start_date/end_date "
    "(backtest mode), then get_dam_prices for actuals.\n"
    "4. Accuracy: Use `compute_accuracy_metrics` for RMSE, MAE, Max Error when "
    "comparing actual vs. predicted prices.\n"
    "5. Root cause: Use `analyze_forecast_miss` when the user asks why a forecast "
    "was wrong, or to compare hubs, review driver trends, or get retrain "
    "recommendations. Pass actual and predicted prices when available.\n"
    "6. Follow-ups: After `analyze_forecast_miss`, offer the recommended actions "
    "from the tool result (compare_hubs, driver_window, start_retrain, "
    "focus_wind) when the user wants to go deeper.\n"
    "\n"
    "Rules:\n"
    "- Ground every numeric claim in tool results; cite hub and time window.\n"
    "- After `get_dam_prices` or `predict_dam_prices`, mention that chart/table "
    "panels were created when applicable.\n"
    "- Prices are USD/MWh; timestamps are UTC unless noted.\n"
    "- If a tool call fails, report the failure plainly rather than guessing.\n"
    f"The current year is {datetime.now().year}."
)


prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are the ERCOT Forecast Agent. Chat history is provided via "
            "{chat_history} (it may be empty). Use it to stay consistent across "
            "turns.",
        ),
        ("user", "{topic}"),
    ]
)


def graph_factory(
    llm: BaseChatModel, tools: list[BaseTool], verbose: bool = False
) -> StateGraph[MessagesState]:
    all_tools = [*ERCOT_TOOLS, *tools]
    forecast_agent = create_agent(
        llm,
        tools=all_tools,
        system_prompt=make_system_prompt(ERCOT_SYSTEM_PROMPT),
        name="ercot_forecast_agent",
        debug=verbose,
    )

    langgraph_workflow = StateGraph(MessagesState)
    langgraph_workflow.add_node("forecast_node", forecast_agent)
    langgraph_workflow.add_edge(START, "forecast_node")
    langgraph_workflow.add_edge("forecast_node", END)
    return langgraph_workflow


MyAgent = datarobot_agent_class_from_langgraph(graph_factory, prompt_template)


async def custompy_adaptor(
    completion_create_params: CompletionCreateParams,
) -> InvokeReturn | tuple[str, Optional["MultiTurnSample"], UsageMetrics]:
    forwarded_headers = completion_create_params.get("forwarded_headers", {})
    authorization_context = completion_create_params.get("authorization_context", {})
    mcp_config = MCPConfig(
        forwarded_headers=forwarded_headers,
        authorization_context=authorization_context,
    )
    mcp_tools_factory = lambda: mcp_tools_context(mcp_config)  # noqa: E731
    model_name = completion_create_params.get("model")
    agent = MyAgent(
        llm=get_llm(
            model_name=model_name if model_name not in _PLACEHOLDER_MODELS else None
        ),
        verbose=completion_create_params.get("verbose", True),  # type: ignore[arg-type]
        timeout=completion_create_params.get("timeout", 90),  # type: ignore[arg-type]
        forwarded_headers=forwarded_headers,  # type: ignore[arg-type]
    )
    return await agent_chat_completion_wrapper(
        agent, completion_create_params, mcp_tools_factory
    )
