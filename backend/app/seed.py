"""
Synthetic seed data for the DMV Web App demo.

Run with:
  docker compose exec backend python -m app.seed

Creates:
  - 1 Rock Hill demo location + 1 fictional "Lakeview" demo location
  - 3 demo customer accounts + 1 demo staff account
  - Appointment slots for the next 5 business days
  - Synthetic tax records (paid, unpaid, not_found) for demo VINs
  - Synthetic ownership records for demo VINs

All data is clearly demo/synthetic. No real government data.
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta

from app.database import SessionLocal, engine
from app.models.models import (
    Base,
    Location,
    OwnershipRecord,
    Slot,
    TaxRecord,
    TaxStatus,
    User,
    UserRole,
)
from app.services.auth_service import hash_password

# ---------------------------------------------------------------------------
# Demo identities (fully synthetic)
# ---------------------------------------------------------------------------
DEMO_USERS = [
    {
        "email": "alice.demo@example.com",
        "full_name": "Alice Demo",
        "password": "DemoPass1!",
        "role": UserRole.customer,
    },
    {
        "email": "bob.demo@example.com",
        "full_name": "Bob Demo",
        "password": "DemoPass1!",
        "role": UserRole.customer,
    },
    {
        "email": "carol.demo@example.com",
        "full_name": "Carol Demo",
        "password": "DemoPass1!",
        "role": UserRole.customer,
    },
    {
        "email": "staff.demo@example.com",
        "full_name": "Sam Staff",
        "password": "StaffPass1!",
        "role": UserRole.staff,
    },
]

# ---------------------------------------------------------------------------
# Demo locations
# ---------------------------------------------------------------------------
DEMO_LOCATIONS = [
    {
        "name": "Rock Hill SCDMV Office (Demo)",
        "address": "454 S Anderson Rd",
        "city": "Rock Hill",
        "state": "SC",
        "zip_code": "29730",
        "phone": "(803) 328-9000",
        "timezone": "America/New_York",
        "is_demo": True,
    },
    {
        "name": "Lakeview Demo DMV (Fictional)",
        "address": "1 Lakeview Blvd",
        "city": "Lakeview",
        "state": "SC",
        "zip_code": "00001",
        "phone": None,
        "timezone": "America/New_York",
        "is_demo": True,
    },
]

# ---------------------------------------------------------------------------
# Demo VINs and synthetic records
# All VINs are fictional / do not represent real vehicles
# ---------------------------------------------------------------------------
DEMO_TAX_RECORDS = [
    {
        "vin": "1HGCM82633A004352",
        "status": TaxStatus.paid,
        "amount_cents": 32500,
        "county": "York County",
        "tax_year": 2024,
        "notes": "Demo: taxes paid — Honda Accord",
    },
    {
        "vin": "2T1BURHE0JC034761",
        "status": TaxStatus.unpaid,
        "amount_cents": 18750,
        "county": "York County",
        "tax_year": 2024,
        "notes": "Demo: taxes unpaid — Toyota Corolla",
    },
    {
        "vin": "3VWFE21C04M000001",
        "status": TaxStatus.paid,
        "amount_cents": 28000,
        "county": "York County",
        "tax_year": 2024,
        "notes": "Demo: taxes paid — VW Jetta",
    },
]

DEMO_OWNERSHIP_RECORDS = [
    {
        "vin": "1HGCM82633A004352",
        "owner_name": "Jordan Smith (Demo Seller)",
        "county": "York County",
        "plate_number": "SC-DEMO-01",
        "title_number": "TITLE-DEMO-001",
        "is_demo": True,
    },
    {
        "vin": "2T1BURHE0JC034761",
        "owner_name": "Morgan Lee (Demo Seller)",
        "county": "York County",
        "plate_number": "SC-DEMO-02",
        "title_number": "TITLE-DEMO-002",
        "is_demo": True,
    },
    {
        "vin": "3VWFE21C04M000001",
        "owner_name": "Riley Park (Demo Seller)",
        "county": "York County",
        "plate_number": "SC-DEMO-03",
        "title_number": "TITLE-DEMO-003",
        "is_demo": True,
    },
]


def _next_weekdays(n: int = 5) -> list[date]:
    """Return the next n weekdays starting from tomorrow."""
    days: list[date] = []
    d = date.today() + timedelta(days=1)
    while len(days) < n:
        if d.weekday() < 5:  # Monday–Friday
            days.append(d)
        d += timedelta(days=1)
    return days


def create_slots(db, location_id: str, days: list[date]) -> None:
    """Create 30-minute appointment slots 8:30 AM – 4:30 PM for each day."""
    for day in days:
        hour = 8
        minute = 30
        while (hour, minute) < (16, 30):
            start = datetime(day.year, day.month, day.day, hour, minute)
            end = start + timedelta(minutes=30)
            # Avoid duplicates
            existing = (
                db.query(Slot)
                .filter(Slot.location_id == location_id, Slot.start_time == start)
                .first()
            )
            if not existing:
                db.add(Slot(location_id=location_id, start_time=start, end_time=end, capacity=3))
            minute += 30
            if minute >= 60:
                hour += 1
                minute = 0


def run_seed() -> None:
    print("Creating tables if they don't exist...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Users
        print("Seeding demo users...")
        for u in DEMO_USERS:
            if not db.query(User).filter(User.email == u["email"]).first():
                db.add(
                    User(
                        email=u["email"],
                        full_name=u["full_name"],
                        hashed_password=hash_password(u["password"]),
                        role=u["role"],
                    )
                )
        db.commit()

        # Locations
        print("Seeding demo locations...")
        location_ids: list[str] = []
        for loc in DEMO_LOCATIONS:
            existing = db.query(Location).filter(Location.name == loc["name"]).first()
            if existing:
                location_ids.append(existing.id)
            else:
                l = Location(**loc)
                db.add(l)
                db.flush()
                location_ids.append(l.id)
        db.commit()

        # Slots (for Rock Hill location only)
        print("Seeding appointment slots...")
        weekdays = _next_weekdays(5)
        create_slots(db, location_ids[0], weekdays)
        db.commit()

        # Tax records
        print("Seeding synthetic tax records...")
        for rec in DEMO_TAX_RECORDS:
            if not db.query(TaxRecord).filter(TaxRecord.vin == rec["vin"]).first():
                db.add(TaxRecord(**rec))
        db.commit()

        # Ownership records
        print("Seeding synthetic ownership records...")
        for rec in DEMO_OWNERSHIP_RECORDS:
            if not db.query(OwnershipRecord).filter(OwnershipRecord.vin == rec["vin"]).first():
                db.add(OwnershipRecord(**rec))
        db.commit()

        print("\n✅ Seed complete.")
        print("\nDemo accounts:")
        for u in DEMO_USERS:
            print(f"  {u['email']} / {u['password']}  ({u['role'].value})")
        print("\nDemo VINs:")
        for r in DEMO_TAX_RECORDS:
            print(f"  {r['vin']}  — tax: {r['status'].value}")
        print("\n⚠️  All data is synthetic. No real government data was used.")

    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
