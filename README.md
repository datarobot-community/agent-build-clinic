<p align="center">
  <a href="https://github.com/datarobot-community/datarobot-agent-application">
    <img src="./.github/datarobot_logo.avif" width="600px" alt="DataRobot Logo"/>
  </a>
</p>
<p align="center">
    <span style="font-size: 1.5em; font-weight: bold; display: block;">ABC Forecast App — Agent Build Clinic</span>
</p>

<p align="center">
  <a href="https://datarobot.com">Homepage</a>
  ·
  <a href="https://docs.datarobot.com/en/docs/agentic-ai/agentic-develop/index.html">Documentation</a>
  ·
  <a href="https://docs.datarobot.com/en/docs/get-started/troubleshooting/general-help.html">Support</a>
</p>

This repository is the **reference implementation** for the DataRobot **Agent Build Clinic** ERCOT day-ahead market (DAM) use case. It is built on the [DataRobot Agent Application template](https://github.com/datarobot-community/datarobot-agent-application) and includes:

- A **LangGraph agent** with ERCOT-specific tools (`get_dam_prices`, `predict_dam_prices`, accuracy metrics, and miss analysis)
- A **FastAPI backend** with ERCOT data and analyst APIs
- A **React frontend** with Forecast Assistant and Analyst views
- **DataRobot Global MCP** for platform tools (no local `mcp_server/` component)

Participants in the clinic replicate this app using the prompts in [`prompts/`](prompts/README.md). The full agent design is documented in [`agent_spec.md`](agent_spec.md).

> [!NOTE]
> This app uses **DataRobot Global MCP**, not a standalone MCP server deployment. Do not set `MCP_DEPLOYMENT_ID`.

# Table of contents

- [Architecture](#architecture)
- [Quick start](#quick-start)
  - [Prerequisite tools](#prerequisite-tools)
  - [Configure environment](#configure-environment)
  - [Install dependencies](#install-dependencies)
  - [Run locally](#run-locally)
- [Clinic workflow](#clinic-workflow)
- [Develop and customize](#develop-and-customize)
- [Deploy](#deploy)
- [Global MCP](#global-mcp)
- [Troubleshooting](#troubleshooting)
- [Get help](#get-help)

For template-level changes, see [CHANGELOG](CHANGELOG.md).

# Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────────┐
│  frontend_web   │────▶│  fastapi_server  │────▶│  agent (LangGraph)      │
│  React + Vite   │     │  REST + AG-UI    │     │  ERCOT tools + Global MCP│
└─────────────────┘     └──────────────────┘     └─────────────────────────┘
        :5173                    :8080                      :8842
```

| Component | Path | Purpose |
|-----------|------|---------|
| Agent | `agent/agent/` | LangGraph agent, ERCOT tools, prompt |
| Backend | `fastapi_server/` | Chat API, ERCOT endpoints, auth |
| Frontend | `frontend_web/` | Forecast Assistant + Analyst UI |
| Infra | `infra/` | Pulumi deployment to DataRobot |

# Quick start

> [!CAUTION]
> macOS and Linux only. On Windows, use a [DataRobot codespace](https://docs.datarobot.com/en/docs/workbench/wb-notebook/codespaces/index.html) or WSL.

## Prerequisite tools

| Tool | Version | Description |
|------|---------|-------------|
| **dr** (DataRobot CLI) | >= 0.2.55 | Templates, auth, task execution |
| **git** | >= 2.30.0 | Version control |
| **uv** | >= 0.9.0 | Python package manager |
| **Pulumi** | >= 3.163.0 | Infrastructure as Code |
| **Taskfile** | >= 3.43.3 | Task runner |
| **Node.js** | >= 24 | Frontend development |

Install on macOS with Homebrew:

```sh
brew install datarobot-oss/taps/dr-cli uv pulumi/tap/pulumi go-task node git
```

Verify:

```sh
dr --version && uv --version && pulumi version && task --version && node --version
```

> [!TIP]
> After installing `uv`, run `uv tool update-shell` once so your shell picks up the updated `PATH`.

> [!NOTE]
> If you do not have a Pulumi account, use `pulumi login --local` or create a free account at [app.pulumi.com](https://app.pulumi.com/signup).

## Configure environment

Copy the template and fill in your values:

```sh
cp .env.template .env
```

Required variables:

| Variable | Description |
|----------|-------------|
| `DATAROBOT_API_TOKEN` | Your DataRobot API token |
| `DATAROBOT_ENDPOINT` | e.g. `https://app.datarobot.com/api/v2` |
| `SESSION_SECRET_KEY` | Random string for session signing |
| `ERCOT_DEPLOYMENT_ID` | Deployed time-series forecast model ID |
| `ERCOT_DATASET_ID` | ERCOT training dataset ID (historical DAM + weather) |
| `EXTERNAL_MCP_URL` | Global MCP endpoint for your DataRobot host |
| `EXTERNAL_MCP_HEADERS` | `{"Authorization": "Bearer <DATAROBOT_API_TOKEN>"}` |
| `EXTERNAL_MCP_TRANSPORT` | `streamable-http` |

Generate a session secret:

```sh
python -c "import os, binascii; print(binascii.hexlify(os.urandom(64)).decode())"
```

Validate credentials:

```sh
dr auth check
```

For instructor-led setup details, see [`prompts/INSTRUCTOR-env-setup.md`](prompts/INSTRUCTOR-env-setup.md).

If you are starting from scratch (not this repo), you can also run `dr start` to walk through the template wizard. This clinic repo is already configured — use `.env.template` as the guide.

## Install dependencies

From the project root:

```sh
dr task run install
```

> [!IMPORTANT]
> Do not copy `.venv` folders between machines or projects. Always run `dr task run install` in this directory so virtualenvs point at the correct paths.

## Run locally

Start all services:

```sh
dr run dev
```

This starts three processes:

| Service | Port | URL |
|---------|------|-----|
| Frontend (Vite) | 5173 | http://localhost:5173 |
| Backend (FastAPI) | 8080 | http://localhost:8080 |
| Agent | 8842 | http://localhost:8842 |

Open http://localhost:5173 and ask a question such as:

> Show HB_HOUSTON day-ahead prices for the last 7 days.

You can also start individual services:

```sh
dr run agent:dev
dr run fastapi_server:dev
dr run frontend_web:dev
```

# Clinic workflow

The clinic follows a three-phase **define → code → deploy** flow. Prompt files live in [`prompts/`](prompts/README.md):

| Phase | Prompt | Output |
|-------|--------|--------|
| 1. Define | `01-define-agent.md` | `agent_spec.md` |
| 2. Code | `02-code-agent.md` | Agent, backend, frontend |
| 3. Deploy | `03-deploy.md` | DataRobot deployment |

Between phases 2 and 3, participants configure `.env` manually (instructor-led). See [`prompts/INSTRUCTOR-env-setup.md`](prompts/INSTRUCTOR-env-setup.md).

# Develop and customize

## Agent

The agent lives in `agent/agent/`:

| File | Purpose |
|------|---------|
| `myagent.py` | LangGraph graph, system prompt, MCP + ERCOT tool wiring |
| `ercot_tools.py` | `get_dam_prices`, `predict_dam_prices`, accuracy and analysis tools |
| `config.py` | Agent configuration |

After agent changes:

```sh
dr task run agent:install
dr task run agent:lint
dr task run agent:test
```

See [AGENTS.md](AGENTS.md) and [docs/agent/README.md](docs/agent/README.md) for framework details.

## Backend and frontend

- ERCOT REST endpoints: `fastapi_server/app/api/v1/ercot.py`
- Forecast Assistant UI: `frontend_web/src/pages/ForecastAssistantPage.tsx`
- Analyst UI: `frontend_web/src/pages/AnalystPage.tsx`

After changes:

```sh
dr task run fastapi_server:lint
dr task run frontend_web:lint
```

## Run all tests

```sh
dr task run test
```

# Deploy

Deploy to DataRobot (requires Pulumi login):

```sh
dr task run infra:up-yes
```

Or:

```sh
dr run deploy
```

Ensure `PULUMI_STACK_NAME` in `.env` matches an existing stack in `infra/`:

```sh
cd infra && pulumi stack ls
```

Post-deploy validation:

```sh
task agent:cli -- execute-deployment \
  --user_prompt "Show HB_HOUSTON DAM prices for the last 7 days" \
  --deployment_id <deployment_id>
```

# Global MCP

This application does **not** ship a local `mcp_server/` component. Platform tools (predictions, catalog, etc.) are accessed through **DataRobot Global MCP**.

Configure in `.env`:

```shell
EXTERNAL_MCP_URL=https://{DATAROBOT_URL}/api/v2/genai/globalmcp/mcp
EXTERNAL_MCP_HEADERS={"Authorization": "Bearer <DATAROBOT_API_TOKEN>"}
EXTERNAL_MCP_TRANSPORT=streamable-http
```

- Do **not** set `MCP_DEPLOYMENT_ID`.
- ERCOT DAM **forecasts** must use the `predict_dam_prices` tool (time-series batch scoring with `ERCOT_DEPLOYMENT_ID`). Global MCP generic prediction tools are not suitable for this deployment.

See [docs/mcp-server.md](docs/mcp-server.md) and [AGENTS.md](AGENTS.md#mcp--global-mcp).

# Troubleshooting

## Ports reference

| Port | Component | Configurable |
|------|-----------|--------------|
| 8080 | FastAPI backend | No |
| 5173 | Vite dev server | No |
| 8842 | Agent endpoint | Yes (`AGENT_PORT` in `.env`) |

### Port conflicts

```sh
lsof -i :8080
lsof -i :5173
lsof -i :8842
```

Stop the conflicting process or free the port before running `dr run dev`.

### DataRobot codespace ports

Expose ports 8080, 5173, and 8842 in the codespace **Session Environment** settings. See [docs/img/codespace-ports.png](docs/img/codespace-ports.png).

## Common issues

### Services won't start

1. Verify prerequisites: `dr --version`, `uv --version`, `node --version`
2. Reinstall dependencies: `dr task run install`
3. Check `.env` has all required variables (see [Configure environment](#configure-environment))
4. Validate auth: `dr auth check`

### Stale virtualenv after copying the project

If tests or scripts reference another project's path (e.g. `abc-forecast-app`), remove and recreate venvs:

```sh
rm -rf agent/.venv fastapi_server/.venv
dr task run install
```

### Agent can't reach MCP or forecast tools fail

1. Confirm `EXTERNAL_MCP_URL` and `EXTERNAL_MCP_HEADERS` are set with a valid token
2. Confirm `ERCOT_DEPLOYMENT_ID` and `ERCOT_DATASET_ID` are set
3. Use `predict_dam_prices` for forecasts — not Global MCP generic prediction tools

### Pulumi stack not found

```sh
cd infra
pulumi stack ls
pulumi stack select <stack-name>   # or create one
```

Update `PULUMI_STACK_NAME` in `.env` to match.

### Frontend build issues

```sh
cd frontend_web
rm -rf node_modules dist
dr task run frontend_web:install
```

# Get help

- [Agent spec](agent_spec.md) — clinic design reference
- [Clinic prompts](prompts/README.md) — participant workflow
- [DataRobot agentic documentation](https://docs.datarobot.com/en/docs/agentic-ai/agentic-develop/index.html)
- [DataRobot CLI (`dr`) documentation](https://github.com/datarobot-oss/cli)
- [DataRobot support](https://docs.datarobot.com/en/docs/get-started/troubleshooting/general-help.html)
