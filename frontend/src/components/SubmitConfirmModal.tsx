/**
 * SubmitConfirmModal
 *
 * Shown when a customer clicks "Submit for Review" on a draft case.
 * Forces an explicit confirmation before the case is submitted, and makes
 * the simulated nature of the submission unambiguous.
 */

interface Props {
  caseId: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function SubmitConfirmModal({ caseId, onConfirm, onCancel }: Props) {
  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="submit-modal-title"
      onClick={(e) => { if (e.target === e.currentTarget) onCancel(); }}
    >
      <div className="w-full max-w-md rounded-xl bg-white shadow-2xl border border-gray-200 overflow-hidden">
        {/* Header */}
        <div className="bg-brand-600 px-6 py-4">
          <h2 id="submit-modal-title" className="text-white text-base font-semibold">
            Submit Case for Review
          </h2>
          <p className="text-blue-100 text-xs mt-0.5 font-mono">
            Case {caseId.slice(0, 8)}&hellip;
          </p>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4">
          <div className="rounded-md bg-yellow-50 border border-yellow-300 px-4 py-3 text-sm text-yellow-800">
            <p className="font-semibold">⚠️ Important — Read before continuing</p>
            <ul className="mt-2 space-y-1 list-disc list-inside text-xs leading-relaxed">
              <li>
                This is a <strong>simulated submission</strong> for the IBM SkillsBuild
                demo only.
              </li>
              <li>
                No information is sent to the South Carolina DMV or any government
                system.
              </li>
              <li>
                A demo approval does <strong>not</strong> legally register your vehicle
                or transfer ownership.
              </li>
              <li>
                You must visit the Rock Hill SCDMV office with your original documents
                to complete the official process.
              </li>
            </ul>
          </div>

          <p className="text-sm text-gray-700">
            Submitting will send your case to demo staff for review. You will receive
            a notification when staff approves or returns the case.
          </p>
        </div>

        {/* Footer */}
        <div className="px-6 pb-5 flex gap-3 justify-end">
          <button
            type="button"
            onClick={onCancel}
            className="btn-secondary"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="btn-primary"
          >
            Confirm Simulated Submission
          </button>
        </div>
      </div>
    </div>
  );
}
