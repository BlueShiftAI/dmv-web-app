# DMV Registration Assistant

**Educational prototype for the IBM SkillsBuild AI Experiential Learning Lab.**
Not affiliated with the South Carolina DMV (SCDMV). All queue, appointment,
tax, and ownership data are simulated.

---

## What This Is

A full-stack responsive web app that demonstrates what a DMV pre-visit preparation
tool could look like. It covers one supported scenario:

> **Private-party vehicle purchase** — registering a previously-titled SC vehicle
> purchased from a private seller, in York County, South Carolina.

Features implemented:

| # | Feature | Status |
|---|---------|--------|
| 1 | Guided intake wizard + requirements checklist | ✅ Complete |
| 2 | In-app fillable Form 400 draft + PDF export | ✅ Complete |
| 3 | Document photo upload with status tracking | ✅ Complete |
| 4 | Simulated tax & ownership lookups | ✅ Complete |
| 5 | Live-updating simulated queue + appointment booking | ✅ Complete |
| 6 | Staff dashboard — queue controls, metrics, notifications | ✅ Complete |
| 7 | In-app + browser turn-alert notifications | ✅ Complete |
| 8 | IBM watsonx Orchestrate assistant (mock + real mode) | ✅ Complete |

---

## Quick Start (Docker Compose)

### Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Docker Desktop | Latest | https://docker.com/products/docker-desktop |
| Node.js | 20 LTS | https://nodejs.org |
| Git | Any | https://git-scm.com |

### 1 — Clone and configure

```bash
git clone <your-repo-url> dmv-web-app
cd dmv-web-app
cp .env.example .env
```

Open `.env` and set a strong `SECRET_KEY`:

```bash
# Generate a secure key
openssl rand -hex 32
```

### 2 — Start all services

```bash
docker compose up --build
```

This starts:
- **PostgreSQL** on port 5432
- **FastAPI backend** on http://localhost:8000
- **React frontend** on http://localhost:5173

### 3 — Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

### 4 — Load synthetic seed data

```bash
docker compose exec backend python -m app.seed
```

The seed script prints login credentials and demo VINs to the console.

### 5 — Open the app

| URL | Description |
|-----|-------------|
| http://localhost:5173 | Customer-facing web app |
| http://localhost:8000/api/docs | Swagger UI (all API endpoints) |
| http://localhost:8000/api/redoc | ReDoc API reference |

---

## Local Development (without Docker)

### Backend only

Requires Python 3.11–3.14. The `.venv` is at `backend/.venv/`.

```bash
cd backend

# Create virtual environment (first time only)
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -r requirements.txt

# Point at your local PostgreSQL (or use SQLite for tests)
export DATABASE_URL=postgresql+psycopg2://dmvapp:changeme@localhost:5432/dmvdb

# Run migrations
alembic upgrade head

# Seed demo data
python -m app.seed

# Start development server
uvicorn app.main:app --reload --port 8000
```

### Frontend only

Requires Node.js 20 LTS.

```bash
cd frontend
npm install
npm run dev          # Starts Vite dev server on http://localhost:5173
```

The Vite config proxies `/api/*` to `http://localhost:8000` automatically.

---

## Running Tests

### Backend unit + integration tests (pytest)

Tests use an **in-memory SQLite database** — no PostgreSQL, no Docker needed.

```bash
cd backend
source .venv/bin/activate    # or .venv\Scripts\activate on Windows

pytest tests/ -v             # verbose
pytest tests/ -q             # quiet summary
pytest tests/test_staff.py   # single file
```

Current coverage: **82 tests, 82 pass**

| Test file | What it covers |
|-----------|---------------|
| `test_health.py` | Health check, OpenAPI, docs endpoints |
| `test_auth.py` | Register, login, duplicate email, wrong password |
| `test_cases.py` | Case creation, scenario guard, auth |
| `test_draft.py` | Form draft save/resume, PDF generation, requirements, lookups |
| `test_booking.py` | Booking, double-booking prevention, cancel/rebook, queue, estimator |
| `test_staff.py` | Staff queue controls, metrics, notifications |
| `test_orchestrate.py` | Tool endpoints, mock chat, confirm_token gate, auth |

### End-to-end tests (Playwright)

Requires Node.js and a running full stack.

```bash
# Start the full stack first
docker compose up

# Install browsers (first time)
cd frontend
npx playwright install --with-deps chromium

# Run all e2e tests
npx playwright test

# Run with browser visible (headed)
npx playwright test --headed

# Run a single spec
npx playwright test e2e/smoke.spec.ts
```

E2E tests live in `e2e/` and cover:
- Home page and disclaimer
- Login / register flows
- Full customer journey (create case → checklist → form → document upload → booking → check-in)
- Queue status page
- Staff dashboard controls
- Assistant widget open/close and mock response

> **Note:** E2E tests require Node.js and a running stack.
> The backend pytest suite does **not** require Node.js or Docker.

---

## Environment Variables

Full list with descriptions in [`.env.example`](.env.example).

### Backend (server-side only)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `SECRET_KEY` | Yes | (insecure dev value) | JWT signing secret — **change before any deployment** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | JWT expiry |
| `CORS_ORIGINS` | No | `http://localhost:5173` | Allowed frontend origins |
| `UPLOAD_DIR` | No | `/app/uploads` | Upload storage root (outside web root) |
| `MAX_UPLOAD_SIZE_BYTES` | No | `10485760` | 10 MB upload limit |
| `DEMO_MODE` | No | `true` | Enables synthetic data endpoints |
| `ORCHESTRATE_API_KEY` | No | — | IBM watsonx Orchestrate key (optional) |
| `ORCHESTRATE_INSTANCE_URL` | No | — | Orchestrate instance base URL |
| `ORCHESTRATE_AGENT_ID` | No | — | Orchestrate agent ID |
| `VAPID_PUBLIC_KEY` | No | — | Web Push VAPID public key |
| `VAPID_PRIVATE_KEY` | No | — | Web Push VAPID private key |

### Frontend (Vite — browser-visible, no secrets)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `""` | Backend URL (empty = same origin via proxy) |
| `VITE_ORCHESTRATE_MOCK` | `true` | Use mock assistant when Orchestrate not configured |

**Never put `ORCHESTRATE_API_KEY` or any secret in a `VITE_` variable.**

---

## Demo Accounts (after running seed)

| Email | Password | Role |
|-------|----------|------|
| alice.demo@example.com | DemoPass1! | customer |
| bob.demo@example.com | DemoPass1! | customer |
| carol.demo@example.com | DemoPass1! | customer |
| staff.demo@example.com | StaffPass1! | staff |

## Demo VINs

| VIN | Tax Status | Owner Name | Notes |
|-----|-----------|------------|-------|
| 1HGCM82633A004352 | Paid ($325.00) | Jordan Smith | Use for a successful journey |
| 2T1BURHE0JC034761 | Unpaid ($187.50) | Morgan Lee | Demonstrates unpaid-tax block |
| 3VWFE21C04M000001 | Paid ($280.00) | Riley Park | Second paid example |

---

## API Overview

The backend exposes a REST API at `/api/*`. All authenticated endpoints require:

```
Authorization: Bearer <jwt-token>
```

| Prefix | Description |
|--------|-------------|
| `/api/auth` | Register, login |
| `/api/cases` | Registration cases |
| `/api/cases/{id}/checklist` | Document checklist |
| `/api/cases/{id}/draft` | Form 400 draft + PDF |
| `/api/cases/{id}/documents` | Document uploads |
| `/api/appointments` | Slots, booking, check-in, cancel |
| `/api/queue` | Live queue snapshot, SSE stream, walk-in, locations |
| `/api/lookup` | Simulated tax and ownership lookups |
| `/api/staff` | Queue controls, appointments, metrics (staff only) |
| `/api/notifications` | In-app alerts |
| `/api/orchestrate` | Chat proxy + tool endpoints for Orchestrate agent |
| `/api/admin` | Simulation trigger, locations (admin/staff only) |

Full interactive documentation: http://localhost:8000/api/docs

---

## Project Structure

```
dmv-web-app/
├── .env.example               Safe template (no secrets)
├── .gitignore
├── docker-compose.yml
├── README.md
│
├── frontend/
│   ├── src/
│   │   ├── api/               Axios client + typed API functions
│   │   ├── components/        Layout, DisclaimerBanner, NotificationBell,
│   │   │                      AssistantWidget
│   │   ├── features/
│   │   │   ├── auth/          Zustand auth store (persist)
│   │   │   └── wizard/        Intake wizard component
│   │   ├── pages/             One component per route
│   │   └── types/             Shared TypeScript types
│   ├── e2e/                   ← lives here via playwright.config.ts
│   ├── package.json
│   ├── vite.config.ts
│   └── playwright.config.ts
│
├── backend/
│   ├── app/
│   │   ├── models/models.py   All 14 SQLAlchemy ORM tables
│   │   ├── routers/           One router per domain (12 files)
│   │   ├── services/          Auth, deps, queue estimator,
│   │   │                      queue simulator, Orchestrate service
│   │   ├── schemas/           Pydantic Form 400 schema
│   │   └── requirements_config/  SC DMV rules as structured config
│   ├── migrations/            Alembic versions
│   ├── tests/                 pytest suite (82 tests)
│   ├── requirements.txt
│   └── seed.py
│
├── e2e/
│   └── smoke.spec.ts          Playwright end-to-end tests
│
└── docs/
    ├── architecture.md
    ├── demo-script.md
    ├── orchestrate-setup.md
    ├── requirements-sources.md
    └── security-limitations.md
```

---

## Orchestrate Assistant

The floating 💬 chat widget works in two modes:

| Mode | When | Behaviour |
|------|------|-----------|
| **Mock (demo)** | `ORCHESTRATE_API_KEY` not set | Rule-based responses from SC DMV requirements config |
| **Real Orchestrate** | Credentials configured | Proxied through backend; API key never reaches browser |

See [`docs/orchestrate-setup.md`](docs/orchestrate-setup.md) for full setup instructions
including agent system prompt, tool registration, and security model.

---

## Troubleshooting

### `docker compose up` fails — "port already in use"
Stop any existing PostgreSQL on port 5432:
```bash
# Linux/macOS
sudo systemctl stop postgresql
# Windows: Services → "PostgreSQL" → Stop
```

### Frontend shows "Network Error"
- Confirm backend is running: `curl http://localhost:8000/api/health`
- Check `VITE_API_BASE_URL` in `.env` matches the backend URL
- In Docker Compose the Vite proxy handles this automatically

### Migrations fail — "relation already exists"
```bash
docker compose exec backend alembic downgrade base
docker compose exec backend alembic upgrade head
```

### Seed fails — "duplicate key"
The seed is idempotent and skips existing records. If it still fails,
check for schema mismatches between the migration and the model, then
re-run migrations from base.

### Backend pytest import errors on Windows
Ensure you're running from inside the `backend/` directory and the venv is activated:
```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m pytest tests/ -v
```

### `npm install` fails
Ensure Node.js 20 LTS is installed: `node --version` should print `v20.x.x`.

### SSE queue stream doesn't update in browser
The SSE endpoint requires a `?token=<jwt>` query parameter because `EventSource`
cannot set headers. The `QueuePage` reads the token from `localStorage` (Zustand persist key `dmv-auth`) and appends it automatically. If the token is missing, the page falls back to polling.

### Notifications don't appear as browser alerts
The `NotificationBell` component requests `Notification` permission via the
"Enable alerts" button in the dropdown. Permission must be granted explicitly.
Alerts only fire while the browser tab is open (in-app polling mode).
Web Push (background alerts) requires VAPID key setup — see `.env.example`.

---

## Known Limitations

- **Node.js / Docker not installed** — If Node.js is absent the frontend cannot
  be compiled or dev-served. Backend tests work without Node.js or Docker.
- **No real SCDMV integration** — Tax, ownership, queue, and appointment data
  are entirely synthetic.
- **Electronic signatures not accepted** — Generated PDFs are preparation
  summaries only, not officially accepted forms.
- **OCR / document authenticity** — Not implemented; deferred to a future milestone.
- **Web Push (background notifications)** — Requires VAPID key generation and
  a service worker; in-app polling notifications work without it.
- **Alembic migration** covers the initial schema. The `Notification` table added
  in M5 is reflected in the ORM but may need a new migration if running against
  an existing PostgreSQL instance. For fresh installs `alembic upgrade head`
  creates all tables correctly via `CREATE TABLE IF NOT EXISTS`.

---

## Disclaimer

This is an educational prototype built for the IBM SkillsBuild AI Experiential
Learning Lab. It is **not affiliated with, endorsed by, or connected to** the
South Carolina DMV (SCDMV), York County, or any government agency.

Requirements, forms, fees, and links are based on provisional research and may
not reflect current official rules. Users must verify all requirements at
**scdmvonline.com** before visiting a DMV office.

The system is not production-ready and must not be used for legally binding
transactions, official government submissions, or real identity verification.
