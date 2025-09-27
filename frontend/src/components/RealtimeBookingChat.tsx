import { useEffect, useState } from 'react';

interface Message {
  author: 'user' | 'assistant';
  text: string;
}

interface RealtimeBookingChatProps {
  sessionId: string | null;
}

export function RealtimeBookingChat({ sessionId }: RealtimeBookingChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');

  useEffect(() => {
    setMessages([]);
  }, [sessionId]);

  function handleSend() {
    if (!input.trim()) return;
    setMessages((prev) => [...prev, { author: 'user', text: input }]);
    setInput('');
    // TODO: connect to websocket bridge
  }

  return (
    <section className="card">
      <h3>Realtime Booking Assistant</h3>
      <div className="chat-window">
        {messages.length === 0 ? <p className="muted">Start the conversation to plan a booking.</p> : null}
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.author}`}>
            <span>{message.text}</span>
          </div>
        ))}
      </div>
      <div className="chat-input">
        <input value={input} onChange={(event) => setInput(event.target.value)} placeholder="Ask the assistant..." />
        <button type="button" onClick={handleSend}>
          Send
        </button>
      </div>
    </section>
  );
}
