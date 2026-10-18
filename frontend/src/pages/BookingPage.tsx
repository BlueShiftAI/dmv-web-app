import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  listLocations,
  listSlots,
  bookAppointment,
  cancelAppointment,
  getAppointmentForCase,
  checkIn,
} from "../api/dmv";
import { listCases } from "../api/dmv";
import type {
  LocationResponse,
  SlotResponse,
  AppointmentResponse,
  CaseResponse,
} from "../types/api";

// ── helpers ────────────────────────────────────────────────────────────────

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function fmt12(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    timeZone: "America/New_York",
  });
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
    timeZone: "America/New_York",
  });
}

// ── component ──────────────────────────────────────────────────────────────

export default function BookingPage() {
  const [searchParams] = useSearchParams();
  const initialCaseId = searchParams.get("case_id") ?? "";

  // data
  const [locations, setLocations] = useState<LocationResponse[]>([]);
  const [cases, setCases] = useState<CaseResponse[]>([]);
  const [slots, setSlots] = useState<SlotResponse[]>([]);
  const [existing, setExisting] = useState<AppointmentResponse | null>(null);

  // selections
  const [caseId, setCaseId] = useState(initialCaseId);
  const [locationId, setLocationId] = useState("");
  const [date, setDate] = useState(today());
  const [selectedSlot, setSelectedSlot] = useState<SlotResponse | null>(null);

  // ui state
  const [loadingLocs, setLoadingLocs] = useState(true);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [loadingExisting, setLoadingExisting] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [booking, setBooking] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [checkingIn, setCheckingIn] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // ── load locations + cases on mount ──────────────────────────────────────
  useEffect(() => {
    Promise.all([listLocations(), listCases()])
      .then(([locs, cs]) => {
        setLocations(locs);
        setCases(cs);
        if (locs.length > 0) setLocationId(locs[0].id);
      })
      .catch(() => setError("Could not load locations."))
      .finally(() => setLoadingLocs(false));
  }, []);

  // ── fetch existing appointment when caseId changes ───────────────────────
  useEffect(() => {
    if (!caseId) { setExisting(null); return; }
    setLoadingExisting(true);
    getAppointmentForCase(caseId)
      .then(setExisting)
      .catch(() => setExisting(null))
      .finally(() => setLoadingExisting(false));
  }, [caseId]);

  // ── fetch slots when location/date changes ───────────────────────────────
  useEffect(() => {
    if (!locationId || !date) { setSlots([]); return; }
    setLoadingSlots(true);
    setSelectedSlot(null);
    setError(null);
    listSlots(locationId, date)
      .then(setSlots)
      .catch(() => setError("Could not load slots for this date."))
      .finally(() => setLoadingSlots(false));
  }, [locationId, date]);

  // ── book ─────────────────────────────────────────────────────────────────
  const handleBook = async () => {
    if (!caseId || !selectedSlot) return;
    setBooking(true);
    setError(null);
    try {
      const appt = await bookAppointment(caseId, selectedSlot.id);
      setExisting(appt);
      setConfirming(false);
      setSelectedSlot(null);
      setSuccess(`Appointment booked! Confirmation: ${appt.confirmation_code}`);
    } catch (e: any) {
      setError(e.response?.data?.detail ?? "Booking failed. Please try again.");
    } finally {
      setBooking(false);
    }
  };

  // ── cancel ────────────────────────────────────────────────────────────────
  const handleCancel = async () => {
    if (!existing) return;
    if (!window.confirm("Cancel your demo appointment?")) return;
    setCancelling(true);
    setError(null);
    try {
      await cancelAppointment(existing.id);
      setExisting(null);
      setSuccess("Appointment cancelled.");
    } catch (e: any) {
      setError(e.response?.data?.detail ?? "Cancellation failed.");
    } finally {
      setCancelling(false);
    }
  };

  // ── check in ─────────────────────────────────────────────────────────────
  const handleCheckIn = async () => {
    if (!existing) return;
    setCheckingIn(true);
    setError(null);
    try {
      await checkIn(existing.id);
      // reload appointment to reflect confirmed status
      const updated = await getAppointmentForCase(caseId);
      setExisting(updated);
      setSuccess("You are checked in! Head to the queue tracker.");
    } catch (e: any) {
      setError(e.response?.data?.detail ?? "Check-in failed.");
    } finally {
      setCheckingIn(false);
    }
  };

  // ── slot grid colour ──────────────────────────────────────────────────────
  const slotClass = (s: SlotResponse) => {
    if (!s.available)
      return "border-gray-200 bg-gray-100 text-gray-400 cursor-not-allowed";
    if (selectedSlot?.id === s.id)
      return "border-brand-600 bg-brand-50 text-brand-800 ring-2 ring-brand-400";
    return "border-gray-300 bg-white text-gray-700 hover:border-brand-400 hover:bg-brand-50 cursor-pointer";
  };

  // ── render ────────────────────────────────────────────────────────────────
  if (loadingLocs) {
    return (
      <div className="max-w-lg space-y-4">
        <h1>Book an Appointment</h1>
        <p className="text-sm text-gray-500 animate-pulse">Loading locations…</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl space-y-6">
      <h1>Book an Appointment</h1>

      {/* disclaimer */}
      <div className="card bg-yellow-50 border-yellow-200 text-xs text-yellow-800">
        <strong>Demo only.</strong> These are prototype appointments, not official SCDMV
        bookings. They do not guarantee immediate service at the appointment time.
      </div>

      {/* feedback banners */}
      {error && (
        <div className="card bg-red-50 border-red-200 text-sm text-red-700" role="alert">
          {error}
        </div>
      )}
      {success && (
        <div className="card bg-green-50 border-green-200 text-sm text-green-700" role="status">
          {success}
        </div>
      )}

      {/* existing appointment card */}
      {loadingExisting ? (
        <p className="text-xs text-gray-400 animate-pulse">Checking existing appointments…</p>
      ) : existing ? (
        <div className="card space-y-3 border-brand-200 bg-brand-50">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <h2 className="text-base text-brand-800">Your Demo Appointment</h2>
            <span className={
              "text-xs rounded-full px-2 py-0.5 font-medium " +
              (existing.status === "confirmed"
                ? "bg-green-100 text-green-700"
                : "bg-blue-100 text-blue-700")
            }>
              {existing.status}
            </span>
          </div>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <dt className="text-gray-500 text-xs">Date</dt>
              <dd className="font-medium">{fmtDate(existing.start_time)}</dd>
            </div>
            <div>
              <dt className="text-gray-500 text-xs">Time</dt>
              <dd className="font-medium">{fmt12(existing.start_time)} ET</dd>
            </div>
            <div>
              <dt className="text-gray-500 text-xs">Confirmation</dt>
              <dd className="font-mono text-brand-700">{existing.confirmation_code}</dd>
            </div>
          </dl>
          <p className="text-xs text-gray-400">{existing.disclaimer}</p>
          <div className="flex gap-3 flex-wrap">
            {existing.status === "booked" && (
              <button
                onClick={handleCheckIn}
                disabled={checkingIn}
                className="btn-primary text-sm"
              >
                {checkingIn ? "Checking in…" : "Check In Now"}
              </button>
            )}
            <button
              onClick={handleCancel}
              disabled={cancelling}
              className="btn-secondary text-sm"
            >
              {cancelling ? "Cancelling…" : "Cancel Appointment"}
            </button>
          </div>
        </div>
      ) : null}

      {/* new booking form — hide if confirmed appt exists */}
      {(!existing || existing.status === "cancelled") && (
        <div className="card space-y-5">
          <h2 className="text-base">New Appointment</h2>

          {/* case picker */}
          <div className="space-y-1">
            <label htmlFor="case-select" className="label">Registration Case</label>
            <select
              id="case-select"
              className="input"
              value={caseId}
              onChange={(e) => { setCaseId(e.target.value); setSuccess(null); }}
            >
              <option value="">— select a case —</option>
              {cases.map((c) => (
                <option key={c.id} value={c.id}>
                  Case {c.id.slice(0, 8)}… · {c.vin ?? "no VIN"} · {c.status}
                </option>
              ))}
            </select>
          </div>

          {/* location picker */}
          <div className="space-y-1">
            <label htmlFor="location-select" className="label">Location</label>
            <select
              id="location-select"
              className="input"
              value={locationId}
              onChange={(e) => setLocationId(e.target.value)}
            >
              {locations.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name} — {l.city}
                  {l.is_demo ? " (Demo)" : ""}
                </option>
              ))}
            </select>
          </div>

          {/* date picker */}
          <div className="space-y-1">
            <label htmlFor="date-pick" className="label">Date</label>
            <input
              id="date-pick"
              type="date"
              className="input"
              value={date}
              min={today()}
              onChange={(e) => setDate(e.target.value)}
            />
          </div>

          {/* slot grid */}
          {loadingSlots ? (
            <p className="text-sm text-gray-400 animate-pulse">Loading slots…</p>
          ) : slots.length === 0 ? (
            <p className="text-sm text-gray-500">
              No slots available for this date. Try a different date or run the seed
              script to generate demo slots.
            </p>
          ) : (
            <div>
              <p className="label mb-2">Available Times</p>
              <div
                className="grid gap-2"
                style={{ gridTemplateColumns: "repeat(auto-fill, minmax(110px, 1fr))" }}
                role="listbox"
                aria-label="Available appointment slots"
              >
                {slots.map((s) => (
                  <button
                    key={s.id}
                    role="option"
                    aria-selected={selectedSlot?.id === s.id}
                    disabled={!s.available}
                    onClick={() => {
                      if (s.available) setSelectedSlot(s);
                    }}
                    className={"rounded border p-2 text-center text-sm font-medium transition " + slotClass(s)}
                  >
                    <span className="block">{fmt12(s.start_time)}</span>
                    {!s.available && (
                      <span className="block text-xs mt-0.5">Full</span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* confirm button */}
          {selectedSlot && !confirming && (
            <button
              className="btn-primary w-full"
              onClick={() => { setConfirming(true); setError(null); }}
            >
              Reserve {fmt12(selectedSlot.start_time)} on {fmtDate(selectedSlot.start_time)}
            </button>
          )}

          {/* confirm dialog */}
          {confirming && selectedSlot && (
            <div
              className="rounded-lg border border-brand-300 bg-brand-50 p-4 space-y-3"
              role="dialog"
              aria-label="Confirm booking"
            >
              <p className="text-sm font-medium text-brand-800">Confirm Demo Appointment</p>
              <p className="text-sm text-gray-600">
                <strong>{fmtDate(selectedSlot.start_time)}</strong> at{" "}
                <strong>{fmt12(selectedSlot.start_time)} ET</strong>
              </p>
              <p className="text-xs text-yellow-700 bg-yellow-50 rounded p-2 border border-yellow-200">
                This is a prototype reservation only. It is not an official SCDMV booking
                and does not guarantee immediate service.
              </p>
              <div className="flex gap-3">
                <button
                  className="btn-primary"
                  onClick={handleBook}
                  disabled={booking}
                >
                  {booking ? "Booking…" : "Confirm Booking"}
                </button>
                <button
                  className="btn-secondary"
                  onClick={() => setConfirming(false)}
                >
                  Go Back
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
