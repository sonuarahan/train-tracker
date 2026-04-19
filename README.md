# 🚂 Indian Rail Tracker

A full-stack web application to check **live Indian train running status** and **chat with co-passengers** in real-time.

## Features

### 1. Live Train Status
- Search trains by **train number** or **train name**
- View real-time running status with delay information
- Station-wise arrival/departure details with platform numbers

### 2. Co-Passenger Chat
- Enter your **10-digit PNR number** to join a chat room
- Chat with other passengers on the **same train** in real-time
- See how many passengers are online
- WebSocket-based instant messaging

## Tech Stack

| Layer    | Technology                          |
|----------|-------------------------------------|
| Frontend | React + Vite                        |
| Backend  | Python Flask + Flask-SocketIO       |
| API      | RapidAPI (IRCTC) / Mock Data        |
| Realtime | WebSocket (Socket.IO)               |

## Setup & Run

### Prerequisites
- Python 3.9+
- Node.js 18+
- (Optional) RapidAPI key for real train data

### 1. Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Copy and configure the environment file
copy .env.example .env
# Edit .env and add your RapidAPI key (optional - mock data works without it)

python app.py
```

Backend runs on **http://localhost:5000**

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on **http://localhost:5173**

### 3. Get Real Train Data (Optional)

The app works with **mock data** out of the box. For real Indian Railway data:

1. Go to [RapidAPI](https://rapidapi.com)
2. Search for **"IRCTC"** or **"Indian Railway"** APIs
3. Subscribe to a free plan
4. Copy your API key to `backend/.env`

## Project Structure

```
train-tracker/
├── backend/
│   ├── app.py              # Flask server + WebSocket handlers
│   ├── train_api.py         # Train API integration + mock data
│   ├── config.py            # Configuration
│   ├── requirements.txt     # Python dependencies
│   └── .env.example         # Environment variables template
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main app with tab navigation
│   │   ├── App.css          # Global styles
│   │   └── components/
│   │       ├── TrainStatus.jsx      # Train search & live status
│   │       ├── TrainStatus.css
│   │       ├── CoPassengerChat.jsx  # PNR-based chat room
│   │       └── CoPassengerChat.css
│   └── package.json
└── README.md
```

## Screenshots

### Train Status
- Enter train number like `12951` for Mumbai Rajdhani Express
- Or search by name like `Rajdhani`

### Co-Passenger Chat
- Enter your name and PNR (use any 10-digit number for demo: `1234567890`)
- Chat in real-time with others on the same train

## API Endpoints

| Method | Endpoint                    | Description            |
|--------|-----------------------------|------------------------|
| GET    | `/api/search?query=`        | Search trains          |
| GET    | `/api/live-status?trainNo=` | Live running status    |
| GET    | `/api/pnr-status?pnr=`     | PNR status             |
| GET    | `/api/chat-history/<no>`    | Chat message history   |

### WebSocket Events

| Event          | Direction | Description            |
|----------------|-----------|------------------------|
| `join_chat`    | Client→Server | Join train chat room |
| `send_message` | Client→Server | Send a message       |
| `leave_chat`   | Client→Server | Leave chat room      |
| `message`      | Server→Client | New message          |
| `user_count`   | Server→Client | Online user count    |
