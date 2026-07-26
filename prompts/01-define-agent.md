# Prompt 1 — Define the Agent

**Agent Assist phase:** Option 1 — Design an AI agent

Paste this into your LLM (or use Agent Assist design mode). The output should be a complete `agent_spec.md` at your project root. Do not write implementation code in this step.

---

## Your task

Design the **ABC Forecast App** — an ERCOT Day-Ahead Market (DAM) forecasting agent for a DataRobot Agent Build Clinic. Produce a complete `agent_spec.md` in YAML format covering the model, system prompt, tools, examples, and frontend requirements.

Write the spec to `agent_spec.md` and display it as YAML. Iterate with the user until the spec is approved, then stop. **Do not proceed to coding.**

---

## Application overview

A multi-page DataRobot agent application (LangGraph + FastAPI + React) that helps energy traders:

- Chat about ERCOT day-ahead hub prices ($/MWh)
- Retrieve historical prices and render chart/table panels
- Run 24-hour-ahead forecasts against a deployed time-series model
- Compare forecast vs actual with RMSE, MAE, Max Error
- Investigate forecast misses with driver analysis and follow-up actions

**App title:** ABC Forecast App (Agent Build Clinic)

---

## ERCOT domain context

- ERCOT manages ~90% of Texas electric load
- Day-Ahead Market (DAM) prices are set 24 hours ahead
- Trading hubs: `HB_HOUSTON`, `HB_NORTH`, `HB_SOUTH`, `HB_WEST` (UI may also show `HB_BUSAVG`)
- Target column: `dam_price_usd_mwh`
- Key dataset columns: `timestamp_utc`, `hub_name`, city weather features (temperature, humidity, precipitation, windspeed), `solar_actual_mw`, `solar_forecast_mw`, `wind_forecast_mw`, `load_forecast_mw`
- All timestamps UTC unless noted; prices in USD/MWh

---

## Architecture decisions (must be reflected in spec)

| Decision | Choice |
|----------|--------|
| Framework | LangGraph via DataRobot agent template |
| MCP | **DataRobot Global MCP** — NOT a standalone `mcp_server/` deployment |
| ERCOT forecasts | Custom tool `predict_dam_prices` using **BatchPredictionJob** against `ERCOT_DEPLOYMENT_ID` — NOT Global MCP generic prediction tools |
| Historical data | Custom tool `get_dam_prices` reading `ERCOT_DATASET_ID` from AI Catalog |
| UI tabs | Two only: Forecast Assistant + AI Analyst (no Panel Workspace tab) |

### Clinic env mapping (document in frontend.requirements)

| Clinic notebook variable | App env variable | Purpose |
|--------------------------|------------------|---------|
| `FORECAST_DEPLOYMENT_ID` | `ERCOT_DEPLOYMENT_ID` | Time-series forecast deployment |
| `ERCOT_TRAINING_DATASET_ID` | `ERCOT_DATASET_ID` | Historical DAM + weather data |
| `SCORING_DATASET_ID` | — | Not required in app `.env` |
| `MCP_DEPLOYMENT_ID` | **NOT USED** | Replaced by Global MCP |

Clinic POV example IDs (instructor provides actual values):

- `ERCOT_DATASET_ID=698dfe27b04f8da88246bc28` (or `6a6169d0d26541f54266b049`)
- `ERCOT_DEPLOYMENT_ID=698e049a2720aafce2802a0c`

Also document required runtime config: `EXTERNAL_MCP_URL`, `EXTERNAL_MCP_HEADERS`, optional `TAVILY_API_KEY`.

---

## Required tools (5)

### 1. `get_dam_prices`

Retrieve historical ERCOT DAM prices and weather/grid features from the AI Catalog dataset.

- **Inputs:** `hubs` (list, optional), `start_date` (YYYY-MM-DD), `end_date` (YYYY-MM-DD)
- **Output:** `records` — list with `timestamp_utc`, `hub_name`, `dam_price_usd_mwh`, weather/grid features
- **Auth:** DataRobot AI Catalog API key
- **Default:** last 30 days when no range specified
- **UI:** Powers Forecast Assistant chart + table panels

### 2. `predict_dam_prices`

Get 24h-ahead DAM price predictions via batch time-series scoring against the configured deployment.

- **Inputs:** `hub` (str), `forecast_origin_date` (optional YYYY-MM-DD), `start_date` / `end_date` (optional, for backtest mode)
- **Output:** `predictions` — list with `timestamp_utc`, `hub_name`, `predicted_dam_price_usd_mwh`
- **Auth:** DataRobot API key (deployment scoring)
- **Critical:** Must use BatchPredictionJob with time-series historical settings — do NOT specify Global MCP prediction tools in the implementation

### 3. `compute_accuracy_metrics`

Compute RMSE, MAE, Max Error and per-point error series with 90% confidence interval.

- **Inputs:** `actuals` (list), `predictions` (list)
- **Output:** `metrics` (dict), `error_series` (list with actual, predicted, error, ci_lower, ci_upper)

### 4. `analyze_forecast_miss`

Classify a forecast miss, build narrative from wind/solar/load drivers, return recommended follow-up actions.

- **Inputs:** `timestamp_utc`, `hub_name`, `actual`, `predicted`, `action` (optional: compare_hubs, driver_window, start_retrain, focus_wind)
- **Output:** `narrative`, `recommended_actions`, `driver_summary`, `action_result`

### 5. `investigate_forecast_error`

Gather feature context for a forecast point; optional Tavily web search in backend.

- **Inputs:** `timestamp_utc`, `hub_name`
- **Output:** `context_features`, `contributing_factors`

---

## System prompt requirements

The system prompt must instruct the agent to:

1. Answer ERCOT/DAM questions with clear explanations
2. Always call `get_dam_prices` for historical data, charts, and tables
3. Always call `predict_dam_prices` for forward-looking forecasts — never Global MCP prediction tools
4. Use `compute_accuracy_metrics` for RMSE/MAE/Max Error
5. Use `analyze_forecast_miss` when asked why a forecast was wrong
6. Ground every numeric claim in tool results; cite hub and time window
7. Report tool failures plainly; do not guess

---

## Frontend requirements

```yaml
frontend:
  type: "multi-page"
  pages:
    - "Forecast Assistant — chat-first AG-UI trace; right-hand Panels workspace renders charts/tables from get_dam_prices and predict_dam_prices tool results"
    - "AI Analyst — hub + date range filters, optional Tavily API key, Forecast vs Actual chart (actual/predicted/90% CI), RMSE/MAE/Max Error badges; click forecast points for miss investigation with streamed narrative and agentic follow-up actions"
  requirements: >
    Dark DataRobot-themed UI. Two tabs only. Tab 1: 63% chat / 37% panels.
    Tab 2: filter bar, batch forecast chart (1-2 min load), clickable predicted dots,
    root-cause narrative, recommended action buttons (compare hubs, driver window, retrain).
    Design tokens: appBg #191D21, surface #23272B, accentActiveTab #A9B0F2,
    periwinkle #929BEF, mint #7EDC92, orange #D5772F (actual line), coral #C17B75.
```

---

## Example user queries

- "Forecast the next 24 hours of ERCOT day-ahead prices on 2025-10-20 for HB_HOUSTON and display as chart"
- "Create a chart panel of ERCOT day-ahead prices for HB_HOUSTON"
- "What is the average dam_price_usd_mwh for all hubs?"
- "How accurate has the forecast been for HB_SOUTH this month? Show RMSE, MAE, and Max Error."

---

## Model

Use: `datarobot/anthropic/claude-sonnet-4-5-20250929` (or equivalent from LLM Gateway catalog)

---

## When done

Display the complete `agent_spec.md` as YAML. Confirm the user is satisfied with the spec.

**Stop here.** The next step is coding (Prompt 2), not deployment. Environment configuration happens after coding, before local testing.
