import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import {
  getChecklist,
  listDocuments,
  uploadDocument,
  deleteDocument,
} from "../api/dmv";
import type { ChecklistItem, DocumentRecord } from "../types/api";

const STATUS_CONFIG: Record<string, { label: string; cls: string }> = {
  missing: { label: "Missing", cls: "badge-missing" },
  uploaded: { label: "Uploaded — pending review", cls: "badge-uploaded" },
  reviewed: { label: "Reviewed", cls: "badge-reviewed" },
  needs_replacement: { label: "Needs replacement", cls: "badge-needs-replacement" },
  waived: { label: "Waived", cls: "badge-reviewed" },
};

const DOC_STATUS_CONFIG: Record<string, { label: string; cls: string }> = {
  uploaded_pending: { label: "Pending review", cls: "badge-uploaded" },
  reviewed: { label: "Reviewed", cls: "badge-reviewed" },
  needs_replacement: { label: "Needs replacement", cls: "badge-needs-replacement" },
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

interface UploadState {
  [itemId: string]: { uploading: boolean; error: string | null };
}

export default function DocumentsPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const [items, setItems] = useState<ChecklistItem[]>([]);
  const [docs, setDocs] = useState<DocumentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>({});
  const [deleting, setDeleting] = useState<string | null>(null);
  const fileRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const refresh = async () => {
    if (!caseId) return;
    try {
      const [cl, dl] = await Promise.all([getChecklist(caseId), listDocuments(caseId)]);
      setItems(cl);
      setDocs(dl);
      setError(null);
    } catch (e: any) {
      setError(e.response?.data?.detail ?? "Failed to load data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, [caseId]);

  const handleUpload = async (itemId: string, file: File) => {
    if (!caseId) return;
    setUploadState((s) => ({ ...s, [itemId]: { uploading: true, error: null } }));
    try {
      await uploadDocument(caseId, file, itemId);
      await refresh();
    } catch (e: any) {
      const msg = e.response?.data?.detail ?? "Upload failed.";
      setUploadState((s) => ({ ...s, [itemId]: { uploading: false, error: msg } }));
      return;
    }
    setUploadState((s) => ({ ...s, [itemId]: { uploading: false, error: null } }));
    // Clear the file input
    if (fileRefs.current[itemId]) fileRefs.current[itemId]!.value = "";
  };

  const handleDelete = async (docId: string) => {
    if (!caseId || !window.confirm("Delete this document?")) return;
    setDeleting(docId);
    try {
      await deleteDocument(caseId, docId);
      await refresh();
    } catch (e: any) {
      setError(e.response?.data?.detail ?? "Failed to delete document.");
    } finally {
      setDeleting(null);
    }
  };

  const docsForItem = (itemId: string) => docs.filter((d) => d.checklist_item_id === itemId);

  if (loading) return <p className="text-gray-500 animate-pulse">Loading documents\u2026</p>;

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1>Document Upload</h1>
        <p className="text-sm text-gray-500 mt-1">
          Case {caseId?.slice(0, 8)}\u2026 &middot; Upload sample photos or PDFs for each required item.
        </p>
      </div>

      {error && (
        <div role="alert" className="card bg-red-50 border-red-200 text-red-700 text-sm">
          {error}
        </div>
      )}

      <div className="card bg-yellow-50 border-yellow-200 text-xs text-yellow-800">
        Uploads are preparation aids only — not proof of authenticity or legal validity.
        Accepted formats: JPEG, PNG, WebP, PDF &middot; Max size: 10 MB per file.
      </div>

      {items.length === 0 ? (
        <div className="card text-center py-8 text-gray-400">No checklist items found.</div>
      ) : (
        <ul className="space-y-4">
          {items.map((item) => {
            const itemDocs = docsForItem(item.id);
            const us = uploadState[item.id] ?? { uploading: false, error: null };
            const statusConf = STATUS_CONFIG[item.status] ?? STATUS_CONFIG.missing;

            return (
              <li key={item.id} className="card space-y-3">
                <div className="flex items-start justify-between gap-2 flex-wrap">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-medium text-sm">{item.label}</p>
                      {item.is_conditional && (
                        <span className="text-xs bg-amber-100 text-amber-700 rounded-full px-2 py-0.5">
                          Conditional
                        </span>
                      )}
                    </div>
                    {item.description && (
                      <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{item.description}</p>
                    )}
                    {item.condition_note && (
                      <p className="text-xs text-amber-600 mt-1">&#9432; {item.condition_note}</p>
                    )}
                  </div>
                  <span className={statusConf.cls}>{statusConf.label}</span>
                </div>

                {/* Uploaded documents for this item */}
                {itemDocs.length > 0 && (
                  <ul className="space-y-2">
                    {itemDocs.map((doc) => {
                      const dsc = DOC_STATUS_CONFIG[doc.status] ?? DOC_STATUS_CONFIG.uploaded_pending;
                      const isImage = doc.mime_type.startsWith("image/");
                      return (
                        <li
                          key={doc.id}
                          className="flex items-center gap-3 rounded-md bg-gray-50 border border-gray-200 p-2"
                        >
                          {/* Thumbnail placeholder (no serving route yet — M4) */}
                          <div className="w-10 h-10 flex-shrink-0 rounded bg-gray-200 flex items-center justify-center text-gray-400 text-xs font-bold overflow-hidden">
                            {isImage ? "\uD83D\uDDBC" : "\uD83D\uDCC4"}
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="text-xs font-medium truncate">{doc.original_filename}</p>
                            <p className="text-xs text-gray-400">
                              {formatBytes(doc.size_bytes)} &middot;{" "}
                              {new Date(doc.created_at).toLocaleString()}
                            </p>
                          </div>
                          <span className={dsc.cls + " flex-shrink-0"}>{dsc.label}</span>
                          <button
                            onClick={() => handleDelete(doc.id)}
                            disabled={deleting === doc.id}
                            className="text-xs text-red-600 hover:underline flex-shrink-0 disabled:opacity-50"
                              aria-label={`Delete ${doc.original_filename}`}
                          >
                            {deleting === doc.id ? "Deleting\u2026" : "Delete"}
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}

                {/* Upload area */}
                <div>
                  <label
                    htmlFor={`upload-${item.id}`}
                    className={[
                      "flex items-center gap-2 cursor-pointer rounded-md border-2 border-dashed px-4 py-3",
                      "text-sm text-gray-500 hover:border-brand-400 hover:text-brand-600 transition-colors",
                      us.uploading ? "opacity-50 cursor-not-allowed" : "",
                    ].join(" ")}
                  >
                    <span aria-hidden="true">\uD83D\uDCCE</span>
                    <span>{us.uploading ? "Uploading\u2026" : "Choose file to upload"}</span>
                  </label>
                  <input
                    id={`upload-${item.id}`}
                    type="file"
                    accept="image/jpeg,image/png,image/webp,application/pdf"
                    className="sr-only"
                    disabled={us.uploading}
                    ref={(el) => { fileRefs.current[item.id] = el; }}
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) handleUpload(item.id, file);
                    }}
                  />
                  {us.error && (
                    <p className="text-red-600 text-xs mt-1" role="alert">{us.error}</p>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
