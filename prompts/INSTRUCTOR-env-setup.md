# Instructor — Configure `.env` Before Local Testing

**When:** After Prompt 2 (coding) is complete, **before** participants run `dr run dev`.

This is a **manual instructor-led step**, not an LLM prompt. Participants edit `.env` themselves.

---

## What to say in the room

> "Coding is done. **Stop.** Copy `.env.template` to `.env` and fill in the values from your handout. Do not run `dr run dev` until your `.env` is complete. Raise your hand when ready."

---

## Participant checklist

```bash
cp .env.template .env
```

Fill in these values:

| Variable | Who provides | Required |
|----------|--------------|----------|
| `DATAROBOT_API_TOKEN` | Participant | Yes |
| `DATAROBOT_ENDPOINT` | Participant (e.g. `https://app.datarobot.com/api/v2`) | Yes |
| `SESSION_SECRET_KEY` | Participant generates locally | Yes |
| `ERCOT_DEPLOYMENT_ID` | **Instructor handout** | Yes |
| `ERCOT_DATASET_ID` | **Instructor handout** | Yes |
| `EXTERNAL_MCP_URL` | Template default (update host if needed) | Yes |
| `EXTERNAL_MCP_HEADERS` | Participant substitutes their token | Yes |
| `EXTERNAL_MCP_TRANSPORT` | `streamable-http` | Yes |
| `TAVILY_API_KEY` | Optional | No |

Generate session secret:

```bash
python -c "import os, binascii; print(binascii.hexlify(os.urandom(64)).decode())"
```

Example `EXTERNAL_MCP_HEADERS`:

```json
{"Authorization": "Bearer <DATAROBOT_API_TOKEN>"}
```

**Do NOT set** `MCP_DEPLOYMENT_ID`.

---

## Instructor handout (distribute with clinic IDs)

```
ABC Forecast App — Clinic Environment Values

ERCOT_DEPLOYMENT_ID=<your clinic forecast deployment>
ERCOT_DATASET_ID=<your clinic training dataset>

Example (POV account):
  ERCOT_DEPLOYMENT_ID=698e049a2720aafce2802a0c
  ERCOT_DATASET_ID=698dfe27b04f8da88246bc28
```

Participants add their own `DATAROBOT_API_TOKEN` separately.

---

## Verify before `dr run dev`

```bash
dr dependency check
```

Then:

```bash
dr run dev
```

### Quick validation

**Forecast Assistant:** "Show me DAM prices for HB_HOUSTON over the last 30 days" → chart + table panels appear.

**AI Analyst:** Select HB_HOUSTON, dates in dataset range, click Update → wait 1–2 min → chart with RMSE/MAE/Max Error badges.

When local testing passes, proceed to **Step 3 — Deploy** (`03-deploy.md` or Agent Assist option 3).
