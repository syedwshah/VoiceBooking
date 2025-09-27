# VoiceBooking

VoiceBooking is a hackathon-ready platform that lets you spin up outreach and booking agents quickly. The project pairs a React dashboard with a FastAPI backend, integrates Vapi for telephony, and prepares an OpenAI Realtime bridge for chat-based booking.

## Project Structure

```
VoiceBooking/
├── backend/            # FastAPI app, database models, services, scripts
│   ├── alembic/        # Database migrations
│   └── scripts/        # Helper scripts (e.g. seed data)
├── frontend/           # React + Vite SPA for orchestration UI
├── infra/              # Docker compose and devops helpers
├── .env                # Local secrets (never commit)
├── .env.example        # Template for required configuration
└── README.md
```

### Backend Highlights
- `/api/calls/launch` kicks off Vapi outreach or booking calls.
- `/api/metadata/*` serves venue data and session summaries (backed by Postgres).
- `/api/booking/{session_id}/confirm` persists a booking, records mock payment + door code, and updates the session snapshot.
- `/api/booking/{booking_id}/door-code` regenerates access codes; `/api/booking/recent` lists the latest reservations for the owner dashboard.
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
      - `DATABASE_URL` (default expects Postgres running on `localhost:5432`).

3. **Start Postgres** (Docker recommended)
   ```bash
   cd infra
   docker compose up -d
   ```

4. **Run database migrations**
   ```bash
   cd backend
   source .venv/bin/activate
   alembic upgrade head
   ```

5. **Seed venue + sample bookings** (optional but handy for local testing)
   ```bash
   cd backend
   source .venv/bin/activate
   PYTHONPATH=. python scripts/seed_data.py
   ```

6. **Run the backend**
   ```bash
   cd backend
   uvicorn app.main:app --reload --port 8000
   ```

7. **Run the frontend**
   ```bash
   cd frontend
   npm run dev -- --port 5173
   ```

8. **Open the dashboard**
   - Visit `http://localhost:5173`.
   - Fill the call brief form, launch an outreach or booking scenario, and watch the status and summaries update.

## Next Steps

- Connect the Vapi webhook handler to enrich transcripts, drive real summary generation, and stream booking/payment/door events back to the UI.
- Wire up the OpenAI Realtime WebSocket bridge for the chat booking assistant.
- Add authentication and persistence if you move beyond a single-user demo.
- Replace the mock key issuance + payment integrations with real services (smart locks, MCP payments) and expose invoices.
- Expand the schema/migrations to cover additional booking lifecycle events (cancellations, refunds, audit logs) when you progress beyond the prototype.

## Manual Test Checklist

1. **Spin up the stack** using the steps above (Docker Postgres, migrations, seed, backend, frontend).
2. **Launch an outreach call** from the dashboard to verify Vapi connectivity (mock updates currently streamed via SSE heartbeat).
3. **Trigger a booking** by submitting the call brief in booking mode; inspect `GET /api/booking/recent` to confirm the booking, payment entry, and door access code were recorded.
4. **Regenerate access**: call `POST /api/booking/{booking_id}/door-code` to ensure mock access codes rotate and the session store reflects the change.
5. **Check seed data** via psql or the `/api/metadata/venues` endpoint to validate venue/room ingestion.

## Team Setup Notes

For teammates setting up locally:

1. `git pull` the latest changes.
2. Copy `.env.example` → `.env` and fill credentials (especially `DATABASE_URL` if Postgres runs elsewhere).
3. In `infra/`, run `docker compose up -d` to start the Postgres container (`voicebooking` DB with `postgres/postgres`).
4. In `backend/`, create/activate the virtualenv and install requirements.
5. Run migrations with `alembic upgrade head` (ensure `.venv` is activated so env vars load).
6. Seed reference data with `PYTHONPATH=. python scripts/seed_data.py` (optional but recommended for the demo flow).
7. Start backend/front-end dev servers as needed.

## Tooling & Scripts

| Purpose        | Command                              |
| -------------- | ------------------------------------- |
| Backend tests  | `cd backend && python3 -m pytest`     |
| Frontend tests | `cd frontend && npm run test` (TBD)   |
| Lint frontend  | `cd frontend && npm run lint`         |

Feel free to extend the plan, plug into real data sources, and deploy the two services wherever you demo.
