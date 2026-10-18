// ---------------------------------------------------------------
// Shared API types
// ---------------------------------------------------------------

export interface CaseResponse {
  id: string;
  user_id: string;
  status: string;
  scenario: string;
  vin: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ChecklistItem {
  id: string;
  requirement_key: string;
  label: string;
  description: string | null;
  is_required: boolean;
  is_conditional: boolean;
  condition_note: string | null;
  status: "missing" | "uploaded" | "reviewed" | "needs_replacement" | "waived";
}

export interface DocumentRecord {
  id: string;
  original_filename: string;
  storage_filename: string;
  mime_type: string;
  size_bytes: number;
  status: "uploaded_pending" | "reviewed" | "needs_replacement";
  checklist_item_id: string | null;
  created_at: string;
}

export interface VehicleInfo {
  vin: string;
  year: number;
  make: string;
  model: string;
  body_style?: string;
  color?: string;
  odometer_reading?: number;
  odometer_unit?: string;
  has_lien?: boolean;
}

export interface BuyerInfo {
  full_name: string;
  address_line1: string;
  address_line2?: string;
  city: string;
  state: string;
  zip_code: string;
  phone?: string;
  sc_county?: string;
}

export interface SellerInfo {
  full_name: string;
  address_line1: string;
  address_line2?: string;
  city: string;
  state: string;
  zip_code: string;
}

export interface PurchaseInfo {
  purchase_price_dollars: number;
  purchase_date: string;
  sale_type?: string;
}

export interface Form400Draft {
  vehicle?: VehicleInfo;
  buyer?: BuyerInfo;
  seller?: SellerInfo;
  purchase?: PurchaseInfo;
  has_odometer_disclosure?: boolean;
  has_lien_release?: boolean;
  additional_notes?: string;
}

export interface DraftResponse {
  id: string;
  case_id: string;
  form_type: string;
  data: Form400Draft;
  version: number;
  is_complete: boolean;
  updated_at: string;
  metadata: {
    key: string;
    label: string;
    description: string;
    disclaimer: string;
    sections: Array<{ key: string; label: string }>;
  };
}

export interface RequirementDoc {
  key: string;
  label: string;
  description: string;
  is_required: boolean;
  is_conditional: boolean;
  condition_note?: string;
  accepted_formats: string[];
}

export interface RequirementsResponse {
  scenario: {
    key: string;
    label: string;
    description: string;
    disclaimer: string;
  };
  documents: RequirementDoc[];
  forms: Array<{ key: string; label: string; description: string }>;
  steps: Array<{ order: number; key: string; label: string; detail: string }>;
  fee_notes: {
    disclaimer: string;
    title_fee_cents: number;
    registration_fee_cents: number;
  };
  official_links: Array<{ label: string; url: string }>;
}

export interface SlotResponse {
  id: string;
  location_id: string;
  start_time: string;
  end_time: string;
  capacity: number;
  booked_count: number;
  available: boolean;
}

export interface AppointmentResponse {
  id: string;
  case_id: string;
  slot_id: string;
  status: string;
  confirmation_code: string;
  booked_at: string;
  start_time: string;
  disclaimer: string;
}

export interface QueueStatusResponse {
  location_id: string;
  waiting_count: number;
  in_service_count: number;
  called_count: number;
  estimated_wait_minutes: number | null;
  p50_service_minutes: number | null;
  p90_service_minutes: number | null;
  sample_size: number;
  method: string;
  queue_status: "empty" | "quiet" | "active" | "busy";
  last_updated: string;
  simulated: boolean;
  disclaimer: string;
}

export interface LocationResponse {
  id: string;
  name: string;
  city: string;
  is_demo: boolean;
}

export interface WalkInResponse {
  queue_entry_id: string;
  position: number;
  estimated_wait_minutes: number | null;
  disclaimer: string;
}

export interface QueueEntryDetail {
  id: string;
  case_id: string;
  location_id: string;
  status: string;
  position: number | null;
  is_walk_in: boolean;
  checked_in_at: string | null;
  called_at: string | null;
  service_started_at: string | null;
}
