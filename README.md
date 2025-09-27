# VoiceBooking

VoiceBooking is a hackathon-ready platform that lets you spin up outreach and booking agents quickly. The project pairs a React dashboard with a FastAPI backend, integrates Vapi for telephony, and prepares an OpenAI Realtime bridge for chat-based booking.

## Project Structure

```
VoiceBooking/
├── backend/            # FastAPI app, services, session store, venue data
├── frontend/           # React + Vite SPA for orchestration UI
├── infra/              # Deployment and devops helpers (placeholder)
├── .env                # Local secrets (never commit)
├── .env.example        # Template for required configuration
└── README.md
```

### Backend Highlights
- `/api/calls/launch` kicks off Vapi outreach or booking calls.
- `/api/metadata/*` serves venue data and session summaries.
- `/api/booking/*` manages booking confirmation and key issuance.
- `/api/events/{session}` exposes SSE stream for live status (stub).

### Frontend Highlights
- `CallBriefForm` captures the intent + context for each call.
- `CallDashboard` displays status and streaming transcript messages.
- `BookingModeToggle` lets users switch between Vapi voice and Realtime chat booking flows.
- `RealtimeBookingChat` stands ready for the OpenAI WebSocket integration.

## Getting Started

1. **Clone & install**
   ```bash
   # Backend
   cd backend
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt

   # Frontend
   cd ../frontend
   npm install
   ```

2. **Environment variables**
   - Copy `.env.example` to `.env` at the repository root and fill in:
     - `VAPI_PRIVATE_KEY`, `VAPI_PUBLIC_KEY`, optional team IDs.
     - `OPENAI_API_KEY`, `OPENAI_REALTIME_MODEL`.
     - `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`.
     - `CALLBACK_SECRET` for authenticating Vapi webhooks (optional for local dev).

3. **Run the backend**
   ```bash
   cd backend
   uvicorn app.main:app --reload --port 8000
   ```

4. **Run the frontend**
   ```bash
   cd frontend
   npm run dev -- --port 5173
   ```

5. **Open the dashboard**
   - Visit `http://localhost:5173`.
   - Fill the call brief form, launch an outreach or booking scenario, and watch the status and summaries update.

## Next Steps

- Connect the Vapi webhook handler to enrich transcripts and drive real summary generation via OpenAI Responses.
- Wire up the OpenAI Realtime WebSocket bridge for the chat booking assistant.
- Add authentication and persistence if you move beyond a single-user demo.
- Replace the mock key issuance service with a real smart-lock integration or MCP payment gate.

## Tooling & Scripts

| Purpose        | Command                              |
| -------------- | ------------------------------------- |
| Backend tests  | `cd backend && python3 -m pytest`     |
| Frontend tests | `cd frontend && npm run test` (TBD)   |
| Lint frontend  | `cd frontend && npm run lint`         |

Feel free to extend the plan, plug into real data sources, and deploy the two services wherever you demo.
