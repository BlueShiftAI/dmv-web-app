"""
SC DMV registration requirements configuration.

Scenario: Private-Party Vehicle Purchase — New Owner Registering
         a Previously-Titled SC Vehicle in York County, SC.

Sources documented in docs/requirements-sources.md.
All items marked with source_verified=false are provisional and require
confirmation against current official SCDMV publications.
"""

SCENARIO_KEY = "private_party_purchase"

SCENARIO_METADATA = {
    "key": SCENARIO_KEY,
    "label": "Private-Party Vehicle Purchase (Used Vehicle)",
    "description": (
        "Registering a previously-titled South Carolina vehicle purchased "
        "from a private seller in York County, SC."
    ),
    "supported": True,
    "disclaimer": (
        "Educational prototype. Not affiliated with the SCDMV. "
        "Queue, appointment, tax, and ownership data are simulated."
    ),
    "unsupported_message": (
        "This scenario isn't covered in this demo. "
        "Please visit scdmv.net or contact the Rock Hill SCDMV office directly."
    ),
}

# ---------------------------------------------------------------------------
# Required forms
# ---------------------------------------------------------------------------
REQUIRED_FORMS = [
    {
        "key": "form_400",
        "label": "SCDMV Form 400 — Application for Certificate of Title",
        "description": (
            "The primary form used to transfer vehicle title and apply for "
            "registration in South Carolina."
        ),
        "source_url": "https://www.scdmvonline.com/DMV-Forms/DMV-400",
        "source_verified": False,  # provisional — verify against current SCDMV site
        "retrieval_date": "2024-01-01",
        "notes": (
            "Source URL is illustrative; verify the current form number and URL at "
            "scdmvonline.com before using in a production context."
        ),
    },
]

# ---------------------------------------------------------------------------
# Required supporting documents
# ---------------------------------------------------------------------------
REQUIRED_DOCUMENTS = [
    {
        "key": "current_title",
        "label": "Current Vehicle Title (signed over by seller)",
        "description": (
            "The existing SC Certificate of Title must be signed by the seller "
            "on the assignment-of-title section. The buyer's name, address, "
            "and purchase price must be completed."
        ),
        "is_required": True,
        "is_conditional": False,
        "accepted_formats": ["image/jpeg", "image/png", "application/pdf"],
        "source_verified": False,
    },
    {
        "key": "bill_of_sale",
        "label": "Bill of Sale",
        "description": (
            "A signed bill of sale listing vehicle description (year, make, model, VIN), "
            "purchase price, sale date, buyer and seller names and addresses, "
            "and seller signature."
        ),
        "is_required": True,
        "is_conditional": False,
        "accepted_formats": ["image/jpeg", "image/png", "application/pdf"],
        "source_verified": False,
    },
    {
        "key": "photo_id",
        "label": "Valid Government-Issued Photo ID",
        "description": (
            "SC driver's license, US passport, or other government-issued photo ID "
            "of the buyer."
        ),
        "is_required": True,
        "is_conditional": False,
        "accepted_formats": ["image/jpeg", "image/png", "application/pdf"],
        "source_verified": False,
    },
    {
        "key": "proof_of_insurance",
        "label": "Proof of SC Liability Insurance",
        "description": (
            "Valid South Carolina liability insurance card or declaration page "
            "showing the vehicle VIN."
        ),
        "is_required": True,
        "is_conditional": False,
        "accepted_formats": ["image/jpeg", "image/png", "application/pdf"],
        "source_verified": False,
    },
    {
        "key": "tax_receipt",
        "label": "York County Property Tax Receipt or Paid Tax Notice",
        "description": (
            "Proof that property taxes have been paid to York County for the vehicle. "
            "In this demo the tax status is checked via simulated lookup; "
            "original receipt may still be required at the DMV window."
        ),
        "is_required": True,
        "is_conditional": False,
        "accepted_formats": ["image/jpeg", "image/png", "application/pdf"],
        "source_verified": False,
    },
    {
        "key": "odometer_disclosure",
        "label": "Odometer Disclosure Statement",
        "description": (
            "Required for vehicles less than 10 years old. "
            "Often completed on the back of the title."
        ),
        "is_required": False,
        "is_conditional": True,
        "condition_rule": "vehicle_year_within_10_years",
        "condition_note": "Required if the vehicle model year is within the last 10 years.",
        "accepted_formats": ["image/jpeg", "image/png", "application/pdf"],
        "source_verified": False,
    },
    {
        "key": "lien_release",
        "label": "Lien Release (if applicable)",
        "description": (
            "If the vehicle has an existing lien, a lien release letter from "
            "the lienholder is required."
        ),
        "is_required": False,
        "is_conditional": True,
        "condition_rule": "vehicle_has_lien",
        "condition_note": "Required only if the vehicle title shows an active lien.",
        "accepted_formats": ["image/jpeg", "image/png", "application/pdf"],
        "source_verified": False,
    },
]

# ---------------------------------------------------------------------------
# Preparation steps (ordered)
# ---------------------------------------------------------------------------
PREPARATION_STEPS = [
    {
        "order": 1,
        "key": "get_title_signed",
        "label": "Have seller sign the title",
        "detail": (
            "The seller must sign the 'Assignment of Title' section on the back of the "
            "current title. Do not fold or alter the title."
        ),
    },
    {
        "order": 2,
        "key": "pay_county_taxes",
        "label": "Pay York County property taxes",
        "detail": (
            "Visit the York County Treasurer's office or pay online before visiting the DMV. "
            "You must show proof of payment."
        ),
    },
    {
        "order": 3,
        "key": "obtain_insurance",
        "label": "Obtain SC liability insurance",
        "detail": (
            "You must have valid SC liability insurance on the vehicle before it can be "
            "registered. Contact your insurance provider."
        ),
    },
    {
        "order": 4,
        "key": "complete_form_400",
        "label": "Complete SCDMV Form 400",
        "detail": (
            "Fill out all buyer information, vehicle details, and purchase price. "
            "Use this app to prepare your draft."
        ),
    },
    {
        "order": 5,
        "key": "gather_documents",
        "label": "Gather all required documents",
        "detail": "Use the checklist in this app to verify all items before your visit.",
    },
    {
        "order": 6,
        "key": "book_appointment",
        "label": "Book a demo appointment (optional)",
        "detail": (
            "Booking an appointment may reduce your wait time. "
            "This demo appointment is not an official SCDMV reservation."
        ),
    },
]

# ---------------------------------------------------------------------------
# Fee schedule (simulated — York County)
# ---------------------------------------------------------------------------
FEE_NOTES = {
    "disclaimer": (
        "Fee amounts shown are for demonstration only. "
        "Verify current fees at scdmvonline.com or with the York County Auditor."
    ),
    "title_fee_cents": 1500,       # $15.00 — provisional
    "registration_fee_cents": 4000, # $40.00 — provisional
    "county_road_fee_cents": 500,  # $5.00 — provisional
    "source_verified": False,
}

# ---------------------------------------------------------------------------
# Official links
# ---------------------------------------------------------------------------
OFFICIAL_LINKS = [
    {
        "label": "SCDMV Official Website",
        "url": "https://www.scdmvonline.com",
    },
    {
        "label": "Rock Hill SCDMV Office",
        "url": "https://www.scdmvonline.com/SC-DMV-Locations/Rock-Hill",
    },
    {
        "label": "York County Treasurer (Tax Payments)",
        "url": "https://www.yorkcountygov.com/195/Treasurer",
    },
    {
        "label": "SCDMV Title Transfer Overview",
        "url": "https://www.scdmvonline.com/Vehicle-Owners/Titles/Title-Transfer",
    },
]
