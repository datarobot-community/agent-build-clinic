# Agentic AI Building Blocks

This repository contains a series of 6 "Agentic Blocks"—modular notebooks designed to demonstrate how to build, enhance, and deploy a production-ready AI Agent using DataRobot.

The goal is to move beyond simple chatbots by equipping an agent with predictive forecasting, structured data querying, and document intelligence.

---

## Setup

### Environment Variables

Create a `.env` file in the repository root with the following variables:

**For Codespace:**
- Create `.env` in the workspace root
- The file will be automatically loaded by the notebooks

**For Local:**
- Create `.env` in the project root directory
- Ensure your notebook environment loads `.env` files (most Jupyter setups do this automatically)
- **Note:** For local development, you'll also need to set `DATAROBOT_ENDPOINT` and `DATAROBOT_API_TOKEN` (these are typically set automatically in Codespace)

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
- `MODEL_NAME` (LLM Gateway model id)
- `DATAROBOT_DEFAULT_USE_CASE` (optional; used for organization/governance in notebooks 5–6)

Replace placeholder values with your actual DataRobot dataset and deployment IDs.

---

## Notebook Overview

### 1 - LLM Gateway
**Goal:** Establish the foundation for the agent by connecting to the DataRobot LLM Gateway.
* Connects to the DataRobot LLM Gateway.
* Demonstrates how to access and switch between nearly 100 different LLMs (e.g., GPT-4, Claude, Gemini) using a single secure endpoint, eliminating the need to manage individual vendor API keys.

### 2 - Prompt Management
**Goal:** Create, version, and programmatically retrieve a DataRobot Prompt Template.
* Demonstrates how to save, version, and manage system prompts externally in DataRobot.
* Allows business users to update the agent's tone or instructions without requiring a code redeployment.
* Prompts are treated as managed, versioned assets (not hardcoded strings).

### 3 - Advanced Data Tools
**Goal:** Empower the agent to query enterprise data warehouses (like Snowflake) to answer factual business questions.
* Uses the Model Context Protocol (MCP) to connect the agent to a DataRobot deployment acting as a secure "Data Tool."
* Enables the agent to dynamically generate queries and retrieve live datasets—transforming it from a simple chatbot into a data analyst capable of answering questions like "What distinct bakeries are we tracking supplies for?"

### 4 - Forecast Agent Tools
**Goal:** Use the DataRobot forecast model deployment as a tool.
* Defines a custom Tool Client that wraps a DataRobot Time Series deployment.
* Allows the agent to recognize forward-looking questions (e.g., "How many croissants will we sell next Friday?") and delegate them to a forecasting model for accurate numerical answers.
* LLMs cannot predict the future, but DataRobot can—this bridges Generative AI with Predictive AI.

### 5 - PDF Onboarding (Aryn)
**Goal:** Enable the agent to answer questions grounded in unstructured PDF documents.
* Creates (or reuses) a deployed **Vector Database (VDB)** from a PDF and queries it via MCP.
* Implements a RAG (Retrieval Augmented Generation) workflow: retrieve relevant excerpts, then answer grounded in the document.
* Example: Answer questions from the ERCOT market briefing PDF.

### 6 - Deploy the Agent
**Goal:** Package and deploy the forecasting agent as a DataRobot Agentic Workflow (custom inference model).
* Programmatically packages the agent code and registers it as a Custom Model in DataRobot.
* Deploys the agent to a serverless Prediction Environment, linking it to a Use Case for easy access and governance.
* Uses DRUM entry points and artifact packaging to turn the agent into a deployable "model."
* Runtime behavior (deployment IDs, dataset IDs, LLM model) is driven by runtime parameters / env vars, not hardcoded values.
* **Tenant-specific config:** In the notebook, update `AGENT_NAME` / `REGISTERED_MODEL_NAME` (labels) and `PREDICTION_ENV_ID` (serverless environment) for your tenant as needed.

---

## Getting Started
1.  Set up your `.env` file (see [Environment Variables](#environment-variables) section above).
2.  Open **Notebook 1 - LLM Gateway** to authenticate and test your LLM connection.
3.  Proceed sequentially through the notebooks to build up the agent's capabilities.
4.  For **Notebook 5 - PDF Onboarding**, ensure the sample PDF exists at `documents/ercot_market_briefing_enhanced.pdf` (or update the notebook’s `pdf_path` variable).

---

## Shared assets required to run the notebooks

- **Python dependencies**: `requirements.txt`
- **Environment variables**: `.env` file (see [Environment Variables](#environment-variables) section)
- **Core agent code**: `agent.py` (created by Notebook 6 - Deploy the Agent)
- **DataRobot assets (must exist in your tenant)**:
  - Forecasting **deployment**: Set `FORECAST_DEPLOYMENT_ID` in `.env`
  - MCP **deployment**: Set `MCP_DEPLOYMENT_ID` in `.env`
  - Training **dataset**: Set `ERCOT_TRAINING_DATASET_ID` in `.env`
  - Forecast scoring **dataset**: Set `SCORING_DATASET_ID` in `.env`
  - Prompt template **ID**: Set `PROMPT_TEMPLATE_ID` in `.env` (if running notebooks 2 and/or 4)
- **Deployment packaging folder**: `agent_artifacts/`
  - Used/created by `6 - Deploy the Agent.ipynb`
  - Expected to contain (and is overwritten/created by the notebook): `custom.py`, `agent.py`, `requirements.txt`, plus packaging metadata like `pyproject.toml`
- **Sample PDF for Document Intelligence**: `documents/ercot_market_briefing_enhanced.pdf`
  - Used by `5 - PDF Onboarding (Aryn).ipynb`