"""
Application Constants
Centralized configuration for API endpoints, patterns, and limits
"""

# ── API Configuration ───────────────────────────────────────────────────

# RailYatri Base URLs
RAILYATRI_BASE_URL = "https://www.railyatri.in"
RAILYATRI_SEARCH_URL = "https://search.railyatri.in/v2/mobile/trainsearch.json"

# Request Headers
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

# Timeout Settings (seconds)
API_TIMEOUT = 15
BUILD_ID_TIMEOUT = 10

# ── Validation Patterns ─────────────────────────────────────────────────

PNR_PATTERN = r"^\d{10}$"
TRAIN_NUMBER_PATTERN = r"^\d{4,5}$"
USERNAME_MAX_LENGTH = 30
MESSAGE_MAX_LENGTH = 500
QUERY_MAX_LENGTH = 100

# ── Chat Configuration ──────────────────────────────────────────────────

# Chat limits
MAX_MESSAGES_PER_ROOM = 500
MAX_CHAT_HISTORY = 100

# Room ID format
CHAT_ROOM_PREFIX = "train_"

# Journey tracking - chat persists until train reaches destination
JOURNEY_CHECK_ENABLED = True
JOURNEY_COMPLETE_KEYWORDS = [
    "arrived",
    "reached",
    "destination reached",
    "journey complete",
]

# ── Mock Data ───────────────────────────────────────────────────────────

# Demo PNRs for testing separate chat rooms
# Use these to test multi-train isolation:
#   1234567890 → Train 12951 (Mumbai Rajdhani) → Room: train_12951
#   2234567890 → Train 12301 (Howrah Rajdhani) → Room: train_12301
# Users with PNR 1234567890 will NOT see messages from users with 2234567890
DEMO_PNR_1 = "1234567890"  # → Train 12951 (Mumbai Rajdhani)
DEMO_PNR_2 = "2234567890"  # → Train 12301 (Howrah Rajdhani)

# Mock train data
MOCK_TRAINS = [
    {
        "trainNo": "12951",
        "trainName": "Mumbai Rajdhani Express",
        "fromStn": "MMCT",
        "toStn": "NDLS",
        "departTime": "16:35",
        "arriveTime": "08:35",
    },
    {
        "trainNo": "12952",
        "trainName": "New Delhi Rajdhani Express",
        "fromStn": "NDLS",
        "toStn": "MMCT",
        "departTime": "16:55",
        "arriveTime": "08:15",
    },
    {
        "trainNo": "12301",
        "trainName": "Howrah Rajdhani Express",
        "fromStn": "HWH",
        "toStn": "NDLS",
        "departTime": "16:55",
        "arriveTime": "09:55",
    },
    {
        "trainNo": "12446",
        "trainName": "Uttar Sampark Kranti Express",
        "fromStn": "SVDK",
        "toStn": "NDLS",
        "departTime": "19:50",
        "arriveTime": "11:45",
    },
]

# Mock station data
MOCK_STATIONS = [
    {
        "code": "NDLS",
        "name": "New Delhi",
        "schArr": "08:35",
        "schDep": "--",
        "actArr": "08:50",
        "delay": "15 min late",
        "distance": "1384 km",
        "platform": "5",
    },
    {
        "code": "BRC",
        "name": "Vadodara Junction",
        "schArr": "02:58",
        "schDep": "03:00",
        "actArr": "03:10",
        "delay": "12 min late",
        "distance": "392 km",
        "platform": "3",
    },
]
