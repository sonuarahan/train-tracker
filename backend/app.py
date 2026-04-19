import eventlet

eventlet.monkey_patch()

import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from config import SECRET_KEY
from train_api import search_train, get_live_status, get_pnr_status
from datetime import datetime
import re

# Serve React build from ../frontend/dist
STATIC_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "dist")
)
print(f"Static folder: {STATIC_FOLDER}, exists: {os.path.exists(STATIC_FOLDER)}")

app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path="")
app.config["SECRET_KEY"] = SECRET_KEY
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory chat storage: { train_number: [{ user, message, timestamp }] }
chat_rooms: dict[str, list[dict]] = {}
# Track active users per room: { train_number: set(sid) }
active_users: dict[str, dict[str, str]] = {}

PNR_PATTERN = re.compile(r"^\d{10}$")
TRAIN_NO_PATTERN = re.compile(r"^\d{4,5}$")


# ── REST Endpoints ──────────────────────────────────────────────────────


@app.route("/api/search", methods=["GET"])
def api_search_train():
    query = request.args.get("query", "").strip()
    if not query:
        return jsonify({"success": False, "error": "Query parameter is required"}), 400
    if len(query) > 100:
        return jsonify({"success": False, "error": "Query too long"}), 400
    result = search_train(query)
    return jsonify(result)


@app.route("/api/live-status", methods=["GET"])
def api_live_status():
    train_no = request.args.get("trainNo", "").strip()
    start_date = request.args.get("startDate", "").strip()

    if not train_no or not TRAIN_NO_PATTERN.match(train_no):
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Valid train number (4-5 digits) is required",
                }
            ),
            400,
        )

    if not start_date:
        start_date = datetime.now().strftime("%Y-%m-%d")

    result = get_live_status(train_no, start_date)
    return jsonify(result)


@app.route("/api/pnr-status", methods=["GET"])
def api_pnr_status():
    pnr = request.args.get("pnr", "").strip()
    if not pnr or not PNR_PATTERN.match(pnr):
        return (
            jsonify(
                {"success": False, "error": "Valid 10-digit PNR number is required"}
            ),
            400,
        )
    result = get_pnr_status(pnr)
    return jsonify(result)


@app.route("/api/chat-history/<train_no>", methods=["GET"])
def api_chat_history(train_no):
    if not TRAIN_NO_PATTERN.match(train_no):
        return jsonify({"success": False, "error": "Invalid train number"}), 400
    messages = chat_rooms.get(train_no, [])
    return jsonify({"success": True, "messages": messages[-100:]})  # Last 100 messages


# ── WebSocket Events ────────────────────────────────────────────────────


@socketio.on("join_chat")
def handle_join(data):
    train_no = data.get("trainNo", "")
    username = data.get("username", "Anonymous")[:30]

    if not train_no or not TRAIN_NO_PATTERN.match(train_no):
        emit("error", {"message": "Invalid train number"})
        return

    join_room(train_no)

    if train_no not in active_users:
        active_users[train_no] = {}
    active_users[train_no][request.sid] = username

    if train_no not in chat_rooms:
        chat_rooms[train_no] = []

    system_msg = {
        "user": "System",
        "message": f"{username} joined the chat",
        "timestamp": datetime.now().isoformat(),
        "type": "system",
    }
    chat_rooms[train_no].append(system_msg)

    emit("message", system_msg, to=train_no)
    emit("user_count", {"count": len(active_users[train_no])}, to=train_no)


@socketio.on("send_message")
def handle_message(data):
    train_no = data.get("trainNo", "")
    message = data.get("message", "").strip()[:500]  # Limit message length
    username = data.get("username", "Anonymous")[:30]

    if not train_no or not message:
        return

    if train_no not in chat_rooms:
        chat_rooms[train_no] = []

    msg = {
        "user": username,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "type": "user",
    }
    chat_rooms[train_no].append(msg)

    # Keep only last 500 messages per room
    if len(chat_rooms[train_no]) > 500:
        chat_rooms[train_no] = chat_rooms[train_no][-500:]

    emit("message", msg, to=train_no)


@socketio.on("leave_chat")
def handle_leave(data):
    train_no = data.get("trainNo", "")
    if not train_no:
        return

    leave_room(train_no)

    username = "Anonymous"
    if train_no in active_users and request.sid in active_users[train_no]:
        username = active_users[train_no].pop(request.sid)

    system_msg = {
        "user": "System",
        "message": f"{username} left the chat",
        "timestamp": datetime.now().isoformat(),
        "type": "system",
    }
    if train_no in chat_rooms:
        chat_rooms[train_no].append(system_msg)

    emit("message", system_msg, to=train_no)
    user_count = len(active_users.get(train_no, {}))
    emit("user_count", {"count": user_count}, to=train_no)


@socketio.on("disconnect")
def handle_disconnect():
    for train_no, users in list(active_users.items()):
        if request.sid in users:
            username = users.pop(request.sid)
            leave_room(train_no)
            system_msg = {
                "user": "System",
                "message": f"{username} disconnected",
                "timestamp": datetime.now().isoformat(),
                "type": "system",
            }
            if train_no in chat_rooms:
                chat_rooms[train_no].append(system_msg)
            emit("message", system_msg, to=train_no)
            emit("user_count", {"count": len(users)}, to=train_no)


# Serve React app for all non-API routes (must be last)
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    if path and os.path.exists(os.path.join(STATIC_FOLDER, path)):
        return send_from_directory(STATIC_FOLDER, path)
    index = os.path.join(STATIC_FOLDER, "index.html")
    if os.path.exists(index):
        return send_from_directory(STATIC_FOLDER, "index.html")
    return (
        f"Static folder: {STATIC_FOLDER}, exists: {os.path.exists(STATIC_FOLDER)}, files: {os.listdir(STATIC_FOLDER) if os.path.exists(STATIC_FOLDER) else 'N/A'}",
        404,
    )


if __name__ == "__main__":
    print("🚂 Train Tracker Backend running on http://localhost:5000")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
