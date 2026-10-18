import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { getDraft, saveDraft, downloadPdf } from "../api/dmv";
import type { Form400Draft } from "../types/api";

const vehicleSchema = z.object({
  vin: z.string().min(1, "Required").max(17),
  year: z.number({ invalid_type_error: "Enter a year" }).int().min(1900).max(2100),
  make: z.string().min(1, "Required").max(50),
  model: z.string().min(1, "Required").max(50),
  body_style: z.string().max(30).optional(),
  color: z.string().max(30).optional(),
  odometer_reading: z.number({ invalid_type_error: "Numbers only" }).int().min(0).optional(),
  has_lien: z.boolean(),
});

const buyerSchema = z.object({
  full_name: z.string().min(2, "Required").max(100),
  address_line1: z.string().min(5, "Required").max(100),
  address_line2: z.string().max(100).optional(),
  city: z.string().min(1, "Required").max(60),
  state: z.string().length(2, "2-letter state code").default("SC"),
  zip_code: z.string().min(5, "Required").max(10),
  phone: z.string().max(20).optional(),
  sc_county: z.string().max(50).optional(),
});

const sellerSchema = z.object({
  full_name: z.string().min(2, "Required").max(100),
  address_line1: z.string().min(5, "Required").max(100),
  address_line2: z.string().max(100).optional(),
  city: z.string().min(1, "Required").max(60),
  state: z.string().length(2, "2-letter state code").default("SC"),
  zip_code: z.string().min(5, "Required").max(10),
});

const purchaseSchema = z.object({
  purchase_price_dollars: z.number({ invalid_type_error: "Enter a price" }).min(0),
  purchase_date: z.string().min(1, "Required"),
});

const fullSchema = z.object({
  vehicle: vehicleSchema,
  buyer: buyerSchema,
  seller: sellerSchema,
  purchase: purchaseSchema,
  additional_notes: z.string().max(1000).optional(),
});

type FormData = z.infer<typeof fullSchema>;

type ActiveSection = "vehicle" | "buyer" | "seller" | "purchase" | "review";

const SECTIONS: { key: ActiveSection; label: string }[] = [
  { key: "vehicle", label: "Vehicle" },
  { key: "buyer", label: "Buyer" },
  { key: "seller", label: "Seller" },
  { key: "purchase", label: "Purchase" },
  { key: "review", label: "Review" },
];

function Field({ label, error, children }: {
  label: string; error?: string; children: React.ReactNode
}) {
  return (
    <div>
      <label className="label">{label}</label>
      {children}
      {error && <p className="text-red-600 text-xs mt-1" role="alert">{error}</p>}
    </div>
  );
}

export default function FormPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [section, setSection] = useState<ActiveSection>("vehicle");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<any>(null);

  const {
    register,
    handleSubmit,
    reset,
    getValues,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(fullSchema),
    defaultValues: {
      vehicle: { has_lien: false },
      buyer: { state: "SC" },
      seller: { state: "SC" },
    },
  });

  useEffect(() => {
    if (!caseId) return;
    getDraft(caseId)
      .then((d) => {
        setMetadata(d.metadata);
        if (d.data && Object.keys(d.data).length > 0) {
          reset(d.data as FormData);
        }
      })
      .catch(() => setError("Failed to load draft."))
      .finally(() => setLoading(false));
  }, [caseId, reset]);

  const handleSave = useCallback(async (isComplete = false) => {
    if (!caseId) return;
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const data = getValues();
      await saveDraft(caseId, data, isComplete);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e: any) {
      setError(e.response?.data?.detail ?? "Failed to save draft.");
    } finally {
      setSaving(false);
    }
  }, [caseId, getValues]);

  const handleDownload = async () => {
    if (!caseId) return;
    await handleSave(false);
    setDownloading(true);
    try {
      const blob = await downloadPdf(caseId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `dmv-prep-summary-${caseId.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Failed to generate PDF.");
    } finally {
      setDownloading(false);
    }
  };

  if (loading) return <p className="text-gray-500 animate-pulse">Loading form\u2026</p>;

  const currentValues = getValues();

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1>Registration Preparation Form</h1>
          <p className="text-sm text-gray-500 mt-1">
            Case {caseId?.slice(0, 8)}\u2026 &middot; SCDMV Form 400 (demo draft)
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleSave(false)}
            disabled={saving}
            className="btn-secondary text-sm"
          >
            {saving ? "Saving\u2026" : saved ? "\u2713 Saved" : "Save Draft"}
          </button>
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="btn-primary text-sm"
          >
            {downloading ? "Generating\u2026" : "\u2193 Download PDF"}
          </button>
        </div>
      </div>

      {metadata && (
        <div className="card bg-yellow-50 border-yellow-200 text-xs text-yellow-800">
          {metadata.disclaimer}
        </div>
      )}
      {error && (
        <div role="alert" className="card bg-red-50 border-red-200 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Section tabs */}
      <nav aria-label="Form sections">
        <ol className="flex gap-1 flex-wrap">
          {SECTIONS.map((s, i) => (
            <li key={s.key}>
              <button
                type="button"
                onClick={() => setSection(s.key)}
                className={[
                  "px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                  section === s.key
                    ? "bg-brand-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200",
                ].join(" ")}
                aria-current={section === s.key ? "step" : undefined}
              >
                {i + 1}. {s.label}
              </button>
            </li>
          ))}
        </ol>
      </nav>

      <form onSubmit={handleSubmit((data) => saveDraft(caseId!, data, true))} noValidate>
        {/* ---------------------------------------------------------------- */}
        {section === "vehicle" && (
          <div className="card space-y-4">
            <h2>Vehicle Information</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="sm:col-span-2">
                <Field label="VIN *" error={errors.vehicle?.vin?.message}>
                  <input className="input uppercase" maxLength={17} {...register("vehicle.vin")} />
                </Field>
              </div>
              <Field label="Year *" error={errors.vehicle?.year?.message}>
                <input className="input" type="number" {...register("vehicle.year", { valueAsNumber: true })} />
              </Field>
              <Field label="Make *" error={errors.vehicle?.make?.message}>
                <input className="input" {...register("vehicle.make")} />
              </Field>
              <div className="sm:col-span-2">
                <Field label="Model *" error={errors.vehicle?.model?.message}>
                  <input className="input" {...register("vehicle.model")} />
                </Field>
              </div>
              <Field label="Body Style" error={errors.vehicle?.body_style?.message}>
                <input className="input" placeholder="e.g. Sedan" {...register("vehicle.body_style")} />
              </Field>
              <Field label="Color" error={errors.vehicle?.color?.message}>
                <input className="input" placeholder="e.g. Silver" {...register("vehicle.color")} />
              </Field>
              <Field label="Odometer Reading (miles)" error={errors.vehicle?.odometer_reading?.message}>
                <input className="input" type="number" {...register("vehicle.odometer_reading", { valueAsNumber: true })} />
              </Field>
              <div className="flex items-center gap-3 pt-5">
                <input type="checkbox" id="has_lien" className="w-4 h-4 accent-brand-600" {...register("vehicle.has_lien")} />
                <label htmlFor="has_lien" className="text-sm text-gray-700">Title has active lien</label>
              </div>
            </div>
          </div>
        )}

        {/* ---------------------------------------------------------------- */}
        {section === "buyer" && (
          <div className="card space-y-4">
            <h2>Buyer / Applicant Information</h2>
            <p className="text-xs text-gray-500">
              Note: We do not collect Social Security numbers or driver's license numbers in this demo.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="sm:col-span-2">
                <Field label="Full Name *" error={errors.buyer?.full_name?.message}>
                  <input className="input" {...register("buyer.full_name")} />
                </Field>
              </div>
              <div className="sm:col-span-2">
                <Field label="Address Line 1 *" error={errors.buyer?.address_line1?.message}>
                  <input className="input" {...register("buyer.address_line1")} />
                </Field>
              </div>
              <div className="sm:col-span-2">
                <Field label="Address Line 2" error={errors.buyer?.address_line2?.message}>
                  <input className="input" {...register("buyer.address_line2")} />
                </Field>
              </div>
              <Field label="City *" error={errors.buyer?.city?.message}>
                <input className="input" {...register("buyer.city")} />
              </Field>
              <Field label="State *" error={errors.buyer?.state?.message}>
                <input className="input" maxLength={2} defaultValue="SC" {...register("buyer.state")} />
              </Field>
              <Field label="ZIP Code *" error={errors.buyer?.zip_code?.message}>
                <input className="input" maxLength={10} {...register("buyer.zip_code")} />
              </Field>
              <Field label="Phone" error={errors.buyer?.phone?.message}>
                <input className="input" type="tel" {...register("buyer.phone")} />
              </Field>
              <div className="sm:col-span-2">
                <Field label="SC County of Residence" error={errors.buyer?.sc_county?.message}>
                  <input className="input" defaultValue="York" {...register("buyer.sc_county")} />
                </Field>
              </div>
            </div>
          </div>
        )}

        {/* ---------------------------------------------------------------- */}
        {section === "seller" && (
          <div className="card space-y-4">
            <h2>Seller Information</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="sm:col-span-2">
                <Field label="Full Name *" error={errors.seller?.full_name?.message}>
                  <input className="input" {...register("seller.full_name")} />
                </Field>
              </div>
              <div className="sm:col-span-2">
                <Field label="Address Line 1 *" error={errors.seller?.address_line1?.message}>
                  <input className="input" {...register("seller.address_line1")} />
                </Field>
              </div>
              <div className="sm:col-span-2">
                <Field label="Address Line 2" error={errors.seller?.address_line2?.message}>
                  <input className="input" {...register("seller.address_line2")} />
                </Field>
              </div>
              <Field label="City *" error={errors.seller?.city?.message}>
                <input className="input" {...register("seller.city")} />
              </Field>
              <Field label="State *" error={errors.seller?.state?.message}>
                <input className="input" maxLength={2} defaultValue="SC" {...register("seller.state")} />
              </Field>
              <Field label="ZIP Code *" error={errors.seller?.zip_code?.message}>
                <input className="input" maxLength={10} {...register("seller.zip_code")} />
              </Field>
            </div>
          </div>
        )}

        {/* ---------------------------------------------------------------- */}
        {section === "purchase" && (
          <div className="card space-y-4">
            <h2>Purchase Details</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Purchase Price (USD) *" error={errors.purchase?.purchase_price_dollars?.message}>
                <input
                  className="input"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0.00"
                  {...register("purchase.purchase_price_dollars", { valueAsNumber: true })}
                />
              </Field>
              <Field label="Date of Sale *" error={errors.purchase?.purchase_date?.message}>
                <input className="input" type="date" {...register("purchase.purchase_date")} />
              </Field>
            </div>
            <Field label="Additional Notes" error={errors.additional_notes?.message}>
              <textarea
                className="input h-24 resize-none"
                maxLength={1000}
                placeholder="Any additional information for your visit\u2026"
                {...register("additional_notes")}
              />
            </Field>
          </div>
        )}

        {/* ---------------------------------------------------------------- */}
        {section === "review" && (
          <div className="card space-y-4">
            <h2>Review Your Draft</h2>
            <div className="space-y-3 text-sm">
              {[
                { label: "Vehicle", data: currentValues.vehicle },
                { label: "Buyer", data: currentValues.buyer },
                { label: "Seller", data: currentValues.seller },
                { label: "Purchase", data: currentValues.purchase },
              ].map(({ label, data }) => (
                <div key={label}>
                  <h3 className="text-xs uppercase tracking-wide text-gray-400 mb-1">{label}</h3>
                  {data && Object.keys(data).length > 0 ? (
                    <dl className="grid grid-cols-2 gap-x-4 gap-y-1">
                      {Object.entries(data)
                        .filter(([, v]) => v !== undefined && v !== "" && v !== null)
                        .map(([k, v]) => (
                          <div key={k}>
                            <dt className="text-gray-500 capitalize">{k.replace(/_/g, " ")}</dt>
                            <dd className="font-medium">{String(v)}</dd>
                          </div>
                        ))}
                    </dl>
                  ) : (
                    <p className="text-gray-400 italic">Not yet filled in.</p>
                  )}
                </div>
              ))}
            </div>

            <div className="flex gap-3 pt-2 flex-wrap">
              <button
                type="button"
                onClick={() => handleSave(true)}
                disabled={saving}
                className="btn-primary"
              >
                {saving ? "Saving\u2026" : "Mark Complete & Save"}
              </button>
              <button
                type="button"
                onClick={handleDownload}
                disabled={downloading}
                className="btn-secondary"
              >
                {downloading ? "Generating\u2026" : "\u2193 Download PDF Summary"}
              </button>
            </div>

            <div className="card bg-yellow-50 border-yellow-200 text-xs text-yellow-800">
              This PDF summary is a preparation aid — <strong>not an officially accepted SCDMV document</strong>.
              You must complete and sign the actual Form 400 at the DMV office.
            </div>
          </div>
        )}
      </form>

      {/* Section navigation */}
      <div className="flex justify-between">
        {section !== "vehicle" && (
          <button
            type="button"
            onClick={() => {
              const idx = SECTIONS.findIndex((s) => s.key === section);
              if (idx > 0) setSection(SECTIONS[idx - 1].key);
            }}
            className="btn-secondary text-sm"
          >
            &larr; Previous
          </button>
        )}
        <div className="flex-1" />
        {section !== "review" && (
          <button
            type="button"
            onClick={async () => {
              await handleSave(false);
              const idx = SECTIONS.findIndex((s) => s.key === section);
              if (idx < SECTIONS.length - 1) setSection(SECTIONS[idx + 1].key);
            }}
            disabled={saving}
            className="btn-primary text-sm"
          >
            Save & Continue &rarr;
          </button>
        )}
      </div>
    </div>
  );
}
