# Architecture

## Overview

DMV Registration Assistant is a **modular monolith** in a single Git repository.
React/TypeScript frontend, FastAPI/Python backend, PostgreSQL database, all
containerised with Docker Compose. IBM watsonx Orchestrate is an optional
server-side integration.

```
Browser (React + Vite)
  │
  ├── HTTP REST  ──────────────────────────────────── FastAPI /api/*
  ├── SSE stream ──────────────────────────────────── /api/queue/{id}/stream
  └── WebStorage (Zustand persist)                        │
                                                    SQLAlchemy 2
                                                          │
                                                    PostgreSQL 16
                                                          │
                                          ┌───────────────┴──────────────┐
                                          │                              │
                                   Synthetic data               IBM watsonx
                                   (queue sim,                  Orchestrate
                                   tax/ownership                (optional,
                                   records)                     server-side)
```

## Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | React 18 + TypeScript + Vite | Fast iteration, type safety, small bundle |
| Routing | React Router v6 | Standard SPA routing |
| State | Zustand (persist) | Lightweight, no boilerplate, localStorage sync |
| Styling | Tailwind CSS v3 | Utility-first, accessible component patterns |
| HTTP client | Axios | Interceptors for auth token injection + 401 logout |
| Backend | FastAPI + Pydantic v2 | High-performance, typed, async-ready |
| ORM | SQLAlchemy 2 + Alembic | Mature, migration-safe, row-locking support |
| Database | PostgreSQL 16 | ACID, JSON columns, `SELECT FOR UPDATE` locking |
| Auth | JWT (python-jose) + bcrypt | Stateless, swappable |
| PDF | reportlab | Pure Python, no external process |
| Queue sim | Custom (Poisson + log-normal) | Documented baseline, reproducible |
| SSE | FastAPI `StreamingResponse` | Real-time queue push without WebSocket complexity |
| AI assistant | IBM watsonx Orchestrate | Optional; mock mode when credentials absent |
| Containerisation | Docker Compose | Reproducible local dev |
| Backend tests | pytest + Starlette TestClient | Fast, SQLite in-memory, no running server |
| E2E tests | Playwright | Real browser, accessibility-friendly |

## Directory Layout

```
dmv-web-app/
├── frontend/
│   └── src/
│       ├── api/               client.ts (Axios + interceptors), dmv.ts (typed fns)
│       ├── components/        Layout, DisclaimerBanner, NotificationBell,
│       │                      AssistantWidget
│       ├── features/auth/     Zustand auth store (token, role, fullName)
│       ├── features/wizard/   IntakeWizard (3-step new-case flow)
│       ├── pages/             One component per route (11 pages)
│       └── types/api.ts       All shared TypeScript response types
│
├── backend/
│   └── app/
│       ├── models/models.py   14 SQLAlchemy ORM tables (see Data Model below)
│       ├── schemas/           Pydantic Form 400 field schema (validation)
│       ├── routers/           12 FastAPI routers (one per domain)
│       ├── services/
│       │   ├── auth_service.py   bcrypt hash/verify, JWT encode/decode
│       │   ├── deps.py           get_current_user, require_staff, require_admin
│       │   ├── queue_service.py  baseline wait estimator
│       │   ├── queue_simulator.py  full day simulator (Poisson, log-normal)
│       │   └── orchestrate_service.py  mock engine + real Orchestrate proxy
│       └── requirements_config/sc_private_party.py  SC DMV rules as config
│
├── migrations/versions/0001_initial.py   All tables in one migration
├── e2e/smoke.spec.ts          Playwright end-to-end tests
└── docs/                      Architecture, requirements sources, demo script,
                               Orchestrate setup, security limitations
```

## Data Model (14 tables)

```
users ──────────────┬── cases ──────────────┬── form_drafts
                    │                       ├── checklist_items ── documents
                    │                       ├── appointments ── slots ── locations
                    │                       └── queue_entries ── queue_events
                    ├── push_subscriptions
                    ├── notifications
                    └── audit_events

locations ──────────┬── slots
                    └── queue_entries

tax_records  (keyed by VIN)
ownership_records  (keyed by VIN)
```

Key ORM relationships:
- `Case` → `User` (many-to-one)
- `Appointment` → `Case` + `Slot` (both required)
- `QueueEntry` → `Case` + `Location` + optional `Appointment`
- `QueueEvent` → `QueueEntry` (immutable audit log)
- `Notification` → `User` (in-app alert store)

All times stored as UTC naive datetimes; displayed in `America/New_York`.

## API Surface (12 routers)

| Prefix | Auth | Description |
|--------|------|-------------|
| `/api/auth` | None | Register, login → JWT |
| `/api/cases` | User | CRUD for registration cases |
| `/api/cases/{id}/checklist` | Owner | Checklist items + lookups |
| `/api/cases/{id}/draft` | Owner | Form 400 draft + PDF stream |
| `/api/cases/{id}/documents` | Owner/Staff | Upload, list, delete |
| `/api/appointments` | User | Slot listing, booking, check-in, cancel |
| `/api/queue` | User | Snapshot, SSE stream, walk-in, public locations |
| `/api/lookup` | User | Simulated tax + ownership |
| `/api/staff` | Staff | Queue controls, appointments, metrics |
| `/api/notifications` | User | In-app alerts CRUD |
| `/api/orchestrate` | User | Chat proxy + 8 tool endpoints |
| `/api/admin` | Staff | Simulation trigger, location listing |

## Key Design Decisions

### Deterministic Requirements
Requirements are stored as structured Python config in
`backend/app/requirements_config/sc_private_party.py`. The assistant may
explain rules but never invents or overrides them. All eligibility decisions
happen in backend code, serving structured JSON to both the UI and the agent.

### Double-Booking Prevention
`POST /api/appointments` uses `SELECT … FOR UPDATE` on the `Slot` row before
incrementing `booked_count`. This serialises concurrent booking attempts at the
database level without application-level locking. Tests verify this with
`capacity=1` slots and concurrent requests.

### SSE Authentication
`EventSource` (the browser SSE API) cannot set custom headers. The
`/api/queue/{id}/stream` endpoint accepts the JWT as `?token=<jwt>` in addition
to the `Authorization` header. The frontend reads the token from localStorage
(Zustand persist store) and appends it to the URL. The queue page falls back
to polling if SSE fails.

### Upload Security
- Files stored at `UPLOAD_DIR` (outside web-served directories)
- Storage filename = `{uuid}_{original}` — original filename only in DB
- MIME type validated against both Content-Type header and file magic bytes
- Access control: only case owner or staff can retrieve/delete
- 10 MB size limit enforced at the router level

### Notifications Architecture
- **In-app:** `Notification` DB table; frontend polls `/api/notifications` every
  10 s; `NotificationBell` component shows unread badge + dropdown
- **Browser alerts:** `window.Notification` API called when a `"called"` event
  arrives during polling; permission requested via explicit user action
- **Web Push (deferred):** `PushSubscription` table and VAPID keys scaffolded;
  full service-worker implementation not yet complete

### Orchestrate Security Model
- API key held server-side only — never in `VITE_*` variables or JS bundles
- Backend resolves user identity from JWT on every request
- Write tools (`book`, `cancel`) require `confirm_token: "CONFIRM"` in body
- Agent must display the proposed action to the user before submitting
- Any Orchestrate error transparently falls back to mock mode
- Read-only tool calls do not require additional confirmation

### Queue Simulation
`queue_simulator.py` runs a discrete-event simulation:
1. Walk-in arrivals — Poisson distributed (default 8/hour)
2. Service duration — log-normal (default µ=12 min, σ=4 min)
3. 15% of transactions get a document-delay event (+8 min)
4. Entries waiting > 30 min are classified as no-shows
5. `estimate_wait_from_history()` uses p50 service time × queue length,
   upgrading to event-log history when ≥ 5 completed records exist
6. Documented baseline parameters; all outputs carry `simulated: true`

## Testing Strategy

| Layer | Tool | DB | Notes |
|-------|------|----|-------|
| Unit + integration | pytest + TestClient | SQLite in-memory | No Docker needed; 82 tests |
| End-to-end | Playwright | Running stack | Covers full user journeys |

Test files:
- `test_health.py` — health check, OpenAPI
- `test_auth.py` — registration, login, guards
- `test_cases.py` — case lifecycle, scenario guard
- `test_draft.py` — draft save/resume, PDF, requirements, lookups
- `test_booking.py` — booking, double-booking, cancel, queue, estimator
- `test_staff.py` — queue controls, metrics, notifications (16 tests)
- `test_orchestrate.py` — tool endpoints, mock chat, confirm_token, auth (23 tests)

## Security Limitations (Demo Context)

See [`docs/security-limitations.md`](security-limitations.md) for the full analysis.

Summary:
1. JWT secret must be rotated before any non-local deployment
2. Demo auth uses email/password only; production requires MFA and proper IdP
3. Uploaded files are not scanned for malware
4. Database runs without TLS in local Docker
5. No rate limiting, account lockout, or CSRF protection
6. SSE token-in-URL is acceptable for demo but not for production over HTTP
7. The system is not production-ready or legally compliant
