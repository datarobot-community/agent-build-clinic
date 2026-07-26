# Step 3 — Deploy the Agent

**Agent Assist phase:** Option 3 — Deploy an AI agent

This step is **not an LLM prompt**. After local testing with `dr run dev` succeeds, deploy using Agent Assist or the CLI directly.

---

## Prerequisites

- [ ] Prompt 1 complete — `agent_spec.md` exists
- [ ] Prompt 2 complete — agent, backend, and frontend implemented
- [ ] `.env` configured (see instructor handout below)
- [ ] Local test passed — `dr run dev` works, both tabs validated
- [ ] `dr dependency check` passes

---

## Deploy with Agent Assist (recommended)

In Cursor with the DataRobot Agent Assist skill:

1. Select **Option 3 — Deploy an AI agent**
2. Agent Assist runs the pre-deployment checklist
3. Deploy when prompted

Or tell Agent Assist:

> Deploy the ABC Forecast App to DataRobot.

---

## Deploy with CLI

From project root:

```bash
dr task run infra:up-yes
```

If deployment fails, tear down and retry:

```bash
dr task run infra:down-yes
# fix issues, then:
dr task run infra:up-yes
```

---

## Post-deploy: verify runtime parameters

In the DataRobot custom application settings, confirm:

| Parameter | Source |
|-----------|--------|
| `ERCOT_DEPLOYMENT_ID` | Clinic handout |
| `ERCOT_DATASET_ID` | Clinic handout |
| `EXTERNAL_MCP_URL` | `https://{host}/api/v2/genai/globalmcp/mcp` |
| `EXTERNAL_MCP_HEADERS` | Bearer token JSON |
| `TAVILY_API_KEY` | Optional |
| `DATAROBOT_API_TOKEN` | Participant token |

---

## Post-deploy validation

```bash
task agent:cli -- execute-deployment \
  --user_prompt "What hubs are available for ERCOT day-ahead prices?" \
  --deployment_id <agent_deployment_id>
```

Test the deployed custom application URL:

- **Forecast Assistant:** ask for HB_HOUSTON prices → panels appear
- **AI Analyst:** select hub + dates → forecast chart loads → click a point → investigation runs

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Deploy fails on dependency check | Run `dr dependency check`, fix errors |
| MCP tools fail in production | Verify EXTERNAL_MCP_URL and bearer token runtime params |
| Empty forecast chart | Confirm ERCOT_DEPLOYMENT_ID runtime param |
| 404 on API calls | Frontend must use `/v1/ercot/...` not `/api/v1/ercot/...` |
