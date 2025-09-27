import { useEffect, useMemo, useState } from 'react';

import './App.css';

import { post } from './api/client';
import type { CallBriefPayload, SessionSummary } from './api/types';
import { BookingModeToggle } from './components/BookingModeToggle';
import { CallBriefForm } from './components/CallBriefForm';
import { CallDashboard } from './components/CallDashboard';
import { RealtimeBookingChat } from './components/RealtimeBookingChat';
import { SummaryView } from './components/SummaryView';
import { useSession } from './hooks/useSession';

const CALL_STATUS_IDLE = 'idle';
const CALL_STATUS_QUEUED = 'queued';
const CALL_STATUS_ERROR = 'error';
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';

interface CallLaunchResponse {
  session_id: string;
  status: string;
}

function App() {
  const [callType, setCallType] = useState<CallBriefPayload['call_type']>('outreach');
  const [bookingMode, setBookingMode] = useState<'vapi' | 'realtime'>('vapi');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>(CALL_STATUS_IDLE);
  const [transcript, setTranscript] = useState<string[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: sessionData, loading: sessionLoading, error: sessionError } = useSession(sessionId);

  useEffect(() => {
    if (!sessionId) return;

    const source = new EventSource(`${API_BASE}/events/${sessionId}`);
    source.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === 'transcript' && payload.text) {
          setTranscript((prev) => [...prev, payload.text]);
        }
        if (payload.type === 'status' && payload.status) {
          setStatus(payload.status);
        }
      } catch (error) {
        console.error('Failed to parse event payload', error);
      }
    };
    source.onerror = () => {
      source.close();
    };

    return () => {
      source.close();
    };
  }, [sessionId]);

  useEffect(() => {
    if (sessionData?.booking_status?.status && sessionData.booking_status.status !== 'pending') {
      setStatus(sessionData.booking_status.status);
    }
  }, [sessionData?.booking_status?.status]);

  const summary: SessionSummary | null = useMemo(() => {
    return sessionData?.summary ?? null;
  }, [sessionData?.summary]);

  async function handleLaunch(payload: CallBriefPayload) {
    try {
      setErrorMessage(null);
      setStatus('launching');
      const response = await post<CallLaunchResponse>('/calls/launch', payload);
      setSessionId(response.session_id);
      setStatus(response.status ?? CALL_STATUS_QUEUED);
      setTranscript([]);
    } catch (error) {
      setStatus(CALL_STATUS_ERROR);
      if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage('Failed to launch call');
      }
    }
  }

  return (
    <div className="app-shell">
      <header>
        <h1>VoiceBooking Control Center</h1>
        <p>Create outreach calls, manage booking conversations, and review outcomes.</p>
      </header>

      <main>
        <section className="card">
          <h2>Interaction Type</h2>
          <div className="toggle-group">
            <button type="button" className={callType === 'outreach' ? 'active' : ''} onClick={() => setCallType('outreach')}>
              Outreach Call
            </button>
            <button type="button" className={callType === 'booking' ? 'active' : ''} onClick={() => setCallType('booking')}>
              Booking Call
            </button>
          </div>
        </section>

        {callType === 'booking' ? <BookingModeToggle mode={bookingMode} onChange={setBookingMode} /> : null}

        <CallBriefForm callType={callType} onSubmit={handleLaunch} />

        {errorMessage ? (
          <div className="card error">Error launching call: {errorMessage}</div>
        ) : null}

        <CallDashboard sessionId={sessionId} status={status} transcript={transcript} />

        <SummaryView summary={summary} />

        {callType === 'booking' && bookingMode === 'realtime' ? <RealtimeBookingChat sessionId={sessionId} /> : null}

        {sessionLoading ? <div className="card">Loading session...</div> : null}
        {sessionError ? <div className="card error">{sessionError.message}</div> : null}
      </main>
    </div>
  );
}

export default App;
