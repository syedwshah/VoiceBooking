interface CallDashboardProps {
  sessionId: string | null;
  status: string;
  transcript: string[];
}

export function CallDashboard({ sessionId, status, transcript }: CallDashboardProps) {
  return (
    <section className="card">
      <h2>Live Call Status</h2>
      <p>Session: {sessionId ?? 'N/A'}</p>
      <p>Status: {status}</p>
      <div className="transcript">
        {transcript.length === 0 ? <p>No transcript yet.</p> : transcript.map((line, index) => <p key={index}>{line}</p>)}
      </div>
    </section>
  );
}
