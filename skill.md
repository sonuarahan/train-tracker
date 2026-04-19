# Running Train Help — AI Agent Skill File

> **Purpose:** This file provides full context about the project so that any AI agent can understand the codebase, architecture, conventions, and constraints before making changes.

---

## Project Overview

**Running Train Help** is a web app for tracking Indian railway trains in real-time and chatting with co-passengers. It has two main features:

1. **Live Train Status** — Search by train number/name, view real-time running status with station-wise delays.
2. **Co-Passenger Chat** — PNR-gated WebSocket chat rooms where passengers on the same train can communicate.

**Live URL:** Deployed on Render.com (free tier).

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | React + Vite | React 19.2, Vite 8.0 |
| Backend | Flask + Flask-SocketIO | Flask 3.1, Flask-SocketIO 5.5 |
| WebSocket | Socket.IO (eventlet) | socket.io-client 4.8 |
| Data Source | RailYatri (scraping, no API key) | Next.js SSR endpoints |
| Deployment | Render.com | Python runtime, gunicorn+eventlet |
| Python | 3.12 | Pinned in `.python-version` |
| Node | 20.x | Used only for build step |

---

## File Structure

```
train-tracker/
├── .gitignore
├── .python-version              # "3.12.0" — required for eventlet compatibility
├── build.sh                     # Render build: npm install + vite build + pip install
├── render.yaml                  # Render IaC config
├── requirements.txt             # Root: just "-r backend/requirements.txt"
├── PITCH.md                     # Product pitch document
│
├── backend/
│   ├── app.py                   # Flask server: REST API + WebSocket + SPA serving
│   ├── config.py                # Loads SECRET_KEY from .env
│   ├── train_api.py             # RailYatri API client + mock fallback data
│   ├── requirements.txt         # Python deps
│   ├── .env                     # Local env (gitignored)
│   └── .env.example             # Template: SECRET_KEY=your-secret-key-...
│
└── frontend/
    ├── index.html               # Title: "Running Train Help"
    ├── package.json             # React, socket.io-client
    ├── vite.config.js           # Dev port 5175, proxy /api + /socket.io → localhost:5000
    └── src/
        ├── main.jsx             # React entry: mounts <App /> into #root
        ├── App.jsx              # Tab nav: "Train Status" | "Co-Passenger Chat"
        ├── App.css              # Header, tabs, footer, layout
        ├── index.css            # Empty
        ├── assets/              # train-bg.jpg, chat-bg-new.jpg, etc.
        └── components/
            ├── TrainStatus.jsx  # Search + live status display
            ├── TrainStatus.css  # Glassmorphism, blurred bg, station table
            ├── CoPassengerChat.jsx  # PNR verify → join chat room
            └── CoPassengerChat.css  # Chat bubbles, message list, input bar
```

---

## Backend Architecture

### Entry Point: `backend/app.py`

- **MUST** start with `import eventlet; eventlet.monkey_patch()` before all other imports.
- Flask app serves React build from `../frontend/dist` via catch-all route.
- `STATIC_FOLDER` is resolved via `os.path.abspath(os.path.join(__file__, '..', '..', 'frontend', 'dist'))`.
- CORS and SocketIO both allow all origins (`*`).

### REST API Endpoints

| Method | Endpoint | Params | Response |
|--------|----------|--------|----------|
| GET | `/api/search` | `?query=` (required, max 100 chars) | `{ success, data: [{ trainNo, trainName, fromStn, toStn, departTime, arriveTime }] }` |
| GET | `/api/live-status` | `?trainNo=` (4-5 digits), `?startDate=YYYY-MM-DD` (optional) | `{ success, data: { trainNo, trainName, fromStn, toStn, currentStation, delay, lastUpdated, journeyDate, stations: [{ code, name, schArr, schDep, actArr, delay, platform }] } }` |
| GET | `/api/pnr-status` | `?pnr=` (exactly 10 digits) | `{ success, data: { pnrNumber, trainNo, trainName, ... passengers } }` |
| GET | `/api/chat-history/<train_no>` | Path param (4-5 digits) | `{ success, messages: [...last 100] }` |

### WebSocket Events (Socket.IO)

**Client → Server:**
| Event | Payload |
|-------|---------|
| `join_chat` | `{ trainNo: string, username: string }` |
| `send_message` | `{ trainNo: string, message: string, username: string }` |
| `leave_chat` | `{ trainNo: string }` |

**Server → Client:**
| Event | Payload |
|-------|---------|
| `message` | `{ user, message, timestamp (ISO), type: "user"|"system" }` |
| `user_count` | `{ count: number }` |
| `error` | `{ message: string }` |

### Validation Patterns
- Train number: `^\d{4,5}$`
- PNR: `^\d{10}$`
- Message length: max 500 chars
- Username: max 30 chars
- Chat history: returns last 100 messages
- Room messages: capped at 500 per train

### Data Source: `backend/train_api.py`

**RailYatri endpoints (no API key needed):**
- **Search:** `https://search.railyatri.in/v2/mobile/trainsearch.json?q={query}`
- **Live status:** `https://www.railyatri.in/_next/data/{buildId}/live-train-status/{trainNo}.json`
- **BuildId:** Scraped from `https://www.railyatri.in/pnr-status` HTML, regex: `"buildId"\s*:\s*"([^"]+)"`
- BuildId is cached in `_build_id_cache` dict, reset on request failure.

**Fallback:** If RailYatri fails, mock data is returned from `MOCK_TRAINS` (12 trains) and `MOCK_STATIONS` (5 stations).

**PNR status:** Always returns mock data (RailYatri PNR API is not publicly available).

**Headers sent to RailYatri:**
```python
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}
```

---

## Frontend Architecture

### Key Constants
- `API_BASE = "/api"` — used in both TrainStatus.jsx and CoPassengerChat.jsx
- `SOCKET_URL = window.location.origin` — used in CoPassengerChat.jsx
- These are **relative URLs**. In dev, Vite proxies them to `localhost:5000`. In production, Flask serves everything.

### TrainStatus.jsx Flow
1. User types query → if it matches `^\d{4,5}$`, fetch live status directly
2. Otherwise, search via `/api/search` → display clickable train cards
3. Clicking a card → fetch `/api/live-status` → display current station, delay, station table

### CoPassengerChat.jsx Flow
1. User enters name + PNR → verify via `/api/pnr-status`
2. Load chat history via `/api/chat-history/{trainNo}`
3. Connect Socket.IO → emit `join_chat` → receive `message` and `user_count` events
4. Send messages via `send_message` event
5. Leave via `leave_chat` event → disconnect socket

### Styling Conventions
- **Color scheme:** Indigo/navy `#1a237e` primary, `#3949ab` secondary
- **Glassmorphism:** `background: rgba(255,255,255,0.92)`, `backdrop-filter: blur(10px)`, `border-radius: 16px`
- **Background images:** Full-screen with `filter: blur(2px) brightness(0.7)` overlay
- **Animations:** `fadeIn` (slide up + fade), `slideIn` (for chat messages)
- **Responsive breakpoint:** 600px

---

## Development Setup

### Start Backend
```bash
cd backend
python app.py
# Runs on http://localhost:5000
```

### Start Frontend
```bash
cd frontend
npm run dev
# Runs on http://localhost:5175
# Proxies /api and /socket.io to localhost:5000
```

### Build Frontend
```bash
cd frontend
npm run build
# Output: frontend/dist/
```

---

## Deployment (Render.com)

- **Runtime:** Python 3.12 (pinned via `.python-version`)
- **Build command:** `bash build.sh` — installs Node deps, builds React, installs Python deps
- **Start command:** `cd backend && gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app`
- **Single service:** Flask serves both API and React SPA from `frontend/dist/`
- **Env vars on Render:** `SECRET_KEY` (auto-generated), `PYTHON_VERSION=3.12.0`, `NODE_VERSION=20.11.0`

### Deploy Process
1. Push to `main` branch on GitHub
2. Render auto-detects push and rebuilds
3. `build.sh` runs → `gunicorn` starts → site is live

---

## Important Constraints & Gotchas

1. **eventlet.monkey_patch()** MUST be the first import in `app.py` — before Flask, requests, or anything else. Otherwise WebSocket breaks on Render.
2. **Python 3.12 only** — eventlet is not compatible with Python 3.14+. Pinned in `.python-version`.
3. **RailYatri buildId changes** — It rotates when RailYatri redeploys. The cache auto-resets on failure, so it self-heals.
4. **No real PNR API** — PNR status is always mock. Any PNR "verification" just returns fake data for train 12951.
5. **Chat is in-memory** — All messages are lost when the server restarts. No database.
6. **Free tier limits** — Render free tier spins down after 15 min of inactivity. First request after sleep takes ~30 seconds.
7. **CORS is open** (`*`) — acceptable for this project but tighten for production.
8. **Single gunicorn worker** — Required for Socket.IO with eventlet. Do not increase workers.

---

## How to Add New Features

### Adding a new API endpoint:
1. Add the route in `backend/app.py` (follow existing pattern with validation)
2. Add the data-fetching logic in `backend/train_api.py` (with mock fallback)
3. Call it from the frontend component using `fetch(\`${API_BASE}/your-endpoint\`)`

### Adding a new frontend page/tab:
1. Create `frontend/src/components/NewFeature.jsx` and `NewFeature.css`
2. Import it in `App.jsx` and add a new tab entry
3. Follow existing styling conventions (glassmorphism, indigo theme)

### Adding a new WebSocket event:
1. Add `@socketio.on("event_name")` handler in `app.py`
2. Emit from frontend via `socketRef.current.emit("event_name", payload)`
3. Listen via `socketRef.current.on("event_name", callback)`

### Deploying changes:
```bash
cd frontend && npm run build && cd ..
git add -A && git commit -m "description" && git push
# Render auto-deploys from main branch
```

---

## Data Flow Diagram

```
User Browser
     │
     ├─── HTTP GET /api/search ──────────► Flask ──► RailYatri search API ──► JSON response
     ├─── HTTP GET /api/live-status ─────► Flask ──► RailYatri _next/data API ──► JSON response
     ├─── HTTP GET /api/pnr-status ──────► Flask ──► Mock data (always)
     ├─── HTTP GET /api/chat-history ────► Flask ──► In-memory chat_rooms dict
     ├─── WebSocket /socket.io ──────────► Flask-SocketIO ──► Room-based broadcast
     └─── HTTP GET / (any non-API path) ─► Flask ──► frontend/dist/index.html (React SPA)
```
