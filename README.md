# Agentic AI Building Blocks

This repository contains a series of 7 "Agentic Blocks"—modular notebooks designed to demonstrate how to build, enhance, and deploy a production-ready AI Agent using DataRobot.

The goal is to move beyond simple chatbots by equipping an agent with predictive forecasting, structured data querying, and document intelligence.

---

## Setup

### MCP Server Setup (Optional Notebook 0)

Before running MCP-enabled notebooks, either:
- complete **0 - MCP Server Setup**, or
- provide an existing `MCP_DEPLOYMENT_ID` in `.env`.

This follows the simplified template flow from the DataRobot MCP component repository ([af-component-datarobot-mcp](https://github.com/datarobot-community/af-component-datarobot-mcp)):
- `uvx copier copy git@github.com:datarobot/af-component-base.git .`
- `uvx copier copy git@github.com:datarobot-community/af-component-datarobot-mcp.git .`

After deployment, set the resulting deployment ID as `MCP_DEPLOYMENT_ID` in your `.env`.

### Environment Variables

Create a `.env` file in the repository root. The notebooks call `load_dotenv()` so they will pick it up automatically.

**For Codespace:**
- Create `.env` in the workspace root
- The file will be automatically loaded by the notebooks

**For Local:**
- Create `.env` in the project root directory
- **Note:** You must provide DataRobot credentials, either via environment variables (`DATAROBOT_ENDPOINT`, `DATAROBOT_API_TOKEN`) or via a local DataRobot config file used by the Python SDK.

**Quick Setup:**
```bash
# Copy the example file and fill in your values
cp .env.example .env
```

**Required Variables:**
See `.env.example` for the complete list. Key variables include:
- `DATAROBOT_ENDPOINT` and `DATAROBOT_API_TOKEN` (required for local development)
- `ERCOT_TRAINING_DATASET_ID`
- `FORECAST_DEPLOYMENT_ID`, `SCORING_DATASET_ID`, and `MCP_DEPLOYMENT_ID`
- `PROMPT_TEMPLATE_ID` (used by notebooks 2 and 4)
- `MODEL_NAME` (LLM Gateway model ID)
- `DATAROBOT_DEFAULT_USE_CASE` (optional; used for organization/governance in notebooks 5–6)
- `PREDICTION_ENV_ID` (required for notebook 6; serverless Prediction Environment id in your tenant)

Replace placeholder values with your actual DataRobot dataset and deployment IDs.

### Dependencies

Notebook **1 - LLM Gateway** installs Python dependencies via `pip install -r requirements.txt`.

If you run notebooks out of order (or only want to run one notebook), you may need to install dependencies first:

```bash
pip install -r requirements.txt
```

---

## Notebook Overview

### 0 - MCP Server Setup
**Goal:** Create and deploy an MCP server once, then reuse it across the rest of the workshop.
* Uses the DataRobot MCP AF component setup flow from the template repository.
* Produces the shared `MCP_DEPLOYMENT_ID` used by notebooks 3, 4, 5, and 6.

### 1 - LLM Gateway
**Goal:** Establish the foundation for the agent by connecting to the DataRobot LLM Gateway.
* Connects to the DataRobot LLM Gateway.
* Demonstrates how to access and switch between more than 100 different LLMs (e.g., GPT-4, Claude, Gemini) using a single secure endpoint, eliminating the need to manage individual vendor API keys.

### 2 - Prompt Management
**Goal:** Create, version, and programmatically retrieve a DataRobot Prompt Template.
* Demonstrates how to save, version, and manage system prompts externally in DataRobot.
* Allows business users to update the agent's tone or instructions without requiring a code redeployment.
* Prompts are treated as managed, versioned assets (not hardcoded strings).

### 3 - DARIA Tools
**Goal:** Empower the agent to query enterprise data warehouses (like Snowflake) to answer factual business questions.
* Uses the Model Context Protocol (MCP) to connect the agent to a DataRobot deployment.
* Enables the agent to dynamically generate queries and retrieve live datasets—transforming it from a simple chatbot into a data analyst capable of answering questions.

### 4 - Forecast Agent Tools
**Goal:** Use a DataRobot forecast model deployment as a tool.
* Connects the agent to an MCP deployment that exposes forecasting tools, then prompts the LLM to call the appropriate forecast tool when the user asks forward-looking questions.
* Optionally demonstrates using a managed DataRobot Prompt Template to keep the agent’s system prompt versioned and centrally managed.
* LLMs cannot predict the future, but DataRobot can—this bridges Generative AI with Predictive AI.

### 5 - PDF Onboarding
**Goal:** Enable the agent to answer questions grounded in unstructured PDF documents.
* Creates (or reuses) a deployed **Vector Database (VDB)** from a PDF and queries it via MCP.
* Implements a RAG (Retrieval Augmented Generation) workflow: retrieve relevant excerpts, then answer grounded in the document.
* Example: Answer questions from the ERCOT market briefing PDF.

### 6 - Deploy the Agent
**Goal:** Package and deploy the forecasting agent as a DataRobot Agentic Workflow (custom inference model).
* Programmatically packages the agent code and registers it as a Custom Model in DataRobot.
* Deploys the agent to a serverless Prediction Environment, linking it to a Use Case for easy access and governance.
* Uses DRUM entry points and artifact packaging to turn the agent into a deployable "model".
* Runtime behavior (deployment IDs, dataset IDs, LLM model) is driven by runtime parameters / env vars, not hardcoded values.
* **Tenant-specific config:** In the notebook, update `AGENT_NAME` / `REGISTERED_MODEL_NAME` (labels) and `PREDICTION_ENV_ID` (serverless environment) for your tenant as needed.

---

## Getting Started
1.  Set up your `.env` file (see [Environment Variables](#environment-variables) section above).
2.  Optional: complete **Notebook 0 - MCP Server Setup** if you need to create/deploy an MCP server.
3.  Ensure `MCP_DEPLOYMENT_ID` is set in `.env` (existing deployment IDs are supported).
4.  Open **Notebook 1 - LLM Gateway** to authenticate and test your LLM connection.
5.  Proceed sequentially through the notebooks to build up the agent's capabilities.
6.  For **Notebook 5 - PDF Onboarding**, the sample PDF is included at `documents/ercot_market_briefing_enhanced.pdf` (or update the notebook’s `pdf_path` variable).

---

## Shared assets required to run the notebooks

- **Python dependencies**: `requirements.txt`
- **Environment variables**: `.env` file (see [Environment Variables](#environment-variables) section)
- **DataRobot assets (must exist in your tenant)**:
  - Forecasting **deployment**: Set `FORECAST_DEPLOYMENT_ID` in `.env`
  - MCP **deployment**: Set `MCP_DEPLOYMENT_ID` in `.env`
  - Training **dataset**: Set `ERCOT_TRAINING_DATASET_ID` in `.env`
  - Forecast scoring **dataset**: Set `SCORING_DATASET_ID` in `.env`
  - Prompt template **ID**: Set `PROMPT_TEMPLATE_ID` in `.env` (if running notebooks 2 and 4)
- **Sample PDF for document intelligence**: `documents/ercot_market_briefing_enhanced.pdf`
  - Used by `5 - PDF Onboarding.ipynb`
- **Deployment packaging folder**: `agent_artifacts/`
  - Used/created by `6 - Deploy the Agent.ipynb`
  - This folder is **generated by notebook 6**; it may be empty until you run the notebook.
  - After running notebook 6, it is expected to contain: `custom.py`, `agent.py`, `requirements.txt`, plus build metadata like `pyproject.toml` (and additional generated files such as `uv.lock`, `model-metadata.yaml`)