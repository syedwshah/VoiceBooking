import type { ChangeEvent, FormEvent } from 'react';
import { useEffect, useMemo, useState } from 'react';

import type { CallBriefPayload } from '../api/types';

interface CallBriefFormProps {
  callType: CallBriefPayload['call_type'];
  onSubmit: (payload: CallBriefPayload) => void;
}

export function CallBriefForm({ callType, onSubmit }: CallBriefFormProps) {
  const [sessionId, setSessionId] = useState<string>(() => crypto.randomUUID());
  const templates = useMemo(
    () => ({
      outreach: {
        targetContact: 'Jamie Lee – Partnerships Manager',
        objective: 'Introduce the agency and schedule a discovery follow-up.',
        notes:
          'Highlight recent campaign success, ask for preferred contact channel, confirm availability for a Tuesday 11am meeting.',
        venueId: '',
        phoneNumber: '+12679784241',
      },
      booking: {
        targetContact: 'Alex Morgan – Workspace Coordinator',
        objective: 'Reserve a workspace for a 40-person offsite next Thursday.',
        notes:
          'Needs projector, breakout area, catering for lunch. Confirm payment method and send access instructions by email.',
        venueId: 'aurora-hall',
        phoneNumber: '+12679784241',
      },
    }),
    [],
  );

  const [targetContact, setTargetContact] = useState<string | null>(null);
  const [objective, setObjective] = useState<string | null>(null);
  const [notes, setNotes] = useState<string | null>(null);
  const [venueId, setVenueId] = useState<string | null>(null);
  const [phoneNumber, setPhoneNumber] = useState<string | null>(null);

  useEffect(() => {
    setTargetContact(null);
    setObjective(null);
    setNotes(null);
    setVenueId(null);
    setPhoneNumber(null);
  }, [callType]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({
      session_id: sessionId,
      call_type: callType,
      target_contact: (targetContact ?? templates[callType].targetContact) || undefined,
      objective: (objective ?? templates[callType].objective) || undefined,
      notes: (notes ?? templates[callType].notes) || undefined,
      venue_id: (venueId ?? templates[callType].venueId) || undefined,
      phone_number: (phoneNumber ?? templates[callType].phoneNumber) || undefined,
    });
  }

  function markEdited(callback: (value: string | null) => void) {
    return (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      const value = event.target.value;
      callback(value === '' ? null : value);
    };
  }

  const template = templates[callType];
  const displayContact = targetContact ?? template.targetContact;
  const displayObjective = objective ?? template.objective;
  const displayNotes = notes ?? template.notes;
  const displayVenue = venueId ?? template.venueId;
  const displayPhone = phoneNumber ?? template.phoneNumber;

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h2>Call Brief</h2>
      <label>
        Session ID
        <div className="session-row">
          <input
            value={sessionId}
            onChange={(event) => setSessionId(event.target.value)}
            placeholder="Auto-generated ID"
          />
          <button type="button" className="ghost" onClick={() => setSessionId(crypto.randomUUID())}>
            New ID
          </button>
        </div>
      </label>
      <label>
        Target Contact
        <input
          value={displayContact}
          onChange={markEdited(setTargetContact)}
          placeholder="e.g. Jamie Lee – Partnerships Manager"
        />
      </label>
      <label>
        Objective
        <textarea
          value={displayObjective}
          onChange={markEdited(setObjective)}
          placeholder="What outcome do you want from the call?"
        />
      </label>
      <label>
        Notes
        <textarea
          value={displayNotes}
          onChange={markEdited(setNotes)}
          placeholder="Important talking points"
        />
      </label>
      <label>
        Venue ID
        <input
          value={displayVenue}
          onChange={markEdited(setVenueId)}
          placeholder="Match metadata entry (e.g. aurora-hall)"
        />
      </label>
      <label>
        Phone Number
        <input
          value={displayPhone}
          onChange={markEdited(setPhoneNumber)}
          placeholder="+12679784241"
        />
      </label>
      <button type="submit">Launch {callType === 'outreach' ? 'Outreach' : 'Booking'} Call</button>
    </form>
  );
}
