"""
Requirements router: serve structured SC DMV requirements config to the frontend.
GET /api/requirements               — full requirements for the supported scenario
GET /api/requirements/forms         — form metadata only
GET /api/requirements/documents     — required documents list
GET /api/requirements/steps         — preparation steps
"""
from __future__ import annotations

from fastapi import APIRouter

from app.requirements_config.sc_private_party import (
    FEE_NOTES,
    OFFICIAL_LINKS,
    PREPARATION_STEPS,
    REQUIRED_DOCUMENTS,
    REQUIRED_FORMS,
    SCENARIO_METADATA,
)

router = APIRouter()


@router.get("")
def get_requirements() -> dict:
    return {
        "scenario": SCENARIO_METADATA,
        "forms": REQUIRED_FORMS,
        "documents": REQUIRED_DOCUMENTS,
        "steps": PREPARATION_STEPS,
        "fee_notes": FEE_NOTES,
        "official_links": OFFICIAL_LINKS,
    }


@router.get("/forms")
def get_forms() -> list:
    return REQUIRED_FORMS


@router.get("/documents")
def get_documents() -> list:
    return REQUIRED_DOCUMENTS


@router.get("/steps")
def get_steps() -> list:
    return PREPARATION_STEPS
