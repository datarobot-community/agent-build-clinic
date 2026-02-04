# Agentic AI Building Blocks

This repository contains a series of 7 "Agentic Blocks"—modular notebooks designed to demonstrate how to build, enhance, and deploy a production-ready AI Agent using DataRobot.

The goal is to move beyond simple chatbots by equipping an agent with predictive forecasting, structured data querying, and document intelligence.

---

## Setup

### Option A: DataRobot Codespace (recommended for these notebooks)

1. Open the Codespace **Terminal**.
2. Install dependencies from this repo:

```bash
pip install -r requirements.txt
```

3. If you installed via terminal, **restart the notebook kernel** (Kernel → Restart) to pick up newly installed packages.

### Option B: Local Python / Jupyter

1. Create and activate a virtual environment (recommended).
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Ensure DataRobot credentials are available to the notebooks (for `dr.Client()`):
   - `DATAROBOT_ENDPOINT`
   - `DATAROBOT_API_TOKEN`
   - Optional (used in some notebooks): `DATAROBOT_DEFAULT_USE_CASE`

4. Optional (Document Intelligence / Aryn):
   - `ARYN_API_KEY` (if not set, the PDF notebook will run in simulation mode)

---

## Notebook Overview

### 1 - LLM Gateway
**Goal:** Establish the foundation.
* Connects to the DataRobot LLM Gateway.
* Demonstrates how to access and switch between nearly 100 different LLMs (e.g., GPT-4, Claude, Gemini) using a single secure endpoint, eliminating the need to manage individual vendor API keys.

### 2 - Advanced Data Tools
**Goal:** Give the agent "Data Analyst" capabilities.
* Uses the Model Context Protocol (MCP) to connect the agent to a DataRobot deployment acting as a data router.
* Enables the agent to autonomously query structured data warehouses (like Snowflake) to answer factual questions (e.g., "Which bakeries are we tracking?").

### 3 - Predictive Tools
**Goal:** Bridge Generative AI with Predictive AI.
* Defines a custom Tool Client that wraps a DataRobot Time Series deployment.
* Allows the agent to recognize forward-looking questions (e.g., "How many croissants will we sell next Friday?") and delegate them to a forecasting model for accurate numerical answers.

### 4 - Document Intelligence
**Goal:** Onboard unstructured knowledge (RAG).
* Integrates the Aryn SDK to intelligently parse PDF documents (e.g., Supplier Quality Standards).
* Injects this context into the agent, enabling it to answer specific compliance rules (e.g., "What is the maximum temp for butter deliveries?").

### 5 - Deploy and Evaluate
**Goal:** Move from experiment to production.
* Programmatically packages the agent code and registers it as a Custom Model in DataRobot.
* Deploys the agent to a prediction server, unlocking the Playground for user interaction and automated "LLM-as-a-Judge" evaluation metrics.

### 6 - Prompt Management
**Goal:** Decouple persona from code.
* Demonstrates how to save, version, and manage system prompts externally.
* Allows business users to update the agent's tone or instructions without requiring a code redeployment.

### 7 - Custom Traces
xxx

---

## Getting Started
1.  Open **Notebook 1** to authenticate and test your LLM connection.
2.  Proceed sequentially to build up the agent's capabilities.
3.  For the PDF demo notebook, ensure the sample PDF exists at `archive/ercot_market_briefing.pdf` (or update the notebook's `PDF_FILENAME`). The notebook will fall back to embedded sample text if the file/key are missing.

---

## Shared assets required to run the notebooks

- **Python dependencies**: `requirements.txt`
- **Core agent code**: `agent.py` (imported by the deployment packaging notebook)
- **DataRobot assets (must exist in your tenant)**:
  - Forecasting **deployment**: `6971b39b3fa6dde87d114a82`
  - Forecasting **scoring dataset**: `6971bf6404e148a1b1b17c71`
- **Deployment packaging folder**: `agent_artifacts/`
  - Used/created by `6 - Deploy the Agent.ipynb`
  - Expected to contain (and is overwritten/created by the notebook): `custom.py`, `agent.py`, `requirements.txt`, plus packaging metadata like `pyproject.toml`
- **Sample PDF for Document Intelligence**: `archive/ercot_market_briefing.pdf`
  - Used by `5 - PDF Onboarding (Aryn).ipynb`
  - Optional: if missing (or if `ARYN_API_KEY` is not set), the notebook runs in a “simulation mode” using embedded fallback policy text