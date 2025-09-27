interface BookingModeToggleProps {
  mode: 'vapi' | 'realtime';
  onChange: (mode: 'vapi' | 'realtime') => void;
}

export function BookingModeToggle({ mode, onChange }: BookingModeToggleProps) {
  return (
    <div className="card">
      <h2>Booking Mode</h2>
      <div className="toggle-group">
        <button type="button" className={mode === 'vapi' ? 'active' : ''} onClick={() => onChange('vapi')}>
          Voice (Vapi)
        </button>
        <button type="button" className={mode === 'realtime' ? 'active' : ''} onClick={() => onChange('realtime')}>
          Chat (Realtime)
        </button>
      </div>
    </div>
  );
}
