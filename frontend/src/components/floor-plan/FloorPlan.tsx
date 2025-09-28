import { useMemo } from 'react';
import './FloorPlan.scss';

export type FloorRoomStatus = 'available' | 'booked';

export interface FloorRoom {
  id: string;
  label: string;
  capacity: number;
  status: FloorRoomStatus;
  bookingInfo?: {
    customerName?: string | null;
    startTime?: string | null;
    endTime?: string | null;
  };
}

interface FloorPlanProps {
  rooms: FloorRoom[];
  venueName?: string;
  isLoading?: boolean;
  error?: string | null;
  lastUpdated?: Date | null;
  onRefresh?: () => void;
}

export const FLOOR_ROOMS = [
  { id: 'aurora-main', label: 'Main Gallery', capacity: 200, venueName: 'Aurora Hall' },
  { id: 'aurora-lounge', label: 'Skyline Lounge', capacity: 60, venueName: 'Aurora Hall' },
  { id: 'harbor-atrium', label: 'Atrium', capacity: 120, venueName: 'Aurora Hall' },
  { id: 'harbor-boardroom', label: 'Boardroom', capacity: 24, venueName: 'Aurora Hall' },
] as const;

export const ROOM_DEFAULTS = FLOOR_ROOMS.reduce(
  (acc, room) => {
    acc[room.id] = room;
    return acc;
  },
  {} as Record<string, (typeof FLOOR_ROOMS)[number]>,
);

export const ROOM_LAYOUTS: Record<string, { column: [number, number]; row: [number, number]; }> = {
  'aurora-main': { column: [1, 8], row: [1, 4] },
  'aurora-lounge': { column: [8, 13], row: [1, 3] },
  'harbor-atrium': { column: [1, 8], row: [4, 7] },
  'harbor-boardroom': { column: [8, 13], row: [3, 6] },
};

export const SUPPORTED_ROOM_IDS = FLOOR_ROOMS.map((room) => room.id) as string[];

const STATUS_LABELS: Record<FloorRoomStatus, string> = {
  available: 'Available',
  booked: 'Booked',
};

export function FloorPlan({
  rooms,
  venueName,
  isLoading = false,
  error,
  lastUpdated,
  onRefresh,
}: FloorPlanProps) {
  const availableCount = useMemo(
    () => rooms.filter((room) => room.status === 'available').length,
    [rooms]
  );

  return (
    <div className="floor-plan" data-component="FloorPlan">
      <div className="floor-plan__header">
        <div className="floor-plan__title">
          <span className="floor-plan__venue">{venueName || 'Coworking Floor'}</span>
          <span className="floor-plan__availability">
            {availableCount} of {rooms.length || 0} rooms available
          </span>
          {lastUpdated && (
            <span className="floor-plan__timestamp">
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
        </div>
        <div className="floor-plan__actions">
          <button
            type="button"
            className="floor-plan__refresh"
            onClick={onRefresh}
            disabled={isLoading}
          >
            {isLoading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>
      {error && <div className="floor-plan__error">{error}</div>}
      <div className="floor-plan__grid">
        {rooms.map((room) => {
          const layout = ROOM_LAYOUTS[room.id];
          const style = layout
            ? {
                gridColumn: `${layout.column[0]} / ${layout.column[1]}`,
                gridRow: `${layout.row[0]} / ${layout.row[1]}`,
              }
            : undefined;

          return (
            <div
              key={room.id}
              className={`floor-plan__room floor-plan__room--${room.status}`}
              style={style}
              title={room.bookingInfo?.customerName || room.label}
            >
              <div className="floor-plan__room-label">{room.label}</div>
              <div className="floor-plan__room-capacity">{room.capacity} ppl</div>
              {room.bookingInfo && (
                <div className="floor-plan__room-booking">
                  <div>{room.bookingInfo.customerName || 'Reserved'}</div>
                  {room.bookingInfo.startTime && room.bookingInfo.endTime && (
                    <div>
                      {new Date(room.bookingInfo.startTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      {' '}–{' '}
                      {new Date(room.bookingInfo.endTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
        {!rooms.length && !isLoading && !error && (
          <div className="floor-plan__empty">No rooms to display</div>
        )}
      </div>
      <div className="floor-plan__legend">
        {Object.entries(STATUS_LABELS).map(([status, label]) => (
          <div key={status} className="floor-plan__legend-item">
            <span className={`floor-plan__status-dot floor-plan__status-dot--${status}`} />
            <span>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
