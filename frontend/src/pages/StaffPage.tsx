import { useEffect, useRef, useState } from "react";
import { listLocations, updateCaseStatus } from "../api/dmv";
import { api } from "../api/client";
import type { CaseResponse, LocationResponse } from "../types/api";

// ── types ──────────────────────────────────────────────────────────────────

interface QueueEntryDetail {
  id: string;
  case_id: string;
  location_id: string;
  status: "waiting" | "called" | "in_service" | "completed" | "no_show";
  position: number | null;
  is_walk_in: boolean;
  checked_in_at: string | null;
  called_at: string | null;
  service_started_at: string | null;
  service_completed_at: string | null;
  flagged: boolean;
  wait_minutes: number | null;
  service_minutes: number | null;
}

interface AppointmentItem {
  id: string;
  case_id: string;
  confirmation_code: string;
  status: string;
  start_time: string;
  is_checked_in: boolean;
}

interface HourBucket {
  hour: number;
  completed: number;
  avg_service_minutes: number | null;
}

interface MetricsData {
  location_id: string;
  period_hours: number;
  total_completed: number;
  total_no_shows: number;
  total_doc_delays: number;
  median_wait_minutes: number | null;
  p90_wait_minutes: number | null;
  median_service_minutes: number | null;
  p90_service_minutes: number | null;
  completions_by_hour: HourBucket[];
  disclaimer: string;
}

// ── helpers ────────────────────────────────────────────────────────────────

function fmtTime(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString("en-US", {
    hour: "numeric", minute: "2-digit", timeZone: "America/New_York",
  });
}

function fmtMins(v: number | null) {
  if (v === null) return "—";
  return `${v.toFixed(1)} min`;
}

const STATUS_CHIP: Record<string, string> = {
  waiting:    "bg-gray-100 text-gray-700",
  called:     "bg-yellow-100 text-yellow-800",
  in_service: "bg-blue-100 text-blue-800",
  completed:  "bg-green-100 text-green-700",
  no_show:    "bg-red-100 text-red-700",
};

// ── mini bar chart for completions by hour ─────────────────────────────────

function HourChart({ data }: { data: HourBucket[] }) {
  if (data.length === 0) return <p className="text-xs text-gray-400">No completion data yet.</p>;
  const maxVal = Math.max(...data.map((d) => d.completed), 1);
  return (
    <div className="space-y-1">
      <p className="text-xs text-gray-500 mb-2">Completions by hour of day</p>
      <div className="flex items-end gap-1 h-16">
        {data.map((d) => {
          const pct = (d.completed / maxVal) * 100;
          return (
            <div key={d.hour} className="flex flex-col items-center gap-0.5 flex-1 min-w-0">
              <div
                className="w-full bg-brand-500 rounded-t"
                style={{ height: `${Math.max(pct, 4)}%` }}
                title={`${d.completed} completed (avg ${d.avg_service_minutes?.toFixed(1) ?? "—"} min)`}
              />
              <span className="text-[10px] text-gray-400 leading-none">{d.hour}</span>
            </div>
          );
        })}
      </div>
      <p className="text-xs text-gray-400 italic">x-axis = hour (0–23 UTC)</p>
    </div>
  );
}

// ── component ──────────────────────────────────────────────────────────────

type Tab = "queue" | "appointments" | "cases" | "metrics";

const CASE_STATUS_CHIP: Record<string, string> = {
  draft:     "bg-gray-100 text-gray-600",
  submitted: "bg-blue-100 text-blue-700",
  in_review: "bg-yellow-100 text-yellow-800",
  approved:  "bg-green-100 text-green-700",
  rejected:  "bg-red-100 text-red-700",
  completed: "bg-purple-100 text-purple-700",
};

export default function StaffPage() {
  const [locations, setLocations] = useState<LocationResponse[]>([]);
  const [locationId, setLocationId] = useState("");
  const [tab, setTab] = useState<Tab>("queue");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  // queue tab
  const [entries, setEntries] = useState<QueueEntryDetail[]>([]);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // appointments tab
  const [appointments, setAppointments] = useState<AppointmentItem[]>([]);

  // cases tab
  const [pendingCases, setPendingCases] = useState<CaseResponse[]>([]);
  const [caseActionLoading, setCaseActionLoading] = useState<string | null>(null);
  const [staffNotesInput, setStaffNotesInput] = useState<Record<string, string>>({});

  // metrics tab
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [metricHours, setMetricHours] = useState(24);

  // ── load locations ──────────────────────────────────────────────────────
  useEffect(() => {
    listLocations()
      .then((locs) => {
        setLocations(locs);
        if (locs.length > 0) setLocationId(locs[0].id);
      })
      .catch(() => setError("Could not load locations."));
  }, []);

  // ── auto-refresh queue every 10s ───────────────────────────────────────
  useEffect(() => {
    if (!locationId) return;
    if (pollRef.current) clearInterval(pollRef.current);
    fetchQueue(locationId);
    pollRef.current = setInterval(() => fetchQueue(locationId), 10_000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [locationId]);

  // ── fetch on tab switch ─────────────────────────────────────────────────
  useEffect(() => {
    if (!locationId) return;
    if (tab === "appointments") fetchAppointments(locationId);
    if (tab === "cases") fetchPendingCases();
    if (tab === "metrics") fetchMetrics(locationId, metricHours);
  }, [tab, locationId]);

  // ── data fetchers ───────────────────────────────────────────────────────
  const fetchQueue = async (lid: string) => {
    try {
      const r = await api.get<QueueEntryDetail[]>(`/api/staff/queue/${lid}`);
      setEntries(r.data);
      setError(null);
    } catch (e: any) {
      setError(e.response?.data?.detail ?? "Failed to load queue.");
    }
  };

  const fetchAppointments = async (lid: string) => {
    setLoading(true);
    try {
      const r = await api.get<AppointmentItem[]>(`/api/staff/appointments/${lid}`);
      setAppointments(r.data);
      setError(null);
    } catch (e: any) {
      setError(e.response?.data?.detail ?? "Failed to load appointments.");
    } finally {
      setLoading(false);
    }
  };

  const fetchMetrics = async (lid: string, hours: number) => {
    setLoading(true);
    try {
      const r = await api.get<MetricsData>(`/api/staff/metrics/${lid}?hours=${hours}`);
      setMetrics(r.data);
      setError(null);
    } catch (e: any) {
      setError(e.response?.data?.detail ?? "Failed to load metrics.");
    } finally {
      setLoading(false);
    }
  };

  // ── cases tab fetcher ───────────────────────────────────────────────────
  const fetchPendingCases = async () => {
    setLoading(true);
    try {
      // Staff can see all cases; filter client-side to submitted/in_review
      const r = await api.get<CaseResponse[]>("/api/cases/pending");
      setPendingCases(r.data);
      setError(null);
    } catch {
      // Endpoint may not exist yet — fall back to empty list gracefully
      setPendingCases([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCaseAction = async (
    caseId: string,
    newStatus: string,
  ) => {
    setCaseActionLoading(caseId);
    const notes = staffNotesInput[caseId] ?? "";
    try {
      const updated = await updateCaseStatus(caseId, newStatus, notes || undefined);
      setPendingCases((prev) =>
        prev
          .map((c) => (c.id === updated.id ? updated : c))
          .filter((c) => ["submitted", "in_review"].includes(c.status))
      );
      setStaffNotesInput((prev) => { const n = { ...prev }; delete n[caseId]; return n; });
      setActionMsg(`Case ${caseId.slice(0, 8)}… → ${newStatus.replace("_", " ")}`);
      setTimeout(() => setActionMsg(null), 3000);
    } catch (e: any) {
      setError(e.response?.data?.detail ?? "Action failed.");
    } finally {
      setCaseActionLoading(null);
    }
  };

  // ── queue actions ───────────────────────────────────────────────────────
  const action = async (entryId: string, verb: string, label: string) => {
    try {
      await api.post(`/api/staff/queue/${entryId}/${verb}`);
      setActionMsg(`${label} successful.`);
      setTimeout(() => setActionMsg(null), 3000);
      fetchQueue(locationId);
    } catch (e: any) {
      setError(e.response?.data?.detail ?? `${label} failed.`);
    }
  };

  // ── render ──────────────────────────────────────────────────────────────
  const tabCls = (t: Tab) =>
    "px-4 py-2 text-sm font-medium border-b-2 transition " +
    (tab === t
      ? "border-brand-600 text-brand-700"
      : "border-transparent text-gray-500 hover:text-gray-700");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1>Staff Dashboard</h1>
        <span className="text-xs bg-yellow-100 text-yellow-800 rounded-full px-2 py-0.5">
          Synthetic demo data — not real SCDMV
        </span>
      </div>

      {/* location picker */}
      <div className="flex items-end gap-3 flex-wrap">
        <div className="space-y-1">
          <label htmlFor="staff-loc" className="label">Location</label>
          <select
            id="staff-loc"
            className="input w-64"
            value={locationId}
            onChange={(e) => setLocationId(e.target.value)}
          >
            {locations.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name} — {l.city}
              </option>
            ))}
          </select>
        </div>
        {tab === "metrics" && (
          <div className="space-y-1">
            <label htmlFor="metric-hours" className="label">Period</label>
            <select
              id="metric-hours"
              className="input"
              value={metricHours}
              onChange={(e) => {
                const h = Number(e.target.value);
                setMetricHours(h);
                if (locationId) fetchMetrics(locationId, h);
              }}
            >
              <option value={8}>Last 8 h</option>
              <option value={24}>Last 24 h</option>
              <option value={48}>Last 48 h</option>
              <option value={168}>Last 7 days</option>
            </select>
          </div>
        )}
      </div>

      {/* tabs */}
      <div className="border-b border-gray-200 flex gap-0">
        <button className={tabCls("queue")} onClick={() => setTab("queue")}>
          🔢 Queue ({entries.length})
        </button>
        <button className={tabCls("appointments")} onClick={() => setTab("appointments")}>
            📅 Appointments
          </button>
          <button className={tabCls("cases")} onClick={() => setTab("cases")}>
            📋 Cases
          </button>
          <button className={tabCls("metrics")} onClick={() => setTab("metrics")}>
            📊 Metrics
          </button>
      </div>

      {/* feedback */}
      {error && <p className="text-red-600 text-sm" role="alert">{error}</p>}
      {actionMsg && <p className="text-green-600 text-sm" role="status">{actionMsg}</p>}

      {/* ── QUEUE TAB ─────────────────────────────────────────────────── */}
      {tab === "queue" && (
        <div>
          {entries.length === 0 ? (
            <p className="text-gray-500 text-sm">No active queue entries for this location.</p>
          ) : (
            <div className="card overflow-x-auto">
              <table className="w-full text-sm" aria-label="Queue entries">
                <thead>
                  <tr className="text-left border-b border-gray-200 text-xs text-gray-500">
                    <th className="pb-2 pr-3 font-medium">Case</th>
                    <th className="pb-2 pr-3 font-medium">Status</th>
                    <th className="pb-2 pr-3 font-medium">Type</th>
                    <th className="pb-2 pr-3 font-medium">Checked In</th>
                    <th className="pb-2 pr-3 font-medium">Wait</th>
                    <th className="pb-2 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map((e) => (
                    <tr
                      key={e.id}
                      className={
                        "border-b border-gray-100 last:border-0 " +
                        (e.flagged ? "bg-red-50" : "")
                      }
                    >
                      <td className="py-2 pr-3 font-mono text-xs">
                        {e.case_id.slice(0, 8)}…
                        {e.flagged && (
                          <span className="ml-1 text-red-600" title="Document issue flagged">🚩</span>
                        )}
                      </td>
                      <td className="py-2 pr-3">
                        <span className={
                          "text-xs rounded-full px-2 py-0.5 font-medium " +
                          (STATUS_CHIP[e.status] ?? "bg-gray-100 text-gray-600")
                        }>
                          {e.status.replace("_", " ")}
                        </span>
                      </td>
                      <td className="py-2 pr-3 text-xs">{e.is_walk_in ? "Walk-in" : "Appt."}</td>
                      <td className="py-2 pr-3 text-xs text-gray-500">
                        {fmtTime(e.checked_in_at)}
                      </td>
                      <td className="py-2 pr-3 text-xs text-gray-500">
                        {fmtMins(e.wait_minutes)}
                      </td>
                      <td className="py-2">
                        <div className="flex gap-1 flex-wrap">
                          {e.status === "waiting" && (
                            <button
                              onClick={() => action(e.id, "call", "Call")}
                              className="btn-primary text-xs"
                            >
                              Call
                            </button>
                          )}
                          {(e.status === "called" || e.status === "waiting") && (
                            <button
                              onClick={() => action(e.id, "start", "Start")}
                              className="btn-secondary text-xs"
                            >
                              Start
                            </button>
                          )}
                          {(e.status === "called" || e.status === "in_service") && (
                            <button
                              onClick={() => action(e.id, "complete", "Complete")}
                              className="btn-primary text-xs"
                            >
                              Complete
                            </button>
                          )}
                          {(e.status === "waiting" || e.status === "called" ||
                            e.status === "in_service") && (
                            <button
                              onClick={() => action(e.id, "flag", "Flag")}
                              className="btn-secondary text-xs"
                              title="Flag document issue"
                            >
                              🚩 Flag
                            </button>
                          )}
                          {(e.status === "waiting" || e.status === "called") && (
                            <button
                              onClick={() => action(e.id, "no_show", "No-show")}
                              className="btn-secondary text-xs"
                              title="Mark no-show"
                            >
                              ✗ No-show
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="text-xs text-gray-400 mt-3">
                Auto-refreshes every 10 s. Simulated demo data.
              </p>
            </div>
          )}
        </div>
      )}

      {/* ── CASES TAB ─────────────────────────────────────────────────── */}
      {tab === "cases" && (
        <div>
          {loading ? (
            <p className="text-gray-400 text-sm animate-pulse">Loading cases…</p>
          ) : pendingCases.length === 0 ? (
            <p className="text-gray-500 text-sm">No submitted or in-review cases.</p>
          ) : (
            <div className="space-y-4">
              {pendingCases.map((c) => (
                <div key={c.id} className="card space-y-3">
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="font-mono text-sm">{c.id.slice(0, 8)}&hellip;</span>
                    <span className={
                      "text-xs rounded-full px-2 py-0.5 font-medium " +
                      (CASE_STATUS_CHIP[c.status] ?? "bg-gray-100 text-gray-600")
                    }>
                      {c.status.replace("_", " ")}
                    </span>
                    {c.vin && (
                      <span className="text-xs text-gray-500">
                        VIN: <span className="font-mono">{c.vin}</span>
                      </span>
                    )}
                  </div>
                  <div>
                    <label className="label text-xs" htmlFor={`notes-${c.id}`}>
                      Staff notes (optional)
                    </label>
                    <input
                      id={`notes-${c.id}`}
                      className="input text-sm mt-1"
                      placeholder="e.g. Missing lien release"
                      value={staffNotesInput[c.id] ?? ""}
                      onChange={(e) =>
                        setStaffNotesInput((prev) => ({ ...prev, [c.id]: e.target.value }))
                      }
                    />
                  </div>
                  <div className="flex gap-2 flex-wrap">
                    {c.status === "submitted" && (
                      <button
                        onClick={() => handleCaseAction(c.id, "in_review")}
                        disabled={caseActionLoading === c.id}
                        className="btn-secondary text-xs"
                      >
                        {caseActionLoading === c.id ? "…" : "🔍 Start Review"}
                      </button>
                    )}
                    {c.status === "in_review" && (
                      <>
                        <button
                          onClick={() => handleCaseAction(c.id, "approved")}
                          disabled={caseActionLoading === c.id}
                          className="btn-primary text-xs"
                        >
                          {caseActionLoading === c.id ? "…" : "✓ Approve"}
                        </button>
                        <button
                          onClick={() => handleCaseAction(c.id, "rejected")}
                          disabled={caseActionLoading === c.id}
                          className="btn-secondary text-xs"
                        >
                          {caseActionLoading === c.id ? "…" : "✗ Return to Customer"}
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))}
              <p className="text-xs text-gray-400 italic">
                Simulated review flow — not an official SCDMV process.
              </p>
            </div>
          )}
        </div>
      )}

      {/* ── APPOINTMENTS TAB ──────────────────────────────────────────── */}
      {tab === "appointments" && (
        <div>
          {loading ? (
            <p className="text-gray-400 text-sm animate-pulse">Loading appointments…</p>
          ) : appointments.length === 0 ? (
            <p className="text-gray-500 text-sm">No appointments scheduled for today at this location.</p>
          ) : (
            <div className="card overflow-x-auto">
              <table className="w-full text-sm" aria-label="Today's appointments">
                <thead>
                  <tr className="text-left border-b border-gray-200 text-xs text-gray-500">
                    <th className="pb-2 pr-3 font-medium">Code</th>
                    <th className="pb-2 pr-3 font-medium">Case</th>
                    <th className="pb-2 pr-3 font-medium">Time</th>
                    <th className="pb-2 pr-3 font-medium">Status</th>
                    <th className="pb-2 font-medium">Checked In</th>
                  </tr>
                </thead>
                <tbody>
                  {appointments.map((a) => (
                    <tr key={a.id} className="border-b border-gray-100 last:border-0">
                      <td className="py-2 pr-3 font-mono text-xs text-brand-700">
                        {a.confirmation_code}
                      </td>
                      <td className="py-2 pr-3 font-mono text-xs">
                        {a.case_id.slice(0, 8)}…
                      </td>
                      <td className="py-2 pr-3 text-xs">{fmtTime(a.start_time)}</td>
                      <td className="py-2 pr-3">
                        <span className="text-xs rounded-full px-2 py-0.5 bg-blue-100 text-blue-700 font-medium">
                          {a.status}
                        </span>
                      </td>
                      <td className="py-2">
                        {a.is_checked_in ? (
                          <span className="text-xs text-green-600 font-medium">✓ In queue</span>
                        ) : (
                          <span className="text-xs text-gray-400">Pending</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── METRICS TAB ───────────────────────────────────────────────── */}
      {tab === "metrics" && (
        <div>
          {loading ? (
            <p className="text-gray-400 text-sm animate-pulse">Loading metrics…</p>
          ) : metrics ? (
            <div className="space-y-5">
              {/* KPI grid */}
              <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {[
                  { label: "Completed", value: metrics.total_completed, color: "text-green-700" },
                  { label: "No-shows", value: metrics.total_no_shows, color: "text-red-600" },
                  { label: "Doc delays", value: metrics.total_doc_delays, color: "text-orange-600" },
                  {
                    label: "Median wait",
                    value: fmtMins(metrics.median_wait_minutes),
                    color: "text-brand-700",
                  },
                ].map((kpi) => (
                  <div key={kpi.label} className="card bg-gray-50 text-center">
                    <dt className="text-xs text-gray-500">{kpi.label}</dt>
                    <dd className={"text-2xl font-bold " + kpi.color}>{kpi.value}</dd>
                  </div>
                ))}
              </dl>

              {/* percentile row */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                {[
                  { label: "P50 wait", v: metrics.median_wait_minutes },
                  { label: "P90 wait", v: metrics.p90_wait_minutes },
                  { label: "P50 service", v: metrics.median_service_minutes },
                  { label: "P90 service", v: metrics.p90_service_minutes },
                ].map((row) => (
                  <div key={row.label} className="card bg-gray-50">
                    <p className="text-gray-500">{row.label}</p>
                    <p className="font-semibold text-sm">{fmtMins(row.v)}</p>
                  </div>
                ))}
              </div>

              {/* bar chart */}
              <div className="card">
                <HourChart data={metrics.completions_by_hour} />
              </div>

              <p className="text-xs text-gray-400 italic">{metrics.disclaimer}</p>
            </div>
          ) : (
            <button
              className="btn-secondary text-sm"
              onClick={() => fetchMetrics(locationId, metricHours)}
            >
              Load Metrics
            </button>
          )}
        </div>
      )}
    </div>
  );
}
