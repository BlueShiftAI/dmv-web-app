# IBM watsonx Orchestrate — Setup & Integration Guide

> **Educational prototype.** Not affiliated with the SCDMV.
> Queue, appointment, tax, and ownership data are simulated.

---

## Overview

The DMV Web App integrates with IBM watsonx Orchestrate as a vehicle-registration
assistant. The integration is **optional** — the app runs fully in mock mode when
credentials are not configured.

```
Browser  →  POST /api/orchestrate/chat  →  FastAPI backend
                                               ↓ (if configured)
                                       IBM watsonx Orchestrate
                                               ↓
                                       Agent calls tool endpoints
                                       GET  /api/orchestrate/tools/*
                                       POST /api/orchestrate/tools/book
                                       POST /api/orchestrate/tools/cancel
```

Private API keys never reach the browser. The backend proxy holds all credentials.

---

## Quick Start — Mock Mode (no credentials needed)

The assistant works immediately in demo mode when `ORCHESTRATE_API_KEY` is not set.
Responses are rule-based answers drawn from the SC private-party registration
requirements config.

To verify:
```bash
# Start backend
cd backend && uvicorn app.main:app --reload

# In another terminal
curl -X POST http://localhost:8000/api/orchestrate/chat \
  -H "Authorization: Bearer <your-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"message": "what documents do I need?"}'
```

---

## Production Setup — Real Orchestrate

### 1. Obtain IBM watsonx Orchestrate credentials

You need:
- `ORCHESTRATE_API_KEY` — your IBM Cloud API key or Orchestrate service key
- `ORCHESTRATE_INSTANCE_URL` — your Orchestrate instance base URL
  (e.g. `https://your-instance.us-south.watsonx.ai`)
- `ORCHESTRATE_AGENT_ID` — the agent ID from your Orchestrate workspace

### 2. Set environment variables

Copy `.env.example` to `.env` and fill in:

```bash
ORCHESTRATE_API_KEY=your-api-key-here
ORCHESTRATE_INSTANCE_URL=https://your-instance.us-south.watsonx.ai
ORCHESTRATE_AGENT_ID=your-agent-id
```

**Never commit `.env` to Git.**

### 3. Create the Orchestrate agent

In your IBM watsonx Orchestrate workspace, create an agent with:

- **Name:** DMV Registration Assistant
- **Description:** Helps customers prepare for private-party vehicle registration
  at the SC DMV in Rock Hill, SC.
- **System prompt** (suggested):

```
You are a helpful DMV registration assistant for the IBM SkillsBuild demo
application. You help customers prepare for private-party vehicle registration
in York County, South Carolina.

You MUST:
- Only answer questions about the supported scenario: private-party purchase
  of a previously-titled SC vehicle in York County.
- Use the provided tool endpoints to look up real data (do not guess).
- Always display the full proposed action to the user before booking or
  cancelling an appointment.
- Include confirm_token="CONFIRM" in book/cancel tool calls ONLY after
  the user has explicitly confirmed the exact action.

You MUST NOT:
- Invent form numbers, fees, eligibility rules, or legal conclusions.
- Override backend data from tax, ownership, queue, or booking tools.
- Guarantee eligibility or legal ownership verification.
- Claim to be an official SCDMV service.

Always end responses involving requirements with:
"Verify current requirements at scdmv.net before your visit."
```

### 4. Register tool endpoints in Orchestrate

Register each backend endpoint as an Orchestrate tool. All require a Bearer token
in the `Authorization` header (the user's JWT from the DMV app login).

| Tool name | Endpoint | Method | Description |
|---|---|---|---|
| `get_checklist` | `/api/orchestrate/tools/checklist?case_id=` | GET | Checklist completion summary |
| `get_draft_status` | `/api/orchestrate/tools/draft?case_id=` | GET | Form 400 draft status |
| `get_queue_status` | `/api/orchestrate/tools/queue?location_id=` | GET | Live simulated queue snapshot |
| `get_tax_status` | `/api/orchestrate/tools/tax?vin=` | GET | Simulated tax record |
| `get_ownership_status` | `/api/orchestrate/tools/ownership?vin=&seller_name=` | GET | Simulated ownership match |
| `list_available_slots` | `/api/orchestrate/tools/slots?location_id=&date=` | GET | Available appointment slots |
| `book_appointment` | `/api/orchestrate/tools/book` | POST | Book appointment (**requires confirm_token="CONFIRM"**) |
| `cancel_appointment` | `/api/orchestrate/tools/cancel` | POST | Cancel appointment (**requires confirm_token="CONFIRM"**) |

**Important:** The `book` and `cancel` tools require `confirm_token: "CONFIRM"` in
the request body. The agent must show the user the exact proposed action and receive
explicit confirmation before calling these tools.

### 5. Set VITE_ORCHESTRATE_MOCK=false in frontend env

```bash
VITE_ORCHESTRATE_MOCK=false
```

When the backend has valid credentials (`orchestrate_enabled: true`), the chat
widget header shows "Powered by IBM watsonx Orchestrate" instead of "Demo mode".

---

## Security Model

| Concern | How it's handled |
|---|---|
| API key exposure | Key is server-side only, never in `VITE_*` vars or JS bundles |
| User identity | JWT resolved from `Authorization` header by the backend — model cannot supply user IDs |
| Write actions | `confirm_token == "CONFIRM"` required; backend validates it |
| Cross-user access | Case/appointment ownership verified on every tool call |
| Orchestrate errors | Backend falls back to mock mode on any Orchestrate error |

---

## Mock Mode Response Coverage

The rule-based mock handles these topics:
- Greetings / general help
- Required documents (title, bill of sale, ID, insurance, tax receipt, odometer, lien)
- Form 400 explanation
- York County tax requirements
- Queue wait time guidance
- Appointment booking flow
- Appointment cancellation / rescheduling
- Ownership lookup explanation
- DMV fees (provisional)
- Walk-in check-in
- Rock Hill office location
- Checklist and document status
- Official disclaimer / what the prototype does and does not do

For anything not matched, a fallback guidance message is returned.

---

## Limitations

- The Orchestrate proxy currently uses a generic `/v1/chat` endpoint shape.
  Adjust `call_orchestrate()` in `backend/app/services/orchestrate_service.py`
  to match the exact Orchestrate API version available in your lab environment.
- Session history is sent as a flat list; session persistence between page reloads
  is not implemented (session_id is regenerated on page load unless stored).
- Web Push (real background push notifications) requires VAPID key setup —
  see `.env.example` for `VAPID_*` variables. In-app polling notifications
  work without VAPID.

---

*Last updated: Milestone 6 — Orchestrate Integration.*
*Educational prototype only. Not affiliated with the SCDMV.*
