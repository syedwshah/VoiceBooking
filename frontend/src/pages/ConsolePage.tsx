import { useEffect, useRef, useCallback, useState } from 'react';
import Vapi from '@vapi-ai/web';
import { WavRecorder, WavStreamPlayer } from '../lib/wavtools/index.js';
import { WavRenderer } from '../utils/wav_renderer';

import { X, Zap, ArrowUp, ArrowDown } from 'react-feather';
import { Button } from '../components/button/Button';
import { Toggle } from '../components/toggle/Toggle';
import { Map } from '../components/Map';

import './ConsolePage.scss';

interface Coordinates {
  lat: number;
  lng: number;
  location?: string;
  temperature?: { value: number; units: string };
  wind_speed?: { value: number; units: string };
}

interface RealtimeEvent {
  time: string;
  source: 'client' | 'server';
  count?: number;
  event: { [key: string]: any };
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
  const [memoryKv, setMemoryKv] = useState<{ [key: string]: any }>({});
  const [coords, setCoords] = useState<Coordinates | null>({ lat: 37.775593, lng: -122.418137 });
  const [marker, setMarker] = useState<Coordinates | null>(null);

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

    vapi.on('message', (message) => setItems((prev) => [...prev, message]));
    vapi.on('error', (err) => console.error('Vapi error:', err));

    // ✅ Correct way: pass assistantId as first argument, not inside an object
    console.log("🔗 Starting Vapi call with assistantId:", assistantId);
    await vapi.start(assistantId);

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
}, []);


  const disconnectConversation = useCallback(async () => {
    setIsConnected(false);
    setRealtimeEvents([]);
    setItems([]);
    setMemoryKv({});
    setCoords({ lat: 37.775593, lng: -122.418137 });
    setMarker(null);

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
    <div data-component="ConsolePage">
      <div className="content-top">
        <div className="content-title">
          <img src="/vapi-logo.svg" alt="Vapi logo" />
          <span>vapi console</span>
        </div>
      </div>
      <div className="content-main">
        <div className="content-logs">
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
              {items.map((conversationItem, i) => (
                <div className="conversation-item" key={i}>
                  <div className={`speaker ${conversationItem.role}`}>
                    <div>{conversationItem.role}</div>
                    <div className="close" onClick={() => setItems((prev) => prev.filter((_, idx) => idx !== i))}>
                      <X />
                    </div>
                  </div>
                  <div className="speaker-content">
                    {conversationItem.transcript || conversationItem.content?.text || '(no text)'}
                    {conversationItem.audioUrl && <audio src={conversationItem.audioUrl} controls />}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="content-actions">
            <Toggle
              defaultValue={false}
              labels={['manual', 'vad']}
              values={['none', 'server_vad']}
              onChange={(_, value) => changeTurnEndType(value)}
            />
            <div className="spacer" />
            {isConnected && canPushToTalk && (
              <Button
                label={isRecording ? 'release to send' : 'push to talk'}
                buttonStyle={isRecording ? 'alert' : 'regular'}
                disabled={!isConnected || !canPushToTalk}
                onMouseDown={startRecording}
                onMouseUp={stopRecording}
              />
            )}
            <div className="spacer" />
            <Button
              label={isConnected ? 'disconnect' : 'connect'}
              iconPosition={isConnected ? 'end' : 'start'}
              icon={isConnected ? X : Zap}
              buttonStyle={isConnected ? 'regular' : 'action'}
              onClick={isConnected ? disconnectConversation : connectConversation}
            />
          </div>
        </div>
        <div className="content-right">
          <div className="content-block map">
            <div className="content-block-title">get_weather()</div>
            <div className="content-block-title bottom">
              {marker?.location || 'not yet retrieved'}
              {!!marker?.temperature && (
                <>
                  <br />🌡️ {marker.temperature.value} {marker.temperature.units}
                </>
              )}
              {!!marker?.wind_speed && (
                <> 🍃 {marker.wind_speed.value} {marker.wind_speed.units}</>
              )}
            </div>
            <div className="content-block-body full">
              {coords && <Map center={[coords.lat, coords.lng]} location={coords.location} />}
            </div>
          </div>
          <div className="content-block kv">
            <div className="content-block-title">set_memory()</div>
            <div className="content-block-body content-kv">
              {JSON.stringify(memoryKv, null, 2)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
