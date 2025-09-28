import { useEffect, useRef, useCallback, useState } from 'react';
import Vapi from '@vapi-ai/web';
import { WavRecorder, WavStreamPlayer } from '../lib/wavtools/index.js';
import { WavRenderer } from '../utils/wav_renderer';

import { X, Zap, ArrowUp, ArrowDown } from 'react-feather';
import { Button } from '../components/button/Button';
import { Toggle } from '../components/toggle/Toggle';
import { FloorPlan, FloorRoom, SUPPORTED_ROOM_IDS, ROOM_DEFAULTS } from '../components/floor-plan/FloorPlan';
import logo from '../logo.svg';

import './ConsolePage.scss';

interface ApiVenue {
  id: string;
  name: string;
  rooms: ApiRoom[];
}

interface ApiRoom {
  id: string;
  label: string;
  capacity: number;
}

interface ApiBooking {
  id: number;
  status: string;
  venue_id: string;
  room_id: string | null;
  start_time?: string | null;
  end_time?: string | null;
  attendee_count?: number | null;
  notes?: string | null;
  customer?: { name?: string | null; email?: string | null; phone_number?: string | null } | null;
}

interface RealtimeEvent {
  time: string;
  source: 'client' | 'server';
  count?: number;
  event: { [key: string]: any };
}

interface PaymentToastState {
  transactionId: string;
  amount?: number | null;
  currency?: string | null;
}

interface ApiPayment {
  id: number;
  booking_id?: number | null;
  provider: string;
  status: string;
  amount?: number | null;
  currency?: string | null;
  transaction_id?: string | null;
  provider_hint?: string | null;
}

export function ConsolePage() {
  const wavRecorderRef = useRef(new WavRecorder({ sampleRate: 24000 }));
  const wavStreamPlayerRef = useRef(new WavStreamPlayer({ sampleRate: 24000 }));
  const vapiRef = useRef(new Vapi(process.env.REACT_APP_VAPI_PUBLIC_KEY!));

  const clientCanvasRef = useRef<HTMLCanvasElement>(null);
  const serverCanvasRef = useRef<HTMLCanvasElement>(null);
  const eventsScrollHeightRef = useRef(0);
  const eventsScrollRef = useRef<HTMLDivElement>(null);
  const startTimeRef = useRef<string>(new Date().toISOString());

  const [items, setItems] = useState<any[]>([]);
  const [realtimeEvents, setRealtimeEvents] = useState<RealtimeEvent[]>([]);
  const [expandedEvents, setExpandedEvents] = useState<{ [key: string]: boolean }>({});
  const [isConnected, setIsConnected] = useState(false);
  const [canPushToTalk, setCanPushToTalk] = useState(true);
  const [isRecording, setIsRecording] = useState(false);
  const [floorRooms, setFloorRooms] = useState<FloorRoom[]>([]);
  const [floorVenueName, setFloorVenueName] = useState('Coworking Floor');
  const [floorLoading, setFloorLoading] = useState(false);
  const [floorError, setFloorError] = useState<string | null>(null);
  const [floorUpdatedAt, setFloorUpdatedAt] = useState<Date | null>(null);
  const [bookingsList, setBookingsList] = useState<ApiBooking[]>([]);
  const [roomDirectory, setRoomDirectory] = useState<Record<string, { label: string; venueName: string; capacity: number }>>(
    () => Object.fromEntries(Object.entries(ROOM_DEFAULTS).map(([id, room]) => [id, { label: room.label, venueName: room.venueName, capacity: room.capacity }]))
  );
  const [paymentToast, setPaymentToast] = useState<PaymentToastState | null>(null);
  const processedTransactionsRef = useRef<Set<string>>(new Set());
  const audioContextRef = useRef<AudioContext | null>(null);

  const backendBase = (process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000/api').replace(/\/$/, '');

  const ensureAudioContext = useCallback(async () => {
    const AudioCtx =
      (window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext);
    if (!AudioCtx) {
      console.warn('AudioContext not supported in this browser');
      return null;
    }
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioCtx();
    }
    const ctx = audioContextRef.current;
    if (ctx.state === 'suspended') {
      try {
        await ctx.resume();
      } catch (error) {
        console.warn('Unable to resume audio context', error);
        return null;
      }
    }
    return ctx;
  }, []);

  const playPaymentChime = useCallback(async () => {
    try {
      const ctx = await ensureAudioContext();
      if (!ctx) return;
      const oscillator = ctx.createOscillator();
      const gain = ctx.createGain();
      const now = ctx.currentTime;
      oscillator.type = 'sine';
      oscillator.frequency.setValueAtTime(880, now);
      oscillator.frequency.exponentialRampToValueAtTime(1320, now + 0.18);
      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.exponentialRampToValueAtTime(0.16, now + 0.03);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.6);
      oscillator.connect(gain);
      gain.connect(ctx.destination);
      oscillator.start();
      oscillator.stop(now + 0.65);
      oscillator.onended = () => {
        gain.disconnect();
        oscillator.disconnect();
      };
    } catch (error) {
      console.warn('Unable to play payment chime', error);
    }
  }, [ensureAudioContext]);

  const fetchFloorData = useCallback(async () => {
    if (!backendBase) {
      setFloorError('Backend URL is not configured');
      return;
    }
    try {
      setFloorLoading(true);
      setFloorError(null);

      const venuesResponse = await fetch(`${backendBase}/metadata/venues`);
      if (!venuesResponse.ok) {
        throw new Error(`Failed to load venues (${venuesResponse.status})`);
      }
      const venues = (await venuesResponse.json()) as ApiVenue[];
      const allRooms = venues.flatMap((venue) =>
        venue.rooms.map((room) => ({
          ...room,
          venueId: venue.id,
          venueName: venue.name,
        }))
      );

      const knownRooms = allRooms.filter((room) => SUPPORTED_ROOM_IDS.includes(room.id));

      const bookingsResponse = await fetch(`${backendBase}/vapi/tools/bookings`);
      if (!bookingsResponse.ok) {
        throw new Error(`Failed to load bookings (${bookingsResponse.status})`);
      }
      const bookingsPayload = (await bookingsResponse.json()) as { bookings?: ApiBooking[] };
      const now = new Date();

      const allBookings = bookingsPayload.bookings || [];

      const normalizedBookings = allBookings
        .filter((booking) => booking.room_id && SUPPORTED_ROOM_IDS.includes(booking.room_id) && booking.status?.toLowerCase() !== 'cancelled')
        .sort((a, b) => {
          const aStart = a.start_time ? new Date(a.start_time).valueOf() : Number.POSITIVE_INFINITY;
          const bStart = b.start_time ? new Date(b.start_time).valueOf() : Number.POSITIVE_INFINITY;
          return aStart - bStart;
        });

      const bookingsByRoom = new Map<string, ApiBooking>();
      const nowValue = now.valueOf();
      for (const booking of normalizedBookings) {
        const roomId = booking.room_id!;
        if (bookingsByRoom.has(roomId)) continue;
        const endValue = booking.end_time ? new Date(booking.end_time).valueOf() : Number.POSITIVE_INFINITY;
        if (endValue >= nowValue) {
          bookingsByRoom.set(roomId, booking);
        }
      }

      const directory: Record<string, { label: string; venueName: string; capacity: number }> = { ...roomDirectory };
      for (const entry of knownRooms) {
        directory[entry.id] = { label: entry.label, venueName: entry.venueName, capacity: entry.capacity };
      }

      setRoomDirectory((prev) => ({
        ...prev,
        ...directory,
      }));

      setFloorRooms(
        SUPPORTED_ROOM_IDS.map((roomId) => {
          const meta = directory[roomId] ?? { ...ROOM_DEFAULTS[roomId] };
          const booking = bookingsByRoom.get(roomId);
          return {
            id: roomId,
            label: meta?.label ?? ROOM_DEFAULTS[roomId]?.label ?? roomId,
            capacity: meta?.capacity ?? ROOM_DEFAULTS[roomId]?.capacity ?? 0,
            status: booking ? 'booked' : 'available',
            bookingInfo: booking
              ? {
                  customerName: booking.customer?.name ?? null,
                  startTime: booking.start_time ?? null,
                  endTime: booking.end_time ?? null,
                }
              : undefined,
          } satisfies FloorRoom;
        })
      );

      setFloorVenueName('Aurora Hall – Coworking Floor');
      setFloorUpdatedAt(new Date());
      setBookingsList(
        [...allBookings]
          .filter((booking) => booking.room_id && SUPPORTED_ROOM_IDS.includes(booking.room_id))
          .sort((a, b) => {
            const aStart = a.start_time ? new Date(a.start_time).valueOf() : Number.POSITIVE_INFINITY;
            const bStart = b.start_time ? new Date(b.start_time).valueOf() : Number.POSITIVE_INFINITY;
            return bStart - aStart;
          })
      );
    } catch (error) {
      console.error('Failed to load floor data', error);
      setFloorError(error instanceof Error ? error.message : 'Failed to load floor data');
    } finally {
      setFloorLoading(false);
    }
  }, [backendBase, roomDirectory]);

  const pollPayments = useCallback(async () => {
    if (!backendBase) {
      return;
    }
    try {
      console.debug('[payments] polling…');
      const response = await fetch(`${backendBase}/vapi/tools/payments`);
      if (!response.ok) {
        throw new Error(`Failed to load payments (${response.status})`);
      }
      const payload = (await response.json()) as { payments?: ApiPayment[] };
      const payments = payload.payments ?? [];
      console.debug('[payments] received', payments.length, 'records');
      if (processedTransactionsRef.current.size === 0 && payments.length) {
        for (const payment of payments) {
          const transactionId = payment.transaction_id || String(payment.id);
          processedTransactionsRef.current.add(transactionId);
        }
        return;
      }
      for (const payment of payments) {
        if ((payment.status || '').toLowerCase() !== 'succeeded') continue;
        const providerLabel = (payment.provider_hint || payment.provider || '').toLowerCase();
        if (providerLabel !== 'apple_pay') continue;
        const transactionId = payment.transaction_id || String(payment.id);
        if (processedTransactionsRef.current.has(transactionId)) continue;
        processedTransactionsRef.current.add(transactionId);
        console.debug('[payments] new apple pay transaction', transactionId);
        setPaymentToast({
          transactionId,
          amount: payment.amount ?? null,
          currency: payment.currency ?? undefined,
        });
        await playPaymentChime();
        void fetchFloorData();
        break;
      }
    } catch (error) {
      console.warn('Failed to poll payments', error);
    }
  }, [backendBase, fetchFloorData, playPaymentChime]);

  useEffect(() => {
    void fetchFloorData();
    const interval = setInterval(() => {
      void fetchFloorData();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchFloorData]);

  useEffect(() => {
    void pollPayments();
    const interval = setInterval(() => {
      void pollPayments();
    }, 5000);
    return () => clearInterval(interval);
  }, [pollPayments]);

  useEffect(() => {
    const handler = () => {
      void ensureAudioContext();
    };
    window.addEventListener('pointerdown', handler, { once: true });
    window.addEventListener('touchstart', handler, { once: true });
    window.addEventListener('keydown', handler, { once: true });
    return () => {
      window.removeEventListener('pointerdown', handler);
      window.removeEventListener('touchstart', handler);
      window.removeEventListener('keydown', handler);
    };
  }, [ensureAudioContext]);

  useEffect(() => {
    if (!paymentToast) {
      return;
    }
    const timeout = window.setTimeout(() => setPaymentToast(null), 4000);
    return () => window.clearTimeout(timeout);
  }, [paymentToast]);

  const formatTime = useCallback((timestamp: string) => {
    const t0 = new Date(startTimeRef.current).valueOf();
    const t1 = new Date(timestamp).valueOf();
    const delta = t1 - t0;
    const hs = Math.floor(delta / 10) % 100;
    const s = Math.floor(delta / 1000) % 60;
    const m = Math.floor(delta / 60_000) % 60;
    const pad = (n: number) => (n < 10 ? `0${n}` : `${n}`);
    return `${pad(m)}:${pad(s)}.${pad(hs)}`;
  }, []);

  const formatCurrency = useCallback((amount?: number | null, currency?: string | null) => {
    if (amount == null) {
      return currency || '';
    }
    try {
      return new Intl.NumberFormat(undefined, { style: 'currency', currency: currency || 'USD' }).format(amount);
    } catch {
      const rounded = Math.round(amount * 100) / 100;
      return `${rounded.toFixed(2)} ${currency || ''}`.trim();
    }
  }, []);

const connectConversation = useCallback(async () => {
  const vapi = vapiRef.current;
  const wavRecorder = wavRecorderRef.current;
  const wavStreamPlayer = wavStreamPlayerRef.current;

  const assistantId = process.env.REACT_APP_VAPI_ASSISTANT_ID;

  if (!process.env.REACT_APP_VAPI_PUBLIC_KEY) {
    console.error('REACT_APP_VAPI_PUBLIC_KEY is missing');
    return;
  }
  if (!assistantId) {
    console.error('REACT_APP_VAPI_ASSISTANT_ID is missing');
    setRealtimeEvents((prev) => [
      ...prev,
      {
        time: new Date().toISOString(),
        source: 'client',
        event: { type: 'error', message: 'Missing assistant ID' }
      }
    ]);
    return;
  }

  try {
    await ensureAudioContext();
    startTimeRef.current = new Date().toISOString();
    setIsConnected(true);
    setRealtimeEvents([]);
    setItems([]);

    // Prepare audio
    await wavRecorder.begin();
    await wavStreamPlayer.connect();

    vapi.removeAllListeners();

    vapi.on('call-start', () => {
      setRealtimeEvents((prev) => [
        ...prev,
        { time: new Date().toISOString(), source: 'server', event: { type: 'call-start' } }
      ]);
    });

    vapi.on('call-end', () => {
      setRealtimeEvents((prev) => [
        ...prev,
        { time: new Date().toISOString(), source: 'server', event: { type: 'call-end' } }
      ]);
      setIsConnected(false);
    });

    vapi.on('message', (message) => {
      setItems((prev) => {
        const updated = [...prev];
        const lastIndex = updated.length - 1;
        const last = updated[lastIndex];
        const newText = (message.transcript || message.content?.text || '').trim();
        if (!newText) {
          return prev;
        }
        if (last && last.role === message.role) {
          const lastText = (last.transcript || last.content?.text || '').trim();
          if (lastText === newText) {
            return prev;
          }
          updated[lastIndex] = {
            ...last,
            transcript: newText,
            content: { ...last.content, text: newText },
          };
          return updated;
        }
        return [...updated, message];
      });
    });

    vapi.on('error', (err) => console.error('Vapi error:', err));

    console.log('🔗 Starting Vapi call with assistantId:', assistantId);
    await vapi.start(assistantId);
    void fetchFloorData();
  } catch (error) {
    console.error('Failed to start Vapi session', error);
    setIsConnected(false);

    try {
      await wavRecorder.end();
    } catch {}
    try {
      wavStreamPlayer.interrupt();
    } catch {}
    try {
      await vapi.stop();
    } catch {}
  }
}, [ensureAudioContext, fetchFloorData]);


  const disconnectConversation = useCallback(async () => {
    setIsConnected(false);
    setRealtimeEvents([]);
    setItems([]);
    setPaymentToast(null);
    processedTransactionsRef.current.clear();

    try {
      await vapiRef.current.stop();
    } catch {}
    try {
      await wavRecorderRef.current.end();
    } catch {}
    try {
      wavStreamPlayerRef.current.interrupt();
    } catch {}
  }, []);

  const startRecording = async () => {
    setIsRecording(true);
    await wavRecorderRef.current.record();
  };

  const stopRecording = async () => {
    setIsRecording(false);
    await wavRecorderRef.current.pause();
  };

  const changeTurnEndType = async (value: string) => {
    setCanPushToTalk(value === 'none');
  };

  useEffect(() => {
    if (eventsScrollRef.current) {
      const eventsEl = eventsScrollRef.current;
      const scrollHeight = eventsEl.scrollHeight;
      if (scrollHeight !== eventsScrollHeightRef.current) {
        eventsEl.scrollTop = scrollHeight;
        eventsScrollHeightRef.current = scrollHeight;
      }
    }
  }, [realtimeEvents]);

  useEffect(() => {
    const conversationEls = [].slice.call(document.body.querySelectorAll('[data-conversation-content]'));
    for (const el of conversationEls) {
      const conversationEl = el as HTMLDivElement;
      conversationEl.scrollTop = conversationEl.scrollHeight;
    }
  }, [items]);

  useEffect(() => {
    let isLoaded = true;
    const wavRecorder = wavRecorderRef.current;
    const clientCanvas = clientCanvasRef.current;
    let clientCtx: CanvasRenderingContext2D | null = null;
    const wavStreamPlayer = wavStreamPlayerRef.current;
    const serverCanvas = serverCanvasRef.current;
    let serverCtx: CanvasRenderingContext2D | null = null;

    const render = () => {
      if (isLoaded) {
        if (clientCanvas) {
          if (!clientCanvas.width || !clientCanvas.height) {
            clientCanvas.width = clientCanvas.offsetWidth;
            clientCanvas.height = clientCanvas.offsetHeight;
          }
          clientCtx = clientCtx || clientCanvas.getContext('2d');
          if (clientCtx) {
            clientCtx.clearRect(0, 0, clientCanvas.width, clientCanvas.height);
            const result = wavRecorder.recording
              ? wavRecorder.getFrequencies('voice')
              : { values: new Float32Array([0]) };
            WavRenderer.drawBars(clientCanvas, clientCtx, result.values, '#0099ff', 10, 0, 8);
          }
        }
        if (serverCanvas) {
          if (!serverCanvas.width || !serverCanvas.height) {
            serverCanvas.width = serverCanvas.offsetWidth;
            serverCanvas.height = serverCanvas.offsetHeight;
          }
          serverCtx = serverCtx || serverCanvas.getContext('2d');
          if (serverCtx) {
            serverCtx.clearRect(0, 0, serverCanvas.width, serverCanvas.height);
            const result = wavStreamPlayer.analyser
              ? wavStreamPlayer.getFrequencies('voice')
              : { values: new Float32Array([0]) };
            WavRenderer.drawBars(serverCanvas, serverCtx, result.values, '#009900', 10, 0, 8);
          }
        }
        window.requestAnimationFrame(render);
      }
    };
    render();
    return () => {
      isLoaded = false;
    };
  }, []);

return (
  <div data-component="ConsolePage" className="console-page">
    {paymentToast && (
      <div className="payment-toast" role="status" aria-live="polite">
        <div className="payment-toast__icon"> Pay</div>
        <div className="payment-toast__content">
          <div className="payment-toast__title">Payment successful</div>
          <div className="payment-toast__body">
            {formatCurrency(paymentToast.amount ?? undefined, paymentToast.currency ?? undefined)} charged
          </div>
        </div>
      </div>
    )}
    <div className="content-top">
      <div className="content-title">
        <img src={logo} alt="OpenAI logomark" />
        <span>Cerebral Valley coworking</span>
      </div>
    </div>

    {/* Split screen layout */}
    <div className="content-main" style={{ display: 'flex', height: 'calc(100vh - 60px)' }}>
      
      {/* LEFT SIDE - Chat + Events + Controls */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '1rem', borderRight: '1px solid #ddd' }}>
        
        {/* Events & Conversation */}
        <div style={{ flex: 1, overflow: 'auto' }}>
          <div className="content-block events">
            <div className="visualization">
              <div className="visualization-entry client">
                <canvas ref={clientCanvasRef} />
              </div>
              <div className="visualization-entry server">
                <canvas ref={serverCanvasRef} />
              </div>
            </div>
            <div className="content-block-title">events</div>
            <div className="content-block-body" ref={eventsScrollRef}>
              {!realtimeEvents.length && `awaiting connection...`}
              {realtimeEvents.map((realtimeEvent, i) => {
                const event = { ...realtimeEvent.event };
                return (
                  <div className="event" key={i}>
                    <div className="event-timestamp">{formatTime(realtimeEvent.time)}</div>
                    <div className="event-details">
                      <div
                        className="event-summary"
                        onClick={() => {
                          const expanded = { ...expandedEvents };
                          if (expanded[i]) delete expanded[i];
                          else expanded[i] = true;
                          setExpandedEvents(expanded);
                        }}
                      >
                        <div className={`event-source ${event.type === 'error' ? 'error' : realtimeEvent.source}`}>
                          {realtimeEvent.source === 'client' ? <ArrowUp /> : <ArrowDown />}
                          <span>{event.type}</span>
                        </div>
                      </div>
                      {!!expandedEvents[i] && (
                        <div className="event-payload">{JSON.stringify(event, null, 2)}</div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="content-block conversation">
            <div className="content-block-title">conversation</div>
            <div className="content-block-body" data-conversation-content>
              {!items.length && `awaiting connection...`}
{items
  .filter(item => item.transcript?.trim() || item.content?.text?.trim())
  .map((conversationItem, i) => (
    <div className="conversation-item" key={i}>
      <div className={`speaker ${conversationItem.role}`}>
        <div>{conversationItem.role}</div>
        <div
          className="close"
          onClick={() =>
            setItems(prev => prev.filter((_, idx) => idx !== i))
          }
        >
          <X />
        </div>
      </div>
      <div className="speaker-content">
        {conversationItem.transcript || conversationItem.content?.text}
        {conversationItem.audioUrl && <audio src={conversationItem.audioUrl} controls />}
      </div>
    </div>
  ))}

            </div>
          </div>
        </div>

        {/* Control Buttons */}
{/* Control Buttons */}
<div
  className="content-actions"
  style={{
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center', // ✅ Center horizontally
    gap: '1rem',
    marginTop: '1rem',
    padding: '0.5rem 1rem',
    backgroundColor: 'white',
    borderRadius: '8px',
    maxWidth: '80%',          // ✅ Prevent stretching full width
    marginLeft: 'auto',       // ✅ Center the block itself
    marginRight: 'auto',
  }}
>
  <Toggle
    defaultValue={false}
    labels={['manual', 'vad']}
    values={['none', 'server_vad']}
    onChange={(_, value) => changeTurnEndType(value)}
  />

  {isConnected && canPushToTalk && (
    <Button
      label={isRecording ? 'release to send' : 'push to talk'}
      buttonStyle={isRecording ? 'alert' : 'regular'}
      disabled={!isConnected || !canPushToTalk}
      onMouseDown={startRecording}
      onMouseUp={stopRecording}
    />
  )}

  <Button
    label={isConnected ? 'disconnect' : 'connect'}
    iconPosition={isConnected ? 'end' : 'start'}
    icon={isConnected ? X : Zap}
    buttonStyle={isConnected ? 'regular' : 'action'}
    onClick={isConnected ? disconnectConversation : connectConversation}
  />
</div>

      </div>

      {/* RIGHT SIDE - Floor plan & memory */}
      <div className="content-right">
        <div className="content-block floor-plan-card">
          <div className="content-block-body full">
            <FloorPlan
              rooms={floorRooms}
              venueName={floorVenueName}
              isLoading={floorLoading}
              error={floorError}
              lastUpdated={floorUpdatedAt}
              onRefresh={() => {
                void fetchFloorData();
              }}
            />
          </div>
        </div>
        <div className="booking-list">
          <h3>Upcoming bookings</h3>
          {bookingsList.length === 0 ? (
            <div className="booking-empty">No bookings scheduled.</div>
          ) : (
            <ul>
              {bookingsList.map((booking) => {
                const roomMeta = booking.room_id ? roomDirectory[booking.room_id] : undefined;
                const roomLabel = roomMeta?.label ?? booking.room_id ?? 'Unknown room';
                const venueLabel = roomMeta?.venueName ?? booking.venue_id;
                const start = booking.start_time ? new Date(booking.start_time) : null;
                const end = booking.end_time ? new Date(booking.end_time) : null;
                const timeRange = start && end
                  ? `${start.toLocaleString([], {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })} – ${end.toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}`
                  : 'Time not set';
                const customerName = booking.customer?.name ?? 'Guest';
                return (
                  <li key={`${booking.id}-${booking.start_time || 'na'}`}>
                    <div className="booking-row">
                      <span className="booking-customer">{customerName}</span>
                      <div className="booking-info">
                        <span className="booking-room">{roomLabel}</span>
                        <span className="booking-venue">{venueLabel}</span>
                        <span className="booking-time">{timeRange}</span>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </div>
  </div>
);

}
