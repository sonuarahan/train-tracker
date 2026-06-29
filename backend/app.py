import eventlet

eventlet.monkey_patch()

import os
import re
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room

# Import configuration
from config import SECRET_KEY

# Import services (Dependency Injection)
from train_api import search_train, get_live_status
from pnr_service import PNRService
from chat_service import ChatService

# Import constants
from constants import (
    PNR_PATTERN,
    TRAIN_NUMBER_PATTERN,
    USERNAME_MAX_LENGTH,
    MESSAGE_MAX_LENGTH,
)

# Serve React build from ../frontend/dist
STATIC_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "dist")
)
print(f"Static folder: {STATIC_FOLDER}, exists: {os.path.exists(STATIC_FOLDER)}")

# Initialize Flask app
app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path="")
app.config["SECRET_KEY"] = SECRET_KEY
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize services (Dependency Injection)
pnr_service = PNRService()
chat_service = ChatService()

# Compile regex patterns
PNR_REGEX = re.compile(PNR_PATTERN)
TRAIN_NO_REGEX = re.compile(TRAIN_NUMBER_PATTERN)


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
    """Get live train running status"""
    from datetime import datetime

    train_no = request.args.get("trainNo", "").strip()
    start_date = request.args.get("startDate", "").strip()

    if not train_no or not TRAIN_NO_REGEX.match(train_no):
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
    """
    Get PNR status and extract train information.
    This endpoint now supports dynamic train extraction for chat routing.
    """
    pnr = request.args.get("pnr", "").strip()

    if not pnr or not PNR_REGEX.match(pnr):
        return (
            jsonify(
                {"success": False, "error": "Valid 10-digit PNR number is required"}
            ),
            400,
        )

    # Use PNR service to fetch status (tries API first, falls back to mock)
    result = pnr_service.get_pnr_status(pnr, use_api=True)
    return jsonify(result)


@app.route("/api/pnr-train-info", methods=["GET"])
def api_pnr_train_info():
    """
    Extract train number and name from PNR.
    Used by frontend to determine which chat room to join.
    """
    pnr = request.args.get("pnr", "").strip()

    if not pnr or not PNR_REGEX.match(pnr):
        return (
            jsonify(
                {"success": False, "error": "Valid 10-digit PNR number is required"}
            ),
            400,
        )

    # Get PNR status
    pnr_result = pnr_service.get_pnr_status(pnr, use_api=True)

    if not pnr_result.get("success"):
        return jsonify(pnr_result), 400

    # Extract train info
    train_info = pnr_service.extract_train_info(pnr_result)

    if not train_info:
        return (
            jsonify({"success": False, "error": "Could not extract train information"}),
            400,
        )

    return jsonify({"success": True, "data": train_info})


@app.route("/api/chat-history/<train_no>", methods=["GET"])
def api_chat_history(train_no):
    """Get chat history for a specific train"""
    if not TRAIN_NO_REGEX.match(train_no):
        return jsonify({"success": False, "error": "Invalid train number"}), 400

    messages = chat_service.get_chat_history(train_no)
    return jsonify({"success": True, "messages": messages})


@app.route("/api/check-journey/<train_no>", methods=["GET"])
def api_check_journey(train_no):
    """
    Check if train has reached destination and reset chat if needed.
    Returns journey status and whether chat was reset.
    """
    from datetime import datetime

    if not TRAIN_NO_REGEX.match(train_no):
        return jsonify({"success": False, "error": "Invalid train number"}), 400

    start_date = request.args.get("startDate", "").strip()
    if not start_date:
        start_date = datetime.now().strftime("%Y-%m-%d")

    # Get train status
    train_status = get_live_status(train_no, start_date)

    # Check and reset if journey complete
    was_reset = chat_service.check_and_reset_journey(train_no, train_status)

    return jsonify(
        {
            "success": True,
            "journey_complete": was_reset,
            "train_status": train_status.get("success", False),
            "message": (
                "Chat reset due to journey completion"
                if was_reset
                else "Journey ongoing"
            ),
        }
    )


# ── WebSocket Events ────────────────────────────────────────────────────


@socketio.on("join_chat")
def handle_join(data):
    """
    Handle user joining a train-specific chat room.
    Each train has its own isolated room.
    Chat persists across page refresh unless train reached destination.
    """
    train_no = data.get("trainNo", "")
    username = data.get("username", "Anonymous")[:USERNAME_MAX_LENGTH]
    pnr = data.get("pnr", "")  # Optional: for validation
    start_date = data.get("startDate", "")  # Optional: for journey tracking
    is_reconnect = data.get("isReconnect", False)  # True if page refresh

    # Validate train number
    if not train_no or not TRAIN_NO_REGEX.match(train_no):
        emit("error", {"message": "Invalid train number"})
        return

    # Optional PNR validation for security
    if pnr and PNR_REGEX.match(pnr):
        # Verify PNR belongs to this train
        pnr_result = pnr_service.get_pnr_status(pnr, use_api=False)
        if pnr_result.get("success"):
            pnr_train = pnr_result["data"].get("trainNo", "")
            if pnr_train != train_no:
                emit("error", {"message": "PNR does not match this train"})
                return

    # Check if train journey is complete and reset chat if needed
    if start_date:
        from datetime import datetime

        if not start_date:
            start_date = datetime.now().strftime("%Y-%m-%d")
        train_status = get_live_status(train_no, start_date)
        was_reset = chat_service.check_and_reset_journey(train_no, train_status)
        if was_reset:
            # Notify that chat was reset due to journey completion
            emit(
                "journey_complete",
                {"message": "Train reached destination. Chat has been reset."},
            )

    # Get room ID and join
    room_id = chat_service.get_room_id(train_no)
    join_room(room_id)

    # Register user in chat service (silent if reconnect)
    join_info = chat_service.join_room(
        train_no, request.sid, username, silent=is_reconnect
    )

    # Emit system message to room only if not reconnect
    if "system_message" in join_info:
        emit("message", join_info["system_message"], to=room_id)

    # Send user count update
    emit("user_count", {"count": join_info["user_count"]}, to=room_id)

    # Send recent messages to joining user (persisted from before refresh)
    emit("chat_history", {"messages": join_info["recent_messages"]})


@socketio.on("send_message")
def handle_message(data):
    """
    Handle sending a message to a train-specific chat room.
    Messages are isolated per train - no cross-train visibility.
    """
    train_no = data.get("trainNo", "")
    message = data.get("message", "").strip()[:MESSAGE_MAX_LENGTH]
    username = data.get("username", "Anonymous")[:USERNAME_MAX_LENGTH]

    # Validate inputs
    if not train_no or not message:
        return

    if not TRAIN_NO_REGEX.match(train_no):
        emit("error", {"message": "Invalid train number"})
        return

    # Add message to chat service
    chat_msg = chat_service.add_message(train_no, username, message, "user")

    # Get room ID
    room_id = chat_service.get_room_id(train_no)

    # Broadcast message to all users in this train's room only
    emit("message", chat_msg.to_dict(), to=room_id)


@socketio.on("leave_chat")
def handle_leave(data):
    """Handle user leaving a train-specific chat room"""
    train_no = data.get("trainNo", "")
    if not train_no or not TRAIN_NO_REGEX.match(train_no):
        return

    # Get room ID
    room_id = chat_service.get_room_id(train_no)
    leave_room(room_id)

    # Remove user from chat service
    leave_info = chat_service.leave_room(train_no, request.sid)

    # Emit system message if user was found
    if "system_message" in leave_info:
        emit("message", leave_info["system_message"], to=room_id)

    # Send updated user count
    emit("user_count", {"count": leave_info["user_count"]}, to=room_id)


@socketio.on("disconnect")
def handle_disconnect():
    """
    Handle user disconnection.
    Clean up user count but don't send messages (avoid spam on refresh).
    """
    # Find which train room this user was in
    train_no = chat_service.find_user_room(request.sid)

    if train_no:
        room_id = chat_service.get_room_id(train_no)
        leave_room(room_id)

        # Remove user silently (no system messages)
        leave_info = chat_service.leave_room(train_no, request.sid, silent=True)

        # Update user count without announcement
        emit("user_count", {"count": leave_info["user_count"]}, to=room_id)


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
