type CallType = 'outreach' | 'booking';

export interface CallBriefPayload {
  session_id: string;
  call_type: CallType;
  target_contact?: string;
  objective?: string;
  notes?: string;
  venue_id?: string;
}

export interface SessionSummary {
  headline: string;
  notes: string;
  action_items?: string[];
}

export interface BookingStatus {
  status: string;
  booking_id?: string;
  room_id?: string;
  check_in_time?: string;
  key_token?: string;
  payment_required?: boolean;
}

export interface SessionResponse {
  session_id: string;
  call_type: CallType;
  brief: Record<string, unknown>;
  summary: SessionSummary | null;
  booking_status: BookingStatus;
}

export interface BookingConfirmationPayload {
  room_id: string;
  check_in_time: string;
  attendees?: number;
  booking_id?: string;
}
