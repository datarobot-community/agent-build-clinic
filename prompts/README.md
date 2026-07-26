# ABC Forecast App — Clinic Prompts

Three-phase workflow aligned with **DataRobot Agent Assist**: define → code → deploy.

Local testing happens **after** Prompt 2, once participants manually configure `.env` (instructor-led).

---

## Clinic flow

```
┌─────────────────────────────────────────────────────────────────┐
│  1. DEFINE          Paste 01-define-agent.md                    │
│     (Agent Assist   → produces agent_spec.md                    │
│      option 1)      → STOP (review spec)                        │
├─────────────────────────────────────────────────────────────────┤
│  2. CODE            Paste 02-code-agent.md                     │
│     (Agent Assist   → implements agent + backend + frontend      │
│      option 2)      → STOP (do not run locally yet)              │
├─────────────────────────────────────────────────────────────────┤
│  INSTRUCTOR PAUSE   See INSTRUCTOR-env-setup.md                 │
│                     → participants manually edit .env            │
│                     → dr run dev → validate locally              │
├─────────────────────────────────────────────────────────────────┤
│  3. DEPLOY          Agent Assist option 3 OR 03-deploy.md        │
│     (not an LLM     → dr task run infra:up-yes                  │
│      prompt)        → post-deploy validation                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Files

| File | Audience | Agent Assist phase |
|------|----------|-------------------|
| `01-define-agent.md` | Participant → LLM | Option 1 — Design |
| `02-code-agent.md` | Participant → LLM | Option 2 — Code |
| `INSTRUCTOR-env-setup.md` | Instructor | Manual pause before local test |
| `03-deploy.md` | Instructor / participant | Option 3 — Deploy |

---

## What participants need

**Before the session:**

- DataRobot account + API token
- `dr` CLI installed and authenticated (`dr auth login`)
- Prerequisites from template README (git, Python 3.11+, Node 24+, uv, Pulumi, Taskfile)

**From instructor (handout):**

- `ERCOT_DEPLOYMENT_ID`
- `ERCOT_DATASET_ID`

---

## Reference implementation

This repo (`abc-forecast-app`) is the canonical example. Participants replicate it using these prompts — they should not copy the repo during the exercise.
