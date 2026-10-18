"""
Form 400 field schema — Application for Certificate of Title (SC DMV).

All fields are for demo/educational purposes.
Field names and requirements are provisional; verify against current SCDMV Form 400.
Source: docs/requirements-sources.md
"""
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class VehicleInfo(BaseModel):
    """Vehicle identification section of Form 400."""
    vin: Annotated[str, Field(min_length=1, max_length=17, description="Vehicle Identification Number")]
    year: Annotated[int, Field(ge=1900, le=2100, description="Model year")]
    make: Annotated[str, Field(min_length=1, max_length=50, description="Vehicle make (e.g. Honda)")]
    model: Annotated[str, Field(min_length=1, max_length=50, description="Vehicle model (e.g. Accord)")]
    body_style: Annotated[str | None, Field(max_length=30, description="Body style (e.g. Sedan)")] = None
    color: Annotated[str | None, Field(max_length=30)] = None
    odometer_reading: Annotated[int | None, Field(ge=0, le=9999999)] = None
    odometer_unit: Annotated[str, Field(description="miles or kilometers")] = "miles"
    has_lien: Annotated[bool, Field(description="Does the vehicle have an active lien?")] = False


class BuyerInfo(BaseModel):
    """Buyer/applicant information section."""
    full_name: Annotated[str, Field(min_length=2, max_length=100)]
    address_line1: Annotated[str, Field(min_length=5, max_length=100)]
    address_line2: Annotated[str | None, Field(max_length=100)] = None
    city: Annotated[str, Field(min_length=1, max_length=60)]
    state: Annotated[str, Field(min_length=2, max_length=2)] = "SC"
    zip_code: Annotated[str, Field(min_length=5, max_length=10)]
    phone: Annotated[str | None, Field(max_length=20)] = None
    # Demo note: we intentionally do NOT collect SSN or DL number
    sc_county: Annotated[str, Field(description="SC county of residence")] = "York"


class SellerInfo(BaseModel):
    """Seller information for private-party transfer."""
    full_name: Annotated[str, Field(min_length=2, max_length=100)]
    address_line1: Annotated[str, Field(min_length=5, max_length=100)]
    address_line2: Annotated[str | None, Field(max_length=100)] = None
    city: Annotated[str, Field(min_length=1, max_length=60)]
    state: Annotated[str, Field(min_length=2, max_length=2)] = "SC"
    zip_code: Annotated[str, Field(min_length=5, max_length=10)]


class PurchaseInfo(BaseModel):
    """Purchase details."""
    purchase_price_dollars: Annotated[float, Field(ge=0, description="Purchase price in USD")]
    purchase_date: Annotated[str, Field(description="Date of sale (YYYY-MM-DD)")]
    sale_type: str = "private_party"


class Form400Draft(BaseModel):
    """
    Full Form 400 draft — all sections combined.
    All sections are optional to allow partial saves.
    """
    vehicle: VehicleInfo | None = None
    buyer: BuyerInfo | None = None
    seller: SellerInfo | None = None
    purchase: PurchaseInfo | None = None

    # Checklist-driven conditionals
    has_odometer_disclosure: bool | None = None
    has_lien_release: bool | None = None

    # Free-form notes from the customer
    additional_notes: Annotated[str | None, Field(max_length=1000)] = None


FORM_400_METADATA = {
    "key": "form_400",
    "label": "SCDMV Form 400 — Application for Certificate of Title",
    "description": (
        "Demo preparation summary based on SCDMV Form 400 fields. "
        "This draft is for preparation purposes only. "
        "It is not an officially accepted electronic submission."
    ),
    "sections": [
        {"key": "vehicle", "label": "Vehicle Information"},
        {"key": "buyer", "label": "Buyer / Applicant Information"},
        {"key": "seller", "label": "Seller Information"},
        {"key": "purchase", "label": "Purchase Details"},
    ],
    "disclaimer": (
        "This is a demo preparation summary, not an official SCDMV form. "
        "Electronic signatures and generated PDFs are not accepted by the SCDMV. "
        "You must complete and sign the actual Form 400 at the DMV office."
    ),
    "source_verified": False,
}
