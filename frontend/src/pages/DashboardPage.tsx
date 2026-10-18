import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { listCases, walkInCheckIn, listLocations, submitCase } from "../api/dmv";
import { useAuthStore } from "../features/auth/authStore";
import IntakeWizard from "../features/wizard/IntakeWizard";
import type { CaseResponse, LocationResponse, WalkInResponse } from "../types/api";
import SubmitConfirmModal from "../components/SubmitConfirmModal";

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  submitted: "bg-blue-100 text-blue-700",
  in_review: "bg-yellow-100 text-yellow-700",
  approved: "bg-green-100 text-green-700",
  completed: "bg-purple-100 text-purple-700",
  rejected: "bg-red-100 text-red-700",
};

const STATUS_HINT: Record<string, string> = {
  draft: "Complete your checklist and form, then submit for staff review.",
  submitted: "Awaiting staff review — no action needed.",
  in_review: "A staff member is reviewing your case.",
  approved:
    "Demo approved. Bring your documents to the Rock Hill SCDMV office to complete registration.",
  rejected: "Your case was returned. Check your notifications for staff notes, then resubmit.",
  completed: "Case complete.",
};

export default function DashboardPage() {
  const { fullName } = useAuthStore();
  const navigate = useNavigate();
  const [cases, setCases] = useState<CaseResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showWizard, setShowWizard] = useState(false);
  const [locations, setLocations] = useState<LocationResponse[]>([]);
  const [walkInResult, setWalkInResult] = useState<Record<string, WalkInResponse>>({});
  const [walkInLoading, setWalkInLoading] = useState<string | null>(null);
  const [walkInError, setWalkInError] = useState<string | null>(null);
  const [submitLoading, setSubmitLoading] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [confirmCaseId, setConfirmCaseId] = useState<string | null>(null);

  const fetchCases = () => {
    setLoading(true);
    listCases()
      .then(setCases)
      .catch((e) => setError(e.response?.data?.detail ?? "Failed to load cases."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchCases();
    listLocations().then(setLocations).catch(() => {});
  }, []);

  const handleWalkIn = async (caseId: string) => {
    if (locations.length === 0) {
      setWalkInError("No locations available.");
      return;
    }
    const locationId = locations[0].id;
    setWalkInLoading(caseId);
    setWalkInError(null);
    try {
      const result = await walkInCheckIn(locationId);
      setWalkInResult((prev) => ({ ...prev, [caseId]: result }));
    } catch (e: any) {
      setWalkInError(e.response?.data?.detail ?? "Walk-in check-in failed.");
    } finally {
      setWalkInLoading(null);
    }
  };

  const handleSubmitConfirmed = async () => {
    if (!confirmCaseId) return;
    const caseId = confirmCaseId;
    setConfirmCaseId(null);
    setSubmitLoading(caseId);
    setSubmitError(null);
    try {
      const updated = await submitCase(caseId);
      setCases((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
    } catch (e: any) {
      setSubmitError(e.response?.data?.detail ?? "Submission failed.");
    } finally {
      setSubmitLoading(null);
    }
  };

  const handleWizardComplete = (caseId: string) => {
    setShowWizard(false);
    navigate(`/cases/${caseId}/checklist`);
  };

  if (showWizard) {
    return (
      <div>
        <button
          onClick={() => setShowWizard(false)}
          className="mb-4 text-sm text-brand-600 hover:underline"
        >
          &larr; Back to dashboard
        </button>
        <IntakeWizard onComplete={handleWizardComplete} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1>Welcome, {fullName}</h1>
        <button onClick={() => setShowWizard(true)} className="btn-primary">
          + Start New Case
        </button>
      </div>

      {error && <p className="text-red-600 text-sm" role="alert">{error}</p>}

      {loading ? (
        <p className="text-gray-500 text-sm animate-pulse">Loading your cases\u2026</p>
      ) : cases.length === 0 ? (
        <div className="card text-center py-12 space-y-3">
          <p className="text-gray-500">No registration cases yet.</p>
          <p className="text-sm text-gray-400">
            Click <strong>Start New Case</strong> to begin preparing your
            private-party vehicle registration.
          </p>
          <button onClick={() => setShowWizard(true)} className="btn-primary">
            Start New Case
          </button>
        </div>
      ) : (
        <ul className="space-y-3" aria-label="Your registration cases">
          {cases.map((c) => (
            <li key={c.id} className="card space-y-3">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-medium text-sm">
                      Case <span className="font-mono">{c.id.slice(0, 8)}&hellip;</span>
                    </p>
                    <span
                      className={"text-xs rounded-full px-2 py-0.5 font-medium " +
                        (STATUS_COLORS[c.status] ?? "bg-gray-100 text-gray-700")}
                    >
                      {c.status.replace("_", " ")}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {c.vin ? <>VIN: <span className="font-mono">{c.vin}</span> &middot; </> : ""}
                    {c.created_at
                      ? new Date(c.created_at).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                        })
                      : ""}
                  </p>
                  {STATUS_HINT[c.status] && (
                    <p className="text-xs text-gray-400 mt-1 italic">{STATUS_HINT[c.status]}</p>
                  )}
                </div>
                {/* Submit button — only visible on draft cases */}
                {c.status === "draft" && (
                  <button
                    onClick={() => setConfirmCaseId(c.id)}
                    disabled={submitLoading === c.id}
                    className="btn-primary text-xs flex-shrink-0"
                    title="Submit this case for staff review"
                  >
                    {submitLoading === c.id ? "Submitting…" : "✓ Submit for Review"}
                  </button>
                )}
              </div>

              {/* Outcome banners — approved and rejected only */}
              {c.status === "approved" && (
                <div className="rounded-md border border-green-300 bg-green-50 px-4 py-3 text-sm text-green-800" role="status">
                  <p className="font-semibold">✅ Demo Approved</p>
                  <p className="mt-1">
                    Your preparation has been reviewed and approved in this demo.{" "}
                    <strong>This is not an official SCDMV decision.</strong>{" "}
                    Bring your original documents to the Rock Hill SCDMV office to complete
                    the official title transfer and registration.
                  </p>
                  <p className="mt-1 text-xs text-green-700 italic">
                    Simulated outcome only · Not legally binding · Verify requirements at scdmvonline.com
                  </p>
                </div>
              )}
              {c.status === "rejected" && (
                <div className="rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
                  <p className="font-semibold">↩ Returned — Action Required</p>
                  <p className="mt-1">
                    Your case was returned by demo staff. Check your{" "}
                    <span className="font-medium">notifications</span> for staff notes,
                    correct the issues, and resubmit.
                  </p>
                  <p className="mt-1 text-xs text-red-700 italic">
                    Simulated review outcome · Not an official SCDMV determination
                  </p>
                </div>
              )}

              <div className="flex gap-2 flex-shrink-0 flex-wrap">
                <Link to={`/cases/${c.id}/checklist`} className="btn-secondary text-xs">
                  Checklist
                </Link>
                <Link to={`/cases/${c.id}/form`} className="btn-secondary text-xs">
                  Form
                </Link>
                <Link to={`/cases/${c.id}/documents`} className="btn-secondary text-xs">
                  Docs
                </Link>
                <Link to={`/booking?case_id=${c.id}`} className="btn-secondary text-xs">
                  📅 Book
                </Link>
                {walkInResult[c.id] ? (
                  <Link to="/queue" className="btn-primary text-xs">
                    🔢 Track Queue
                  </Link>
                ) : (
                  <button
                    onClick={() => handleWalkIn(c.id)}
                    disabled={walkInLoading === c.id}
                    className="btn-secondary text-xs"
                    title="Walk-in check-in at the first available location"
                  >
                    {walkInLoading === c.id ? "…" : "🚶 Walk In"}
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {submitError && (
        <p className="text-red-600 text-sm" role="alert">{submitError}</p>
      )}
      {walkInError && (
        <p className="text-red-600 text-sm" role="alert">{walkInError}</p>
      )}

      {/* walk-in result banner */}
      {Object.values(walkInResult).length > 0 && (
        <div className="card bg-green-50 border-green-200 text-sm text-green-700 space-y-1">
          {Object.entries(walkInResult).map(([cid, r]) => (
            <p key={cid}>
              Case <span className="font-mono">{cid.slice(0, 8)}…</span>:
              You are <strong>#{r.position}</strong> in the queue.
              {r.estimated_wait_minutes !== null
                ? ` Est. wait: ${r.estimated_wait_minutes} min.`
                : ""}
              {" "}<Link to="/queue" className="underline text-green-800">Track queue →</Link>
            </p>
          ))}
          <p className="text-xs text-green-600">{Object.values(walkInResult)[0].disclaimer}</p>
        </div>
      )}

      <div className="card bg-gray-50 border-gray-200">
        <h2 className="text-base mb-3">Tools</h2>
        <div className="flex flex-wrap gap-3">
          <Link to="/queue" className="btn-secondary text-sm">📊 Queue Status</Link>
          <Link to="/booking" className="btn-secondary text-sm">📅 Book Appointment</Link>
        </div>
      </div>

      {/* Submit confirmation modal */}
      {confirmCaseId && (
        <SubmitConfirmModal
          caseId={confirmCaseId}
          onConfirm={handleSubmitConfirmed}
          onCancel={() => setConfirmCaseId(null)}
        />
      )}
    </div>
  );
}
