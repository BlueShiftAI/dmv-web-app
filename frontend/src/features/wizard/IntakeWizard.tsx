import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { createCase, saveDraft } from "../../api/dmv";

// ---------------------------------------------------------------------------
// Step definitions
// ---------------------------------------------------------------------------
const STEPS = ["Situation", "Vehicle", "Confirm"] as const;
type Step = (typeof STEPS)[number];

// ---------------------------------------------------------------------------
// Step 1 schema
// ---------------------------------------------------------------------------
const step1Schema = z.object({
  scenario: z.literal("private_party_purchase", {
    errorMap: () => ({ message: "Only private-party purchases are supported in this demo." }),
  }),
});

// ---------------------------------------------------------------------------
// Step 2 schema
// ---------------------------------------------------------------------------
const step2Schema = z.object({
  vin: z
    .string()
    .min(1, "VIN is required")
    .max(17, "VIN must be 17 characters or fewer")
    .regex(/^[A-HJ-NPR-Z0-9]+$/i, "VIN contains invalid characters"),
  year: z
    .number({ invalid_type_error: "Enter a 4-digit year" })
    .int()
    .min(1981, "Year must be 1981 or later")
    .max(new Date().getFullYear() + 1, "Year cannot be in the future"),
  make: z.string().min(1, "Make is required").max(50),
  model: z.string().min(1, "Model is required").max(50),
  has_lien: z.boolean(),
});

type Step2Data = z.infer<typeof step2Schema>;

const UNSUPPORTED_MESSAGE =
  "This scenario isn\u2019t covered in this demo. " +
  "Please visit scdmv.net or contact the Rock Hill SCDMV office directly.";

interface Props {
  onComplete: (caseId: string) => void;
}

export default function IntakeWizard({ onComplete }: Props) {
  const [step, setStep] = useState<Step>("Situation");
  const [scenarioError, setScenarioError] = useState<string | null>(null);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Step 2 form
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors: s2Errors, isSubmitting },
  } = useForm<Step2Data>({
    resolver: zodResolver(step2Schema),
    defaultValues: { has_lien: false },
  });

  const hasLien = watch("has_lien");

  // -------------------------------------------------------------------------
  // Step 1: choose scenario
  // -------------------------------------------------------------------------
  const handleScenarioSelect = async (value: string) => {
    if (value !== "private_party_purchase") {
      setScenarioError(UNSUPPORTED_MESSAGE);
      return;
    }
    setScenarioError(null);
    setCreating(true);
    try {
      const c = await createCase();
      setCaseId(c.id);
      setStep("Vehicle");
    } catch (e: any) {
      setError(e.response?.data?.detail ?? "Failed to create case.");
    } finally {
      setCreating(false);
    }
  };

  // -------------------------------------------------------------------------
  // Step 2: vehicle info
  // -------------------------------------------------------------------------
  const onStep2Submit = async (data: Step2Data) => {
    if (!caseId) return;
    try {
      await saveDraft(caseId, {
        vehicle: {
          vin: data.vin.toUpperCase(),
          year: data.year,
          make: data.make,
          model: data.model,
          has_lien: data.has_lien,
        },
      });
      setStep("Confirm");
    } catch (e: any) {
      setError(e.response?.data?.detail ?? "Failed to save vehicle info.");
    }
  };

  // -------------------------------------------------------------------------
  // Progress indicator
  // -------------------------------------------------------------------------
  const stepIndex = STEPS.indexOf(step);

  return (
    <div className="max-w-xl mx-auto space-y-6">
      {/* Progress bar */}
      <nav aria-label="Wizard progress">
        <ol className="flex items-center gap-2">
          {STEPS.map((s, i) => (
            <li key={s} className="flex items-center gap-2">
              <span
                className={[
                  "w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold",
                  i < stepIndex
                    ? "bg-green-500 text-white"
                    : i === stepIndex
                    ? "bg-brand-600 text-white"
                    : "bg-gray-200 text-gray-500",
                ].join(" ")}
                aria-current={i === stepIndex ? "step" : undefined}
              >
                {i < stepIndex ? "\u2713" : i + 1}
              </span>
              <span
                className={[
                  "text-sm",
                  i === stepIndex ? "font-semibold text-gray-900" : "text-gray-500",
                ].join(" ")}
              >
                {s}
              </span>
              {i < STEPS.length - 1 && (
                <span className="text-gray-300 mx-1" aria-hidden="true">
                  /
                </span>
              )}
            </li>
          ))}
        </ol>
      </nav>

      {error && (
        <div role="alert" className="card bg-red-50 border-red-200 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Step 1 — Situation                                                */}
      {/* ----------------------------------------------------------------- */}
      {step === "Situation" && (
        <div className="card space-y-4">
          <h2>What brings you to the DMV?</h2>
          <p className="text-sm text-gray-600">
            Select your registration situation. Only one scenario is supported in this demo.
          </p>

          {scenarioError && (
            <div role="alert" className="rounded-md bg-amber-50 border border-amber-200 p-4 text-sm text-amber-800">
              <strong>Unsupported scenario</strong>
              <p className="mt-1">{scenarioError}</p>
              <a
                href="https://www.scdmvonline.com"
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 inline-block underline text-amber-700"
              >
                Visit scdmvonline.com &rarr;
              </a>
            </div>
          )}

          <div className="space-y-3">
            {[
              {
                value: "private_party_purchase",
                label: "I bought a used vehicle from a private seller",
                desc: "Register a previously-titled SC vehicle purchased from an individual (not a dealer).",
                supported: true,
              },
              {
                value: "dealer_purchase",
                label: "I bought from a dealer",
                desc: "Dealer-facilitated sales are not covered in this demo.",
                supported: false,
              },
              {
                value: "out_of_state",
                label: "I moved to SC with an out-of-state vehicle",
                desc: "Out-of-state title transfers are not covered in this demo.",
                supported: false,
              },
              {
                value: "other",
                label: "Something else",
                desc: "Other registration scenarios are not covered in this demo.",
                supported: false,
              },
            ].map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => handleScenarioSelect(opt.value)}
                disabled={creating}
                className={[
                  "w-full text-left rounded-lg border-2 p-4 transition-colors",
                  opt.supported
                    ? "border-brand-200 hover:border-brand-500 hover:bg-brand-50 cursor-pointer"
                    : "border-gray-200 hover:border-gray-300 hover:bg-gray-50 cursor-pointer",
                ].join(" ")}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-medium text-sm">{opt.label}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{opt.desc}</p>
                  </div>
                  {opt.supported && (
                    <span className="flex-shrink-0 text-xs bg-green-100 text-green-700 rounded-full px-2 py-0.5 font-medium">
                      Supported
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>

          {creating && <p className="text-sm text-gray-500 animate-pulse">Creating case\u2026</p>}
        </div>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Step 2 — Vehicle info                                             */}
      {/* ----------------------------------------------------------------- */}
      {step === "Vehicle" && (
        <form onSubmit={handleSubmit(onStep2Submit)} className="card space-y-4" noValidate>
          <h2>Tell us about the vehicle</h2>
          <p className="text-sm text-gray-500">
            This information will pre-fill your preparation summary.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label htmlFor="vin" className="label">
                Vehicle Identification Number (VIN)
              </label>
              <input
                id="vin"
                type="text"
                className="input uppercase"
                maxLength={17}
                placeholder="e.g. 1HGCM82633A004352"
                {...register("vin")}
              />
              {s2Errors.vin && (
                <p className="text-red-600 text-xs mt-1" role="alert">
                  {s2Errors.vin.message}
                </p>
              )}
              <p className="text-xs text-gray-400 mt-1">
                Demo VINs: 1HGCM82633A004352, 2T1BURHE0JC034761, 3VWFE21C04M000001
              </p>
            </div>

            <div>
              <label htmlFor="year" className="label">Year</label>
              <input
                id="year"
                type="number"
                className="input"
                placeholder="e.g. 2003"
                {...register("year", { valueAsNumber: true })}
              />
              {s2Errors.year && (
                <p className="text-red-600 text-xs mt-1" role="alert">
                  {s2Errors.year.message}
                </p>
              )}
            </div>

            <div>
              <label htmlFor="make" className="label">Make</label>
              <input id="make" type="text" className="input" placeholder="e.g. Honda" {...register("make")} />
              {s2Errors.make && (
                <p className="text-red-600 text-xs mt-1" role="alert">
                  {s2Errors.make.message}
                </p>
              )}
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="model" className="label">Model</label>
              <input id="model" type="text" className="input" placeholder="e.g. Accord" {...register("model")} />
              {s2Errors.model && (
                <p className="text-red-600 text-xs mt-1" role="alert">
                  {s2Errors.model.message}
                </p>
              )}
            </div>

            <div className="sm:col-span-2">
              <label className="flex items-center gap-3 cursor-pointer">
                <input type="checkbox" className="w-4 h-4 rounded accent-brand-600" {...register("has_lien")} />
                <span className="text-sm font-medium text-gray-700">
                  The title shows an active lien (money still owed on the vehicle)
                </span>
              </label>
              {hasLien && (
                <p className="mt-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
                  A lien release letter from the lienholder will be required.
                  This will appear as a conditional checklist item.
                </p>
              )}
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={() => setStep("Situation")}
              className="btn-secondary"
            >
              Back
            </button>
            <button type="submit" className="btn-primary flex-1" disabled={isSubmitting}>
              {isSubmitting ? "Saving\u2026" : "Continue"}
            </button>
          </div>
        </form>
      )}

      {/* ----------------------------------------------------------------- */}
      {/* Step 3 — Confirm                                                  */}
      {/* ----------------------------------------------------------------- */}
      {step === "Confirm" && caseId && (
        <div className="card space-y-4">
          <div className="flex items-center gap-3">
            <span className="text-3xl" aria-hidden="true">\u2705</span>
            <h2>Case created!</h2>
          </div>
          <p className="text-sm text-gray-600">
            Your registration case has been created and your vehicle details have been saved.
            Next, review your document checklist and begin filling out your preparation form.
          </p>
          <div className="flex gap-3">
            <button
              onClick={() => onComplete(caseId)}
              className="btn-primary flex-1"
            >
              View My Checklist &rarr;
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
