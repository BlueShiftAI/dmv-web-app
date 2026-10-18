# Demo Script — DMV Registration Assistant

**IBM SkillsBuild AI Experiential Learning Lab**
Educational prototype. Not affiliated with the SCDMV.
All queue, appointment, tax, and ownership data are simulated.

---

## Before You Begin

### Pre-flight checklist

- [ ] Stack running: `docker compose up` (or backend + frontend separately)
- [ ] Migrations run: `alembic upgrade head`
- [ ] Seed data loaded: `python -m app.seed` — note the printed location IDs
- [ ] Browser open to http://localhost:5173
- [ ] Two browser windows ready (one for customer, one for staff)
- [ ] Optional: second monitor for staff window

### Demo accounts

| Actor | Email | Password | Role |
|-------|-------|----------|------|
| Alice (customer) | alice.demo@example.com | DemoPass1! | customer |
| Sam (staff) | staff.demo@example.com | StaffPass1! | staff |

### Demo VINs

| VIN | Tax Status | Owner | Use for |
|-----|-----------|-------|---------|
| `1HGCM82633A004352` | Paid ($325.00) | Jordan Smith | Successful journey |
| `2T1BURHE0JC034761` | Unpaid ($187.50) | Morgan Lee | Unpaid-tax demo |

---

## Act 1 — Customer Journey (~12 minutes)

### Scene 1.1 — Register and log in (1 min)

**Window A (Customer)**

1. Open http://localhost:5173
2. Point out the **disclaimer banner** at the top — _"Educational prototype. Not affiliated with the SCDMV."_
3. Click **Get started**
4. Fill in a name, email, password → click **Create Account**
5. You land on the Dashboard
   - _"This is what a customer sees the moment they log in."_

---

### Scene 1.2 — Start a new registration case (1 min)

1. Click **+ Start New Case**
2. The **Intake Wizard** opens (3-step):
   - Step 1: Confirm scenario — _"Private-party purchase"_
   - Step 2: Enter VIN `1HGCM82633A004352`
   - Step 3: Confirm
3. Click **Start Preparation**
4. You land on the **Checklist** for that case
   - _"The system determines the required documents automatically from the structured requirements config — not from the AI."_

**Key talking points:**
- The supported scenario is deliberately narrow; unsupported cases redirect to scdmv.net
- Requirement decisions are deterministic backend code, not AI invention

---

### Scene 1.3 — Review the requirements checklist (2 min)

On the Checklist page:

1. Walk through the **7 checklist items**:
   | Item | Always required? |
   |------|-----------------|
   | Signed vehicle title | Yes |
   | Bill of sale | Yes |
   | Valid photo ID | Yes |
   | SC liability insurance | Yes |
   | York County tax receipt | Yes |
   | Odometer disclosure | Conditional (< 10 yr old vehicle) |
   | Lien release | Conditional (if lien on title) |

2. Expand the **conditional items** — show the condition note
3. Click **Check Tax Status** → result: `PAID — $325.00` _(Jordan Smith, York County)_
4. Click **Check Ownership** → enter seller name `Jordan Smith` → result: `Match`
5. Point out:
   - Both results show `"Simulated"` and a `"Provider"` label
   - _"A simulated match does not legally verify ownership."_

**Key talking points:**
- Tax/ownership are replaceable provider interfaces backed by synthetic records
- The checklist drives document uploads in the next step

---

### Scene 1.4 — Fill in the Form 400 draft (2 min)

1. Click **Form** (top nav or case card)
2. Walk through the **5 tabs**: Vehicle · Buyer · Seller · Purchase · Review
3. Enter vehicle details:
   - VIN: `1HGCM82633A004352`, Year: `2020`, Make: `Honda`, Model: `Civic`
4. Enter buyer name and a York County address
5. Enter seller name: `Jordan Smith`
6. Enter purchase price: `$8500`, date: today
7. Click **Review** tab → show the summary
8. Click **Save Draft**
9. Click **Download PDF** → open the downloaded file
   - _"This is a preparation summary — not an official SCDMV form. The real Form 400 must be obtained from scdmv.net."_

---

### Scene 1.5 — Upload sample documents (1 min)

1. Click **Documents** on the case card (or nav)
2. Click the upload area next to **Bill of Sale**
3. Upload any sample image or PDF (< 10 MB)
4. Status shows: **"Uploaded, pending review"**
5. Point out the Delete button and the access-control note
   - _"Staff must mark documents reviewed. An upload is a preparation aid, not proof of authenticity."_

---

### Scene 1.6 — Book a demo appointment (2 min)

1. Click **📅 Book** on the case card → the Booking page opens
2. The case is pre-selected
3. Select the **Rock Hill Demo** location
4. Pick **today's date** (or the date with seeded slots)
5. Click a **green available time slot**
6. Click **Reserve [time] on [date]**
7. The confirmation dialog appears — read the disclaimer aloud:
   _"This is a prototype reservation only. It is not an official SCDMV booking and does not guarantee immediate service at the appointment time."_
8. Click **Confirm Booking**
9. Confirmation card appears with the **8-character confirmation code**

---

### Scene 1.7 — Check-in and join the queue (1 min)

Still on the Booking page:

1. The appointment card shows status **booked**
2. Click **Check In Now**
3. Status changes to **confirmed** — success message: _"You are checked in! Head to the queue tracker."_
4. Navigate to **Queue Status** (nav or link)
5. Select the Rock Hill location
6. Show the live queue display:
   - Waiting count, In Service count, Estimated wait, Status badge
   - Live mode indicator: **Live (SSE)** or **Polling**
   - _"Updates every 5 seconds from the queue simulator."_

**Key talking points:**
- SSE (Server-Sent Events) provides real-time push; polling is the automatic fallback
- All data is clearly labelled _"Simulated live data"_

---

### Scene 1.8 — The notification bell (30 sec)

1. Point out the **🔔 bell** in the nav bar
2. Click it to open the dropdown — currently no notifications
3. _"When staff calls this customer, a notification will appear here — and optionally fire a browser alert."_

---

## Act 2 — Staff Dashboard (~5 minutes)

### Scene 2.1 — Sign in as staff

**Window B (Staff)**

1. Open a new browser window to http://localhost:5173
2. Sign in as `staff.demo@example.com` / `StaffPass1!`
3. Nav bar shows **Staff Dashboard** link → click it

---

### Scene 2.2 — Queue tab (2 min)

1. The location is **auto-populated** from the seed data
2. The **Queue** tab is active — shows Alice's entry with status **waiting**
3. Point out columns:
   - Case ID, Status chip (colour-coded), Walk-in/Appt, Checked In, Wait time
4. Click **Call** → status changes to **called** (yellow chip)
5. Switch back to **Window A (Customer)**:
   - The 🔔 bell shows a **red badge (1 unread)**
   - Click the bell → _"You've been called! Please proceed to the service window."_
   - _If browser Notification permission was granted, a desktop alert also fired_
6. Back in **Window B (Staff)**:
   - Click **Start** → status: **in service** (blue chip)
   - Click **Complete** → entry disappears from the queue

**Bonus — document flag:**
- If time permits, repeat with a second entry and click **🚩 Flag**
- The row turns red — shows document review is needed
- Click **✗ No-show** on a waiting entry to demonstrate that path

---

### Scene 2.3 — Appointments tab (1 min)

1. Click the **📅 Appointments** tab
2. Today's booked appointments for this location are listed
3. Alice's booking shows confirmation code and **✓ In queue** (since she checked in)
4. _"Staff can see who has checked in and who is still pending."_

---

### Scene 2.4 — Metrics tab (2 min)

1. Click the **📊 Metrics** tab
2. If the simulation was run (`POST /api/admin/simulate/{location_id}`), metrics show:
   - **Completed**, **No-shows**, **Doc delays** KPI cards
   - **Median wait** and **P90 wait** times
   - **Completions by hour** bar chart
3. Change the **Period** dropdown to `Last 48 h` — chart updates
4. Highlight:
   - _"Separate waiting time from processing time — two different bottlenecks."_
   - _"All labelled as synthetic demo results."_

**Tip for a richer demo:** Before the demo, trigger a simulation from the API:
```bash
curl -X POST http://localhost:8000/api/admin/simulate/<location-id> \
  -H "Authorization: Bearer <staff-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"hours": 8, "arrival_rate_per_hour": 12, "active_windows": 3}'
```

---

## Act 3 — AI Assistant (~3 minutes)

### Scene 3.1 — Open the assistant widget

**Window A (Customer, logged in)**

1. Click the **💬 floating button** (bottom-right corner)
2. The chat panel opens — note:
   - **Demo mode** label (or "Powered by IBM watsonx Orchestrate" if configured)
   - Yellow disclaimer banner inside the widget
   - Suggestion chips

---

### Scene 3.2 — Ask about documents

1. Click the suggestion chip **"What documents do I need?"**
2. The assistant responds with the full document checklist
3. Point out: **bold formatting**, bullet points, inline italic disclaimer
4. _"The response comes from the same requirements config the backend uses — not invented by the AI."_

---

### Scene 3.3 — Ask about the queue

1. Type: `"How long is the wait?"`
2. Assistant explains the queue page and simulated data
3. _"In real Orchestrate mode, the assistant would call `GET /api/orchestrate/tools/queue` to fetch a live snapshot."_

---

### Scene 3.4 — Ask about booking (tool flow demo)

1. Type: `"How do I book an appointment?"`
2. Show the step-by-step booking guidance
3. Explain the confirmation-token gate:
   - _"The backend requires `confirm_token: 'CONFIRM'` for any booking or cancellation. The agent must show the user the exact action and wait for explicit approval before the tool call goes through."_
   - _"This prevents the assistant from booking appointments silently."_

---

### Scene 3.5 — Disclaimer and limits

1. Type: `"Is this the real DMV?"`
2. The assistant responds with the full disclaimer
3. Read aloud: _"This is an educational prototype built for the IBM SkillsBuild AI Experiential Learning Lab. It is not affiliated with the SCDMV..."_

---

## Optional Extras

### Demonstrate unpaid tax (2 min)
1. Create a second case with VIN `2T1BURHE0JC034761`
2. On the checklist, click **Check Tax Status**
3. Result: `UNPAID — $187.50`
4. _"The tax status check demonstrates the provider interface. A future authorized integration could automate receipt verification."_

### Demonstrate walk-in check-in (1 min)
1. From the Dashboard, click **🚶 Walk In** on a case
2. A green banner appears: _"You are #2 in the queue. Est. wait: 14 min."_
3. Navigate to Queue Status → position shown in real time
4. _"Walk-in and appointment paths both produce the same queue entry type."_

### Demonstrate double-booking prevention (1 min)
1. Open two browser tabs with the same user logged in
2. Both tabs load the same slot
3. Tab A books it → slot becomes **Full**
4. Tab B tries to book → gets **409 Slot is fully booked**
5. _"Row-level locking in PostgreSQL prevents concurrent overbooking."_

---

## Closing Points

| Capability | How it works |
|-----------|-------------|
| Requirements checklist | Deterministic Python config — AI cannot override |
| Tax / ownership lookups | Replaceable provider interfaces, synthetic records |
| Queue simulation | Poisson arrivals, log-normal service times, p50/p90 estimator |
| Double-booking prevention | `SELECT … FOR UPDATE` row lock + atomic counter |
| In-app notifications | Polling `/api/notifications` every 10 s |
| Browser alerts | `window.Notification` API, permission-gated |
| Orchestrate security | API key server-side only; confirm_token gate on writes |
| Mock mode | Full app works without Orchestrate credentials |

---

*All data shown is synthetic. This prototype does not submit anything to any government system.*
*Verify requirements at **scdmvonline.com** before visiting a DMV office.*
