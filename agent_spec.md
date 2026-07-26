model: "datarobot/anthropic/claude-sonnet-4-5-20250929"

system_prompt: |
  You are the ABC Forecast Agent (Agent Build Clinic — ERCOT DAM use case), an
  expert assistant for the ERCOT day-ahead market (DAM). You help energy traders
  and analysts understand and investigate day-ahead market prices ($/MWh) across
  ERCOT trading hubs: HB_HOUSTON, HB_NORTH, HB_SOUTH, and HB_WEST.

  Use case context: ERCOT manages ~90% of Texas electric load. We forecast
  day-ahead market price by hub 24 hours ahead using a deployed DataRobot
  time-series model, then compare forecasts to actuals to analyze error and
  improve the model.

  Your capabilities (agent maturity: tool-equipped + predictive-aware):
  1. Conversation: Answer questions about ERCOT and the day-ahead market with
     clear, factual explanations. For general questions, briefly explain relevant
     ERCOT/DAM concepts before diving into data.
  2. Data & panels: Retrieve historical DAM prices and weather/grid features
     (humidity, wind speed, temperature) from the configured DataRobot dataset.
     Produce rich panels alongside the conversation:
       - Multi-line hub price charts (USD/MWh).
       - Filterable/sortable data tables (timestamp_utc, hub_name, dam_price).
     Default to the last 30 days when no range is specified.
  3. Forecasting: Obtain day-ahead price predictions by calling `predict_dam_prices`
     (configured ERCOT_DEPLOYMENT_ID + ERCOT_DATASET_ID). Do not use Global MCP
     prediction tools for ERCOT DAM forecasts.
  4. Accuracy analysis: Compute RMSE, MAE, and Max Error comparing predicted vs.
     actual prices over a selected hub and window.
  5. Root-cause investigation: When a forecast point is inaccurate, investigate
     weather patterns, grid conditions, renewable generation (solar/wind), load,
     and market dynamics. Use dataset feature values plus Tavily web search when
     a key is available.

  Behavior rules:
  - Ground every numeric claim in tool results; cite hub and time window.
  - Prices are in USD/MWh; timestamps are UTC unless noted.
  - Prefer tables/charts for data, prose for reasoning; be concise.
  - If required input (hub, date range) is missing, state the default applied.
  - If a tool call fails, report the failure plainly rather than guessing.

tools:
  - function_name: get_dam_prices
    description: >
      Retrieve historical ERCOT day-ahead market prices and weather/grid features
      from the DataRobot AI Catalog training dataset, filtered by hub(s) and date
      range. Powers Forecast Assistant chart/table panels and provides actuals
      for accuracy comparison.
    inputs:
      - arg_name: hubs
        type: list
        object_schema: "list[str] e.g. ['HB_HOUSTON','HB_NORTH','HB_SOUTH','HB_WEST']; omit for all hubs"
      - arg_name: start_date
        type: str
        object_schema: "ISO-8601 date (YYYY-MM-DD)"
      - arg_name: end_date
        type: str
        object_schema: "ISO-8601 date (YYYY-MM-DD)"
    out:
      - arg_name: records
        type: list
        object_schema: "timestamp_utc, hub_name, dam_price_usd_mwh, weather/grid features"
    auth_spec:
      service_name: "DataRobot AI Catalog"
      auth_method: api_key

  - function_name: predict_dam_prices
    description: >
      Get 24h-ahead DAM price predictions from the deployed time-series forecast
      model via DataRobot Global MCP prediction tools (Level 3 predictive-aware).
    inputs:
      - arg_name: rows
        type: list
        object_schema: "scoring rows with hub_name, timestamp_utc, and model features"
    out:
      - arg_name: predictions
        type: list
        object_schema: "timestamp_utc, hub_name, predicted_dam_price_usd_mwh"
    auth_spec:
      service_name: "DataRobot Global MCP"
      auth_method: bearer_token

  - function_name: compute_accuracy_metrics
    description: >
      Compute RMSE, MAE, Max Error and per-point error series with 90% CI for
      the AI Analyst Forecast vs Actual dashboard.
    inputs:
      - arg_name: actuals
        type: list
      - arg_name: predictions
        type: list
    out:
      - arg_name: metrics
        type: dict
      - arg_name: error_series
        type: list
    auth_spec:
      service_name: "internal"
      auth_method: other

  - function_name: analyze_forecast_miss
    description: >
      Classify a forecast miss, build a narrative from dataset drivers (wind, solar, load),
      and return recommended follow-up actions (compare_hubs, driver_window, recommend_retrain,
      focus_wind). Use when the user asks why a forecast was wrong.
    inputs:
      - arg_name: timestamp_utc
        type: str
      - arg_name: hub_name
        type: str
      - arg_name: actual
        type: float
      - arg_name: predicted
        type: float
      - arg_name: action
        type: str
    out:
      - arg_name: narrative
        type: list
      - arg_name: recommended_actions
        type: list
      - arg_name: driver_summary
        type: dict
    auth_spec:
      service_name: "internal"
      auth_method: other

  - function_name: investigate_forecast_error
    description: >
      SSE-style root-cause investigation for a clicked forecast miss on the AI
      Analyst chart — weather, grid, renewables, market dynamics; optional
      Tavily web context.
    inputs:
      - arg_name: timestamp_utc
        type: str
      - arg_name: hub_name
        type: str
      - arg_name: context_features
        type: dict
    out:
      - arg_name: explanation
        type: str
      - arg_name: contributing_factors
        type: list
    auth_spec:
      service_name: "Tavily Search API"
      auth_method: api_key

examples:
  - "Forecast the next 24 hours of ERCOT day-ahead prices on 2025-10-20 of the HB_HOUSTON hub and display as chart"
  - "Forecast the next 24 hours of ERCOT day-ahead prices on 2025-10-24 of the HB_WEST hub and display as chart"
  - "Create a chart panel of the ERCOT day-ahead prices of the HB_HOUSTON hub"
  - "What is the average dam_price_usd_mwh for all hubs?"
  - "How accurate has the forecast been for HB_SOUTH this month? Show RMSE, MAE, and Max Error."

frontend:
  type: "multi-page"
  pages:
    - "Forecast Assistant — Tab 1: chat-first flat-agent workflow (AG-UI trace). Agent calls tools via Global MCP + local LangChain tools; right-hand Panels workspace shows charts/tables created during the conversation."
    - "AI Analyst — Tab 2: guided dashboard with hub + date range filters, optional Tavily API key, Forecast vs Actual chart (actual/predicted/90% CI band), RMSE/MAE/Max Error badges. Click forecast points for streamed miss classification, real driver context, and agentic follow-up actions (compare hubs, driver window, retrain recommendations)."
  requirements: >
    App title: ABC Forecast App (Agent Build Clinic). Implements slides Tabs 1–2 with agentic
    investigation CTAs on Tab 2 instead of a separate Panel Workspace tab.

    Architecture vs clinic notebooks: notebooks 0–5 deploy a standalone MCP server
    (MCP_DEPLOYMENT_ID). This app uses DataRobot Global MCP instead — set
    EXTERNAL_MCP_URL + EXTERNAL_MCP_HEADERS; do NOT set MCP_DEPLOYMENT_ID.

    Runtime parameter mapping (clinic .env → this app):
      FORECAST_DEPLOYMENT_ID / forecast model → ERCOT_DEPLOYMENT_ID
      ERCOT_TRAINING_DATASET_ID / training data → ERCOT_DATASET_ID
      SCORING_DATASET_ID → used by Global MCP prediction tools at scoring time
      MCP_DEPLOYMENT_ID → not used (replaced by Global MCP)

    Clinic POV example IDs (replace with your account IDs):
      ERCOT_TRAINING_DATASET_ID=698dfe27b04f8da88246bc28
      FORECAST_DEPLOYMENT_ID=698e049a2720aafce2802a0c
      SCORING_DATASET_ID=698f3ae36603c710354245fd

    Also configure: EXTERNAL_MCP_URL, EXTERNAL_MCP_HEADERS, optional TAVILY_API_KEY.
