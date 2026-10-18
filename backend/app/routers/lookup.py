"""
Lookup router: simulated tax and ownership status checks.
All results are synthetic demo data.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import OwnershipRecord, TaxRecord, User
from app.services.deps import get_current_user

router = APIRouter()


class TaxLookupResponse(BaseModel):
    vin: str
    status: str
    amount_cents: int | None
    county: str
    tax_year: int | None
    provider: str = "York County Demo Tax System"
    simulated: bool = True
    lookup_timestamp: str
    disclaimer: str = (
        "Simulated result. Does not replace official York County tax receipts or "
        "SCDMV verification. A missing or unavailable record does not confirm "
        "taxes are unpaid."
    )


class OwnershipLookupResponse(BaseModel):
    vin: str
    status: str
    owner_name: str | None
    county: str
    provider: str = "SC Demo Title Registry"
    simulated: bool = True
    lookup_timestamp: str
    disclaimer: str = (
        "Simulated result. Does not replace official SCDMV title verification. "
        "A no-match or not-found result does not constitute legal authority "
        "to sell or fraud detection."
    )


from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/tax/{vin}", response_model=TaxLookupResponse)
def lookup_tax(
    vin: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaxLookupResponse:
    record = db.query(TaxRecord).filter(TaxRecord.vin == vin.upper()).first()
    if not record:
        return TaxLookupResponse(
            vin=vin.upper(),
            status="not_found",
            amount_cents=None,
            county="York County",
            tax_year=None,
            lookup_timestamp=_now_iso(),
        )
    return TaxLookupResponse(
        vin=record.vin,
        status=record.status.value,
        amount_cents=record.amount_cents,
        county=record.county,
        tax_year=record.tax_year,
        lookup_timestamp=_now_iso(),
    )


@router.get("/ownership/{vin}", response_model=OwnershipLookupResponse)
def lookup_ownership(
    vin: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OwnershipLookupResponse:
    record = db.query(OwnershipRecord).filter(OwnershipRecord.vin == vin.upper()).first()
    if not record:
        return OwnershipLookupResponse(
            vin=vin.upper(),
            status="not_found",
            owner_name=None,
            county="York County",
            lookup_timestamp=_now_iso(),
        )
    return OwnershipLookupResponse(
        vin=record.vin,
        status="match",
        owner_name=record.owner_name,
        county=record.county,
        lookup_timestamp=_now_iso(),
    )
