import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getChecklist, getRequirements } from "../api/dmv";
import type { ChecklistItem, RequirementsResponse } from "../types/api";
import { api } from "../api/client";

const STATUS_CONFIG: Record<string, { label: string; cls: string }> = {
  missing: { label: "Missing", cls: "badge-missing" },
  uploaded: { label: "Uploaded — pending review", cls: "badge-uploaded" },
  reviewed: { label: "Reviewed by demo staff", cls: "badge-reviewed" },
  needs_replacement: { label: "Needs replacement", cls: "badge-needs-replacement" },
  waived: { label: "Waived", cls: "badge-reviewed" },
};

interface LookupResult {
  status: string;
  simulated: boolean;
  disclaimer: string;
  owner_name?: string;
  amount_cents?: number;
  tax_year?: number;
  provider?: string;
}

export default function ChecklistPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [items, setItems] = useState<ChecklistItem[]>([]);
  const [requirements, setRequirements] = useState<RequirementsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [vin, setVin] = useState("");
  const [taxResult, setTaxResult] = useState<LookupResult | null>(null);
  const [ownerResult, setOwnerResult] = useState<LookupResult | null>(null);
  const [lookingUp, setLookingUp] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);

  useEffect(() => {
    if (!caseId) return;
    Promise.all([
      getChecklist(caseId),
      getRequirements(),
    ])
      .then(([cl, req]) => { setItems(cl); setRequirements(req); })
      .catch((e) => setError(e.response?.data?.detail ?? "Failed to load checklist."))
      .finally(() => setLoading(false));
  }, [caseId]);

  const runLookups = async () => {
    if (!vin.trim()) { setLookupError("Enter a VIN to look up."); return; }
    setLookingUp(true);
    setLookupError(null);
    setTaxResult(null);
    setOwnerResult(null);
    try {
      const [taxR, ownerR] = await Promise.all([
        api.get(`/api/lookup/tax/${vin.trim().toUpperCase()}`),
        api.get(`/api/lookup/ownership/${vin.trim().toUpperCase()}`),
      ]);
      setTaxResult(taxR.data);
      setOwnerResult(ownerR.data);
    } catch (e: any) {
      setLookupError(e.response?.data?.detail ?? "Lookup failed.");
    } finally {
      setLookingUp(false);
    }
  };

  const taxStatusColor: Record<string, string> = {
    paid: "text-green-700 bg-green-50 border-green-200",
    unpaid: "text-red-700 bg-red-50 border-red-200",
    not_found: "text-gray-700 bg-gray-50 border-gray-200",
    provider_unavailable: "text-amber-700 bg-amber-50 border-amber-200",
  };

  const ownerStatusColor: Record<string, string> = {
    match: "text-green-700 bg-green-50 border-green-200",
    no_match: "text-red-700 bg-red-50 border-red-200",
    not_found: "text-gray-700 bg-gray-50 border-gray-200",
    provider_unavailable: "text-amber-700 bg-amber-50 border-amber-200",
  };

  if (loading) return <p className="text-gray-500 animate-pulse">Loading checklist\u2026</p>;
  if (error) return <p className="text-red-600" role="alert">{error}</p>;

  const required = items.filter((i) => !i.is_conditional);
  const conditional = items.filter((i) => i.is_conditional);
  const complete = items.filter((i) => i.status === "reviewed").length;
  const total = items.length;

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1>Registration Checklist</h1>
          <p className="text-sm text-gray-500 mt-1">
            Case {caseId?.slice(0, 8)}\u2026 &middot; Private-Party Purchase &middot; York County, SC
          </p>
        </div>
        <div className="text-right">
          <span className="text-2xl font-bold text-brand-700">{complete}</span>
          <span className="text-gray-400 text-sm">/{total} reviewed</span>
        </div>
      </div>

      {/* Quick actions */}
      <div className="flex flex-wrap gap-3">
        <Link to={`/cases/${caseId}/form`} className="btn-primary text-sm">
          ✍️ Fill Out Form
        </Link>
        <Link to={`/cases/${caseId}/documents`} className="btn-secondary text-sm">
          📎 Upload Documents
        </Link>
      </div>

      {/* Steps from requirements config */}
      {requirements?.steps && (
        <details className="card">
          <summary className="cursor-pointer font-medium text-sm text-brand-700">
            Preparation Steps ({requirements.steps.length})
          </summary>
          <ol className="mt-3 space-y-2">
            {requirements.steps.map((s) => (
              <li key={s.key} className="flex gap-3 text-sm">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-brand-100 text-brand-700 font-bold flex items-center justify-center text-xs">
                  {s.order}
                </span>
                <div>
                  <p className="font-medium">{s.label}</p>
                  <p className="text-gray-500 text-xs mt-0.5">{s.detail}</p>
                </div>
              </li>
            ))}
          </ol>
        </details>
      )}

      {/* Required documents */}
      <section aria-labelledby="required-heading">
        <h2 id="required-heading" className="mb-3">Required Documents</h2>
        <ul className="space-y-3">
          {required.map((item) => {
            const conf = STATUS_CONFIG[item.status] ?? STATUS_CONFIG.missing;
            return (
              <li key={item.id} className="card">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-medium text-sm">{item.label}</p>
                    {item.description && (
                      <p className="text-xs text-gray-500 mt-1 leading-relaxed">{item.description}</p>
                    )}
                  </div>
                  <span className={conf.cls + " flex-shrink-0"}>{conf.label}</span>
                </div>
              </li>
            );
          })}
        </ul>
      </section>

      {conditional.length > 0 && (
        <section aria-labelledby="conditional-heading">
          <h2 id="conditional-heading" className="mb-3">Conditional Documents</h2>
          <ul className="space-y-3">
            {conditional.map((item) => {
              const conf = STATUS_CONFIG[item.status] ?? STATUS_CONFIG.missing;
              return (
                <li key={item.id} className="card border-dashed">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-medium text-sm">{item.label}</p>
                      {item.condition_note && (
                        <p className="text-xs text-amber-700 mt-1 font-medium">
                          \u2139\uFE0F {item.condition_note}
                        </p>
                      )}
                      {item.description && (
                        <p className="text-xs text-gray-500 mt-1">{item.description}</p>
                      )}
                    </div>
                    <span className={conf.cls + " flex-shrink-0"}>{conf.label}</span>
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {/* Tax & Ownership Lookup */}
      <section className="card space-y-4" aria-labelledby="lookup-heading">
        <h2 id="lookup-heading" className="text-base">Simulated Tax & Ownership Lookup</h2>
        <p className="text-xs text-gray-500">
          Enter the vehicle VIN to run simulated lookups.
          Results are demo data — not real government records.
        </p>
        <div className="flex gap-2">
          <input
            className="input flex-1"
            placeholder="VIN (e.g. 1HGCM82633A004352)"
            value={vin}
            onChange={(e) => setVin(e.target.value.toUpperCase())}
            maxLength={17}
          />
          <button onClick={runLookups} disabled={lookingUp} className="btn-primary text-sm flex-shrink-0">
            {lookingUp ? "Looking up\u2026" : "Look Up"}
          </button>
        </div>
        {lookupError && <p className="text-red-600 text-xs" role="alert">{lookupError}</p>}

        {taxResult && (
          <div className={"rounded-md border p-3 text-sm " + (taxStatusColor[taxResult.status] ?? "")}>
            <p className="font-semibold capitalize">Tax Status: {taxResult.status.replace("_", " ")}</p>
            {taxResult.amount_cents != null && (
              <p>Amount: ${(taxResult.amount_cents / 100).toFixed(2)} (York County, {taxResult.tax_year})</p>
            )}
            <p className="text-xs mt-1 opacity-75">{taxResult.disclaimer}</p>
          </div>
        )}
        {ownerResult && (
          <div className={"rounded-md border p-3 text-sm " + (ownerStatusColor[ownerResult.status] ?? "")}>
            <p className="font-semibold capitalize">Ownership Status: {ownerResult.status.replace("_", " ")}</p>
            {ownerResult.owner_name && <p>Recorded Owner: {ownerResult.owner_name}</p>}
            <p className="text-xs mt-1 opacity-75">{ownerResult.disclaimer}</p>
          </div>
        )}
      </section>

      {/* Official links */}
      {requirements?.official_links && (
        <div className="card bg-gray-50">
          <h3 className="text-sm font-medium mb-2">Official Resources</h3>
          <ul className="space-y-1">
            {requirements.official_links.map((l) => (
              <li key={l.url}>
                <a
                  href={l.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-brand-600 hover:underline"
                >
                  {l.label} &rarr;
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="card bg-yellow-50 border-yellow-200 text-xs text-yellow-800">
        Requirements are based on provisional research. Verify at{" "}
        <a href="https://www.scdmvonline.com" className="underline" target="_blank" rel="noopener noreferrer">
          scdmvonline.com
        </a>{" "}
        before your visit.
      </div>
    </div>
  );
}
