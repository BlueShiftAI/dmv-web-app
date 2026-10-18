import { api } from "./client";
import type {
  CaseResponse,
  ChecklistItem,
  DocumentRecord,
  DraftResponse,
  RequirementsResponse,
  SlotResponse,
  AppointmentResponse,
  QueueStatusResponse,
  LocationResponse,
  WalkInResponse,
} from "../types/api";

// Cases
export const listCases = () =>
  api.get<CaseResponse[]>("/api/cases").then((r) => r.data);

export const createCase = (vin?: string) =>
  api
    .post<CaseResponse>("/api/cases", { scenario: "private_party_purchase", vin })
    .then((r) => r.data);

export const getCase = (id: string) =>
  api.get<CaseResponse>(`/api/cases/${id}`).then((r) => r.data);

// Checklist
export const getChecklist = (caseId: string) =>
  api.get<ChecklistItem[]>(`/api/cases/${caseId}/checklist`).then((r) => r.data);

// Draft
export const getDraft = (caseId: string) =>
  api.get<DraftResponse>(`/api/cases/${caseId}/draft`).then((r) => r.data);

export const saveDraft = (caseId: string, data: object, isComplete = false) =>
  api
    .put<DraftResponse>(`/api/cases/${caseId}/draft`, { data, is_complete: isComplete })
    .then((r) => r.data);

export const downloadPdf = (caseId: string) =>
  api
    .get(`/api/cases/${caseId}/draft/pdf`, { responseType: "blob" })
    .then((r) => r.data as Blob);

// Documents
export const listDocuments = (caseId: string) =>
  api.get<DocumentRecord[]>(`/api/cases/${caseId}/documents`).then((r) => r.data);

export const uploadDocument = (
  caseId: string,
  file: File,
  checklistItemId?: string
) => {
  const form = new FormData();
  form.append("file", file);
  if (checklistItemId) form.append("checklist_item_id", checklistItemId);
  return api
    .post<DocumentRecord>(`/api/cases/${caseId}/documents`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((r) => r.data);
};

export const deleteDocument = (caseId: string, docId: string) =>
  api.delete(`/api/cases/${caseId}/documents/${docId}`);

// Requirements
export const getRequirements = () =>
  api.get<RequirementsResponse>("/api/requirements").then((r) => r.data);

// Appointments
export const listSlots = (locationId: string, date: string) =>
  api
    .get<SlotResponse[]>(`/api/appointments/slots?location_id=${locationId}&date=${date}`)
    .then((r) => r.data);

export const bookAppointment = (caseId: string, slotId: string, notes?: string) =>
  api
    .post<AppointmentResponse>("/api/appointments", { case_id: caseId, slot_id: slotId, notes })
    .then((r) => r.data);

export const cancelAppointment = (apptId: string) =>
  api.delete(`/api/appointments/${apptId}`);

export const checkIn = (apptId: string) =>
  api.post<{ message: string; queue_entry_id: string }>(`/api/appointments/${apptId}/checkin`)
    .then((r) => r.data);

// Queue
export const getQueueStatus = (locationId: string) =>
  api.get<QueueStatusResponse>(`/api/queue/${locationId}`).then((r) => r.data);

export const walkInCheckIn = (locationId: string) =>
  api.post<WalkInResponse>(`/api/queue/${locationId}/walkin`).then((r) => r.data);

// Locations (public, auth required)
export const listLocations = () =>
  api.get<LocationResponse[]>("/api/queue/locations").then((r) => r.data);

// Appointment lookup for a case
export const getAppointmentForCase = (caseId: string) =>
  api.get<AppointmentResponse | null>(`/api/appointments?case_id=${caseId}`).then((r) => r.data);

// Case lifecycle
export const submitCase = (caseId: string) =>
  api.post<CaseResponse>(`/api/cases/${caseId}/submit`).then((r) => r.data);

export const updateCaseStatus = (
  caseId: string,
  status: string,
  staffNotes?: string
) =>
  api
    .patch<CaseResponse>(`/api/cases/${caseId}/status`, { status, staff_notes: staffNotes })
    .then((r) => r.data);
