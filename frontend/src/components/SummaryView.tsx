import type { SessionSummary } from '../api/types';

interface SummaryViewProps {
  summary: SessionSummary | null;
}

export function SummaryView({ summary }: SummaryViewProps) {
  if (!summary) {
    return (
      <section className="card">
        <h2>Summary</h2>
        <p>No summary available yet.</p>
      </section>
    );
  }

  return (
    <section className="card">
      <h2>Summary</h2>
      <p className="headline">{summary.headline}</p>
      <p>{summary.notes}</p>
      {summary.actionItems && summary.actionItems.length > 0 ? (
        <ul>
          {summary.actionItems.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
