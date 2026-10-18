"""
FastAPI application entry point.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, cases, checklist, documents, appointments, queue, staff, lookup, draft, requirements, admin, notifications, orchestrate

app = FastAPI(
    title="DMV Web App API",
    description=(
        "Educational prototype for the IBM SkillsBuild AI Experiential Learning Lab. "
        "Not affiliated with the SCDMV. All queue, appointment, tax, and ownership "
        "data are simulated."
    ),
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router,         prefix="/api/auth",         tags=["auth"])
app.include_router(cases.router,        prefix="/api/cases",        tags=["cases"])
app.include_router(checklist.router,    prefix="/api/cases",        tags=["checklist"])
app.include_router(documents.router,    prefix="/api/cases",        tags=["documents"])
app.include_router(appointments.router, prefix="/api/appointments", tags=["appointments"])
app.include_router(queue.router,        prefix="/api/queue",        tags=["queue"])
app.include_router(lookup.router,       prefix="/api/lookup",       tags=["lookup"])
app.include_router(staff.router,        prefix="/api/staff",        tags=["staff"])
app.include_router(draft.router,        prefix="/api/cases",        tags=["draft"])
app.include_router(requirements.router, prefix="/api/requirements", tags=["requirements"])
app.include_router(admin.router,        prefix="/api/admin",        tags=["admin"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(orchestrate.router,   prefix="/api/orchestrate",   tags=["orchestrate"])


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/api/health", tags=["health"])
async def health() -> dict:
    return {
        "status": "ok",
        "demo_mode": settings.demo_mode,
        "orchestrate_enabled": settings.orchestrate_enabled,
        "disclaimer": (
            "Educational prototype. Not affiliated with the SCDMV. "
            "All data are simulated."
        ),
    }
