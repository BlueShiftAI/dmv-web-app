"""
Admin router — simulation control endpoints.
Staff/admin only.  Not exposed in the public API surface.

POST /api/admin/simulate/{location_id}  — run a day simulation for a location
GET  /api/admin/locations               — list demo locations (for the UI)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Location, User
from app.services.deps import require_staff
from app.services.queue_simulator import DEFAULT_PARAMS, run_simulation

router = APIRouter()


class SimulateRequest(BaseModel):
    hours: float = DEFAULT_PARAMS["simulation_hours"]
    arrival_rate_per_hour: float = DEFAULT_PARAMS["arrival_rate_per_hour"]
    active_windows: int = DEFAULT_PARAMS["active_windows"]


class LocationResponse(BaseModel):
    id: str
    name: str
    city: str
    is_demo: bool

    model_config = {"from_attributes": True}


@router.get("/locations", response_model=list[LocationResponse])
def list_locations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> list[LocationResponse]:
    locs = db.query(Location).filter(Location.is_active.is_(True)).all()
    return [LocationResponse.model_validate(l) for l in locs]


@router.post("/simulate/{location_id}")
def trigger_simulation(
    location_id: str,
    payload: SimulateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> dict:
    loc = db.get(Location, location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    if not loc.is_demo:
        raise HTTPException(status_code=403, detail="Simulation only allowed on demo locations")

    params = {
        "simulation_hours": payload.hours,
        "arrival_rate_per_hour": payload.arrival_rate_per_hour,
        "active_windows": payload.active_windows,
    }
    summary = run_simulation(
        db=db,
        location_id=location_id,
        staff_user_id=current_user.id,
        params=params,
    )
    return {"ok": True, "summary": summary}
