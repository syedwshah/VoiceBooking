import { FormEvent, useState } from 'react';

import type { CallBriefPayload } from '../api/types';

interface CallBriefFormProps {
  callType: CallBriefPayload['call_type'];
  onSubmit: (payload: CallBriefPayload) => void;
}

export function CallBriefForm({ callType, onSubmit }: CallBriefFormProps) {
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID());
  const [targetContact, setTargetContact] = useState('');
  const [objective, setObjective] = useState('');
  const [notes, setNotes] = useState('');
  const [venueId, setVenueId] = useState('');

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({
      session_id: sessionId,
      call_type: callType,
      target_contact: targetContact || undefined,
      objective: objective || undefined,
      notes: notes || undefined,
      venue_id: venueId || undefined,
    });
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h2>Call Brief</h2>
      <label>
        Session ID
        <input value={sessionId} onChange={(event) => setSessionId(event.target.value)} />
      </label>
      <label>
        Target Contact
        <input value={targetContact} onChange={(event) => setTargetContact(event.target.value)} placeholder="e.g. Venue manager" />
      </label>
      <label>
        Objective
        <textarea value={objective} onChange={(event) => setObjective(event.target.value)} placeholder="What outcome do you want from the call?" />
      </label>
      <label>
        Notes
        <textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Important talking points" />
      </label>
      <label>
        Venue ID
        <input value={venueId} onChange={(event) => setVenueId(event.target.value)} placeholder="Match metadata entry" />
      </label>
      <button type="submit">Launch {callType === 'outreach' ? 'Outreach' : 'Booking'} Call</button>
    </form>
  );
}
