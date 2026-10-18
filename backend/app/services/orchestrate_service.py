"""
Orchestrate integration service.

Handles:
  - Forwarding chat messages to IBM watsonx Orchestrate (when configured)
  - Returning mock responses when credentials are absent
  - Tool-callable backend endpoints (auth-enforced, never trust model-supplied user IDs)
"""
from __future__ import annotations

import httpx

from app.config import settings

MOCK_AGENT_NAME = "DMV Registration Assistant (Demo)"
MOCK_DISCLAIMER = (
    "This is a mock assistant. IBM watsonx Orchestrate credentials are not configured. "
    "Responses are generated from static requirements data."
)


# ---------------------------------------------------------------------------
# Mock response engine (rule-based, no LLM)
# ---------------------------------------------------------------------------

_MOCK_RULES: list[tuple[list[str], str]] = [
    (
        ["hello", "hi", "hey", "help"],
        (
            "Hello! I'm the DMV Registration Assistant. I can help you with:\n"
            "• Required documents for private-party vehicle registration\n"
            "• Checking your checklist and form status\n"
            "• Finding available appointment slots\n"
            "• Checking simulated tax and ownership status\n"
            "• Viewing current queue wait times\n\n"
            "What would you like to know?"
        ),
    ),
    (
        ["document", "documents", "what do i need", "requirements", "bring"],
        (
            "For a **private-party vehicle purchase** in York County, SC, you typically need:\n\n"
            "1. **Signed vehicle title** — seller must sign the assignment section\n"
            "2. **Bill of sale** — signed, with VIN, price, date, buyer & seller info\n"
            "3. **Valid government-issued photo ID** (SC license, passport, etc.)\n"
            "4. **Proof of SC liability insurance** showing the vehicle VIN\n"
            "5. **York County property tax receipt** or paid-tax notice\n"
            "6. **Odometer disclosure** — if vehicle is less than 10 years old\n"
            "7. **Lien release** — only if title shows an active lien\n\n"
            "Use the Checklist in your registration case to track these items.\n\n"
            "_Educational prototype. Requirements are provisional — verify at scdmv.net._"
        ),
    ),
    (
        ["form 400", "form400", "400", "application for title"],
        (
            "**SCDMV Form 400** is the Application for Certificate of Title. "
            "It is the primary form for transferring a vehicle title and registering "
            "a vehicle in South Carolina.\n\n"
            "You can prepare a draft of this form in the **Form** section of your case. "
            "Note: the generated draft is a preparation summary — not an officially accepted "
            "electronic submission. Bring your completed paper form to the DMV.\n\n"
            "_Source: scdmvonline.com (provisional — verify current form number)._"
        ),
    ),
    (
        ["tax", "property tax", "county tax", "york county tax"],
        (
            "You must pay **York County vehicle property tax** before registering at the DMV. "
            "Pay at the York County Treasurer's office or online at yorkcountygov.com.\n\n"
            "In this prototype you can run a **simulated tax lookup** from your Checklist page "
            "to see a demo result. The real lookup requires integration with York County — "
            "this prototype uses synthetic records.\n\n"
            "_Simulated data only — not a real tax-status check._"
        ),
    ),
    (
        ["wait", "queue", "how long", "wait time", "line"],
        (
            "You can check the **live simulated queue** on the Queue Status page. "
            "It shows estimated wait time, customers ahead, and queue status "
            "(Empty / Quiet / Active / Busy).\n\n"
            "The queue is updated every 5 seconds via live simulation. "
            "_This is simulated data — not an official SCDMV queue feed._"
        ),
    ),
    (
        ["appointment", "book", "schedule", "reserve", "slot"],
        (
            "You can book a demo appointment from the **Book Appointment** page or "
            "directly from your Dashboard using the 📅 Book button on a case.\n\n"
            "Steps:\n"
            "1. Select a location\n"
            "2. Choose a date\n"
            "3. Pick an available time slot\n"
            "4. Confirm your booking\n\n"
            "You'll receive a confirmation code. On the day, check in from the Booking page.\n\n"
            "_Demo appointments only — not official SCDMV bookings._"
        ),
    ),
    (
        ["cancel", "reschedule", "change appointment"],
        (
            "To cancel a demo appointment, go to the **Book Appointment** page. "
            "If you have an active booking, you'll see a Cancel button. "
            "After cancelling, the slot becomes available again and you can book a new one.\n\n"
            "_Demo appointments only — not official SCDMV bookings._"
        ),
    ),
    (
        ["ownership", "title", "seller", "who owns"],
        (
            "This prototype includes a **simulated ownership lookup** on the Checklist page. "
            "Enter the seller's name to check if it matches our synthetic ownership record "
            "for that VIN.\n\n"
            "Possible results: Match · No match · Not found · Provider unavailable.\n\n"
            "**Important:** A simulated match is NOT legal verification of ownership or "
            "authority to sell. Original signed title is required.\n\n"
            "_Synthetic records only — not connected to real SCDMV ownership data._"
        ),
    ),
    (
        ["fee", "cost", "how much", "price"],
        (
            "SC DMV fees vary. For this prototype:\n"
            "• Title fee: **$15** (provisional — verify at scdmv.net)\n"
            "• Registration fee: **$40** (provisional — varies by vehicle weight/type)\n\n"
            "These are illustrative figures used for demo purposes only. "
            "_Verify current fees at scdmv.net before your visit._"
        ),
    ),
    (
        ["walk", "walk-in", "walk in", "no appointment"],
        (
            "Walk-in customers are welcome at the DMV without an appointment. "
            "From your Dashboard, click the **🚶 Walk In** button next to a case "
            "to join the simulated queue directly.\n\n"
            "You'll see your queue position and estimated wait time. "
            "Watch the Queue Status page for updates.\n\n"
            "_Simulated queue — not an official SCDMV queue._"
        ),
    ),
    (
        ["rock hill", "location", "address", "where"],
        (
            "This prototype focuses on the **Rock Hill, SC SCDMV office**.\n\n"
            "Official address: 454 Crawford Road, Rock Hill, SC 29730\n"
            "_(Verify current hours and address at scdmv.net before visiting.)_\n\n"
            "A second fictional demo location is also available for dashboard comparison."
        ),
    ),
    (
        ["checklist", "status", "progress", "ready"],
        (
            "Your **Checklist** shows the status of each required document and preparation step. "
            "Open a case from your Dashboard to see it.\n\n"
            "Document statuses:\n"
            "• **Missing** — not yet uploaded\n"
            "• **Uploaded, pending review** — uploaded but not yet reviewed\n"
            "• **Reviewed** — confirmed by demo staff\n"
            "• **Needs replacement** — flagged for re-upload\n\n"
            "Upload sample document photos to each checklist item to track your preparation."
        ),
    ),
    (
        ["official", "real", "legal", "government", "actual dmv"],
        (
            "**Important disclaimer:** This is an educational prototype built for the "
            "IBM SkillsBuild AI Experiential Learning Lab. It is **not affiliated with "
            "the SCDMV** and does not submit anything to any government system.\n\n"
            "• Queue, appointment, tax, and ownership data are **simulated**\n"
            "• Generated PDFs are preparation summaries, not official forms\n"
            "• Document uploads are preparation aids, not legal submissions\n"
            "• For official DMV services, visit **scdmv.net**"
        ),
    ),
]


def get_mock_response(message: str) -> str:
    """Return a rule-based mock response for a user message."""
    msg_lower = message.lower()
    for keywords, response in _MOCK_RULES:
        if any(kw in msg_lower for kw in keywords):
            return response
    return (
        "I'm the DMV Registration Assistant. I can help with required documents, "
        "form preparation, appointments, queue wait times, and tax/ownership lookups "
        "for private-party vehicle registration in York County, SC.\n\n"
        "Try asking: _'What documents do I need?'_, _'How do I book an appointment?'_, "
        "or _'What is the current wait time?'_\n\n"
        f"_{MOCK_DISCLAIMER}_"
    )


# ---------------------------------------------------------------------------
# Real Orchestrate proxy
# ---------------------------------------------------------------------------

async def call_orchestrate(
    session_id: str,
    message: str,
    history: list[dict],
) -> str:
    """
    Send a message to the real IBM watsonx Orchestrate agent.
    Returns the assistant's text response.
    Raises httpx.HTTPError on failure.
    """
    if not settings.orchestrate_enabled:
        return get_mock_response(message)

    headers = {
        "Authorization": f"Bearer {settings.orchestrate_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "agent_id": settings.orchestrate_agent_id,
        "session_id": session_id,
        "message": message,
        "history": history,
    }
    base_url = settings.orchestrate_instance_url or ""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{base_url}/v1/chat",
            headers=headers,
            json=payload,
        )
        r.raise_for_status()
        data = r.json()
        # Orchestrate response shape: { "response": { "text": "..." } }
        return data.get("response", {}).get("text", "(no response)")
