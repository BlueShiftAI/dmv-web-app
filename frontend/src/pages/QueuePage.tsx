import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { listLocations, getQueueStatus } from "../api/dmv";
import type { LocationResponse, QueueStatusResponse } from "../types/api";

const POLL_INTERVAL_MS = 8_000;
const SSE_RECONNECT_DELAY_MS = 3_000;

// ── status badge ────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<
  string,
  { label: string; bg: string; text: string; border: string }
> = {
  empty:  { label: "Empty",  bg: "bg-gray-100",   text: "text-gray-600",   border: "border-gray-200" },
  quiet:  { label: "Quiet",  bg: "bg-green-100",  text: "text-green-700",  border: "border-green-200" },
  active: { label: "Active", bg: "bg-blue-100",   text: "text-blue-700",   border: "border-blue-200" },
  busy:   { label: "Busy",   bg: "bg-orange-100", text: "text-orange-700", border: "border-orange-200" },
};

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.active;
  return (
    <span className={`rounded-full px-3 py-1 text-sm font-semibold ${cfg.bg} ${cfg.text}`}>
      {cfg.label}
    </span>
  );
}

// ── wait bar ─────────────────────────────────────────────────────────────────

function WaitBar({ minutes, max = 60 }: { minutes: number; max?: number }) {
  const pct = Math.min(100, (minutes / max) * 100);
  const color =
    pct < 34 ? "bg-green-500" : pct < 67 ? "bg-yellow-400" : "bg-red-500";
  return (
    <div className="h-2 w-full rounded-full bg-gray-200 overflow-hidden" aria-hidden>
      <div
        className={"h-full rounded-full transition-all duration-700 " + color}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

// ── component ─────────────────────────────────────────────────────────────────

export default function QueuePage() {
  const [locations, setLocations] = useState<LocationResponse[]>([]);
  const [locationId, setLocationId] = useState("");
  const [status, setStatus] = useState<QueueStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingLocs, setLoadingLocs] = useState(true);
  const [liveMode, setLiveMode] = useState<"sse" | "poll" | "none">("none");
  const [lastFetched, setLastFetched] = useState<Date | null>(null);

  const esRef = useRef<EventSource | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // load locations
  useEffect(() => {
    listLocations()
      .then((locs) => {
        setLocations(locs);
        if (locs.length > 0) setLocationId(locs[0].id);
      })
      .catch(() => setError("Could not load locations."))
      .finally(() => setLoadingLocs(false));
  }, []);

  // connect / reconnect when locationId changes
  useEffect(() => {
    if (!locationId) return;
    cleanup();
    connectSSE(locationId);
    return () => cleanup();
  }, [locationId]);

  function cleanup() {
    if (esRef.current) { esRef.current.close(); esRef.current = null; }
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    setLiveMode("none");
  }

  function connectSSE(lid: string) {
    // EventSource can't send Authorization headers — pass token via query param
    // (backend accepts token query param in addition to Authorization header)
    const token = localStorage.getItem("dmv-auth")
      ? JSON.parse(localStorage.getItem("dmv-auth")!).state?.token ?? ""
      : "";

    try {
      const url = token
        ? `/api/queue/${lid}/stream?token=${encodeURIComponent(token)}`
        : `/api/queue/${lid}/stream`;

      const es = new EventSource(url);
      esRef.current = es;

      es.onopen = () => {
        setLiveMode("sse");
        setError(null);
      };

      es.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data) as QueueStatusResponse;
          if (data.error) throw new Error(data.error as unknown as string);
          setStatus(data);
          setLastFetched(new Date());
          setError(null);
        } catch {
          // ignore parse errors; fall through to polling
        }
      };

      es.onerror = () => {
        es.close();
        esRef.current = null;
        // SSE not available (no token in URL, CORS, proxy issue) → fall back
        fallbackPoll(lid);
      };
    } catch {
      fallbackPoll(lid);
    }
  }

  function fallbackPoll(lid: string) {
    setLiveMode("poll");
    fetchOnce(lid);
    pollRef.current = setInterval(() => fetchOnce(lid), POLL_INTERVAL_MS);
  }

  async function fetchOnce(lid: string) {
    try {
      const data = await getQueueStatus(lid);
      setStatus(data);
      setLastFetched(new Date());
      setError(null);
    } catch (e: any) {
      setError(e.response?.data?.detail ?? "Could not fetch queue status.");
    }
  }

  // ── render ─────────────────────────────────────────────────────────────────

  const modeBadge =
    liveMode === "sse"
      ? { label: "Live (SSE)", cls: "bg-green-100 text-green-700" }
      : liveMode === "poll"
      ? { label: "Polling", cls: "bg-blue-100 text-blue-700" }
      : { label: "Connecting…", cls: "bg-gray-100 text-gray-500" };

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1>Live Queue Status</h1>
        <span className={"rounded-full px-2 py-0.5 text-xs font-medium " + modeBadge.cls}>
          {modeBadge.label}
        </span>
      </div>

      <p className="text-sm text-gray-500">
        <strong>Simulated live data</strong> — not an official SCDMV queue feed. Updates
        every {liveMode === "sse" ? "5" : "8"} seconds.
      </p>

      {/* location picker */}
      {loadingLocs ? (
        <p className="text-sm text-gray-400 animate-pulse">Loading locations…</p>
      ) : (
        <div className="space-y-1">
          <label htmlFor="q-location" className="label">Location</label>
          <select
            id="q-location"
            className="input max-w-xs"
            value={locationId}
            onChange={(e) => { setLocationId(e.target.value); setStatus(null); }}
          >
            {locations.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name} — {l.city}
              </option>
            ))}
          </select>
        </div>
      )}

      {error && (
        <p className="text-red-600 text-sm" role="alert">{error}</p>
      )}

      {/* queue card */}
      {status ? (
        <div className="card space-y-5">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <h2 className="text-base">Queue Status</h2>
            <StatusBadge status={status.queue_status} />
          </div>

          {/* main metrics */}
          <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            <div className="card bg-gray-50 text-center">
              <dt className="text-xs text-gray-500">Waiting</dt>
              <dd className="text-3xl font-bold text-gray-800">{status.waiting_count}</dd>
            </div>
            <div className="card bg-gray-50 text-center">
              <dt className="text-xs text-gray-500">In Service</dt>
              <dd className="text-3xl font-bold text-brand-700">{status.in_service_count}</dd>
            </div>
            <div className="card bg-gray-50 text-center">
              <dt className="text-xs text-gray-500">Called</dt>
              <dd className="text-3xl font-bold text-yellow-700">{status.called_count}</dd>
            </div>
            <div className="card bg-gray-50 text-center">
              <dt className="text-xs text-gray-500">Est. Wait</dt>
              <dd className="text-3xl font-bold text-gray-800">
                {status.estimated_wait_minutes !== null
                  ? `${status.estimated_wait_minutes}`
                  : "—"}
              </dd>
              {status.estimated_wait_minutes !== null && (
                <dd className="text-xs text-gray-400">min</dd>
              )}
            </div>
          </dl>

          {/* wait bar */}
          {status.estimated_wait_minutes !== null && (
            <div className="space-y-1">
              <WaitBar minutes={status.estimated_wait_minutes} />
              <p className="text-xs text-gray-400">
                Based on {status.sample_size} recent service record
                {status.sample_size !== 1 ? "s" : ""} · method: {status.method}
              </p>
            </div>
          )}

          {/* p50/p90 */}
          {(status.p50_service_minutes || status.p90_service_minutes) && (
            <div className="grid grid-cols-2 gap-3 text-xs">
              {status.p50_service_minutes !== null && (
                <div className="card bg-gray-50">
                  <p className="text-gray-500">Median service time</p>
                  <p className="font-semibold">{status.p50_service_minutes.toFixed(1)} min</p>
                </div>
              )}
              {status.p90_service_minutes !== null && (
                <div className="card bg-gray-50">
                  <p className="text-gray-500">90th-pct service time</p>
                  <p className="font-semibold">{status.p90_service_minutes.toFixed(1)} min</p>
                </div>
              )}
            </div>
          )}

          <div className="flex items-center justify-between text-xs text-gray-400 flex-wrap gap-2">
            <span>
              Last updated:{" "}
              {lastFetched ? lastFetched.toLocaleTimeString() : "—"}
            </span>
            <span className="italic">{status.disclaimer}</span>
          </div>
        </div>
      ) : !error && locationId ? (
        <div className="card text-center py-10 text-gray-400 animate-pulse text-sm">
          Connecting to queue…
        </div>
      ) : null}

      {/* empty state guidance */}
      {status?.queue_status === "empty" && (
        <div className="card bg-green-50 border-green-200 text-sm text-green-700">
          The queue is currently empty. Walk-in check-in or an appointment is available.
        </div>
      )}

      {/* navigation */}
      <div className="flex gap-3 flex-wrap">
        <Link to="/booking" className="btn-secondary text-sm">
          📅 Book Appointment
        </Link>
        <Link to="/dashboard" className="btn-secondary text-sm">
          ← My Cases
        </Link>
      </div>
    </div>
  );
}
