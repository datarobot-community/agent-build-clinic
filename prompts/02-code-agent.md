# Prompt 2 — Code the Agent

**Agent Assist phase:** Option 2 — Code an AI agent

Paste this after Prompt 1 is complete and `agent_spec.md` exists in your project. Implement the full application from the spec. **Do not deploy.** **Do not run `dr run dev` yet** — the instructor will have you configure `.env` manually before local testing.

---

## Your task

Implement the ABC Forecast App by adapting the DataRobot agent application template to match `agent_spec.md`. Code the agent, backend, and frontend. Run linters/tests where possible, but **stop before local runtime** — participants configure `.env` separately.

---

## Template conventions (mandatory)

- Framework: LangGraph — `MyAgent` via `datarobot_agent_class_from_langgraph` — **do not rename**
- LLM: `get_llm()` from `datarobot_genai.langgraph.llm` — never instantiate LLMs directly
- Agent code: modify ONLY `agent/agent/`
- Backend: `fastapi_server/`
- Frontend: `frontend_web/` — React + TypeScript + Vite + Tailwind + shadcn/ui + Recharts
- Do not switch frameworks (no Next.js, Vue, etc.)
- Global MCP via `mcp_tools_context` in `custompy_adaptor` — no local `mcp_server/`
- ERCOT forecasts: `predict_dam_prices` with BatchPredictionJob — NOT Global MCP prediction tools

After agent dependency changes: `dr task run agent:install`

---

## Part A — Agent (`agent/agent/`)

### `ercot_tools.py` — 5 LangChain tools

#### `get_dam_prices(hubs?, start_date?, end_date?)`

- Download CSV: `GET datasets/{ERCOT_DATASET_ID}/file/` via datarobot client
- Cache with `lru_cache`; filter hubs and dates; default last 30 days
- Return records with `timestamp_utc` (ISO), `hub_name`, `dam_price_usd_mwh`, features

#### `predict_dam_prices(hub, forecast_origin_date?, start_date?, end_date?)`

**CRITICAL:** BatchPredictionJob only.

```python
BatchPredictionJob.score(
    deployment=os.getenv("ERCOT_DEPLOYMENT_ID"),
    intake_settings={"type": "localFile", "file": csv_bytes},
    output_settings={"type": "localFile", "path": None},
    timeseries_settings={
        "type": "historical",
        "relax_known_in_advance_features_check": True,
        "predictions_start_date": "...",
        "predictions_end_date": "...",
    },
)
```

- Scoring timestamps: `"%Y-%m-%d %H:%M:%S"` (naive, no TZ)
- Modes: `forward_24h` (default, 24 hourly FD=1 predictions) and `backtest` (start_date/end_date)
- Detect prediction column: `dam_price_usd_mwh (actual)_PREDICTION` or `*_PREDICTION`

#### `compute_accuracy_metrics(actuals, predictions)`

- Inner join on timestamp + hub; RMSE, MAE, max abs error
- error_series with 90% CI (1.645 × residual std)

#### `analyze_forecast_miss(timestamp_utc, hub_name, actual?, predicted?, action?)`

- Classify: renewable_shortfall, load_surprise, price_spike, model_bias, mixed_drivers
- Narrative from wind/solar/load drivers
- Actions: compare_hubs, driver_window, start_retrain, focus_wind

#### `investigate_forecast_error(timestamp_utc, hub_name)`

- Return nearest row's weather/grid/renewable/load features

Export: `ERCOT_TOOLS = [get_dam_prices, predict_dam_prices, compute_accuracy_metrics, analyze_forecast_miss, investigate_forecast_error]`

### `miss_analysis.py`

Rule-based: `classify_miss`, `build_narrative`, `recommended_actions`, `compare_hubs_at_timestamp`, `driver_window`, `retrain_recommendations`, `ERROR_MODES`.

### `retrain_service.py`

`start_retrain()` → platform deep links (dataset, deployment, retraining, project); optional Autopilot project creation.

### `myagent.py`

- `ERCOT_SYSTEM_PROMPT` with configured dataset/deployment IDs and tool-use rules
- `graph_factory`: single `create_agent` node with `[*ERCOT_TOOLS, *mcp_tools]`
- `MyAgent = datarobot_agent_class_from_langgraph(graph_factory, prompt_template)`
- `custompy_adaptor`: wire MCPConfig + `get_llm()` + `agent_chat_completion_wrapper`

Run: `dr task run agent:lint` and `dr task run agent:test`

---

## Part B — Backend (`fastapi_server/`)

### Config (`app/config.py`)

Add: `ercot_deployment_id`, `ercot_dataset_id`, `tavily_api_key`

### Service (`app/ercot/service.py`)

`ErcotService` with:

- `get_prices()` — same logic as get_dam_prices
- `predict_history()` — BatchPredictionJob backtest, FORECAST_DISTANCE=1
- `get_forecast_vs_actual()` — predict + actuals + accuracy metrics
- `investigate()` — miss analysis + optional Tavily search

Copy `miss_analysis.py` and `retrain_service.py` under `app/ercot/`.

### Router (`app/api/v1/ercot.py`)

| Method | Path | Notes |
|--------|------|-------|
| GET | `/ercot/hubs` | List hubs |
| GET | `/ercot/prices` | Query: hubs, start_date, end_date |
| GET | `/ercot/forecast-vs-actual` | Query: hub, start_date, end_date (1–2 min) |
| POST | `/ercot/investigate` | Body: timestamp_utc, hub_name, tavily_api_key?, actual?, predicted?, action? |

Register in `app/api/v1/__init__.py`. Ensure infra passes ERCOT_* as runtime parameters.

Run: `dr task run fastapi_server:lint` and `dr task run fastapi_server:test`

---

## Part C — Frontend (`frontend_web/`)

### Routes

- `/chat` → ForecastAssistantPage (default)
- `/analyst` → AnalystPage

### Design tokens (`components/forecast/tokens.ts`)

```
appBg: #191D21    surface: #23272B    border: #2B3036    borderStrong: #40454C
textPrimary: #F5F5F5    textMuted: #9AA0A6    accentActiveTab: #A9B0F2
periwinkle: #929BEF    mint: #7EDC92    sky: #69BDF7    lime: #CCFB8E
orange: #D5772F    coral: #C17B75    idleBtnBg: #40454C    idleBtnText: #9197A0
```

Hub line colors: HOUSTON=mint, NORTH=sky, SOUTH=periwinkle, WEST=lime

### AppShell

Header: DataRobot logo mark (3 bars) + wordmark; two pill tabs (Forecast Assistant, AI Analyst); per-page `rightSlot`.

### Tab 1 — Forecast Assistant

- **63% left:** AG-UI chat trace (YOU / AGENT / TOOL labels), streaming, greeting, input bar, Send button
- **37% right:** Panels workspace — chart + table bundles from `get_dam_prices` and `predict_dam_prices` tool results
- `useForecastChat.ts`: HttpAgent, subscribe to tool results, `panelFromDamPricesResult` / `panelFromPredictionsResult`
- ChartPanel: Recharts multi-line, overlaid legend, "DAM Price (USD/MWh)"
- TablePanel: filterable columns, pagination 20/page

### Tab 2 — AI Analyst

- Filter bar: hub select, start/end date, optional Tavily key, Update button
- Forecast vs Actual chart: actual (orange solid), predicted (periwinkle dashed), CI band (gray dashed), clickable dots (yellow selected, red if abs_error ≥ 20)
- Badges: RMSE (mint), MAE (neutral), Max Error (coral)
- Click point → callout → POST /investigate → streamed narrative + action buttons
- API: `src/api/ercot/` — paths `/v1/ercot/...` (apiClient baseURL already includes `/api`)

Install missing shadcn components before importing. Run: `dr task run frontend_web:lint` and `dr task run frontend_web:test`

---

## Stop — do not run locally yet

When implementation is complete:

1. Confirm linters/tests pass
2. **Wait for instructor** — participants will manually configure `.env` (see instructor handout)
3. Then run `dr run dev` from project root to test locally

Do not run `dr run dev`, `dr task run infra:up-yes`, or deploy until `.env` is configured.
