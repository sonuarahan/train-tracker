"""
Chat Service
Manages multi-room train chat with dynamic room isolation
"""

from typing import Dict, List, Set, Optional
from datetime import datetime
from constants import (
    CHAT_ROOM_PREFIX,
    MAX_MESSAGES_PER_ROOM,
    MAX_CHAT_HISTORY,
    USERNAME_MAX_LENGTH,
    MESSAGE_MAX_LENGTH,
    JOURNEY_CHECK_ENABLED,
)


class ChatMessage:
    """Represents a chat message"""

    def __init__(
        self,
        user: str,
        message: str,
        msg_type: str = "user",
        timestamp: Optional[str] = None,
    ):
        self.user = user[:USERNAME_MAX_LENGTH]
        self.message = message[:MESSAGE_MAX_LENGTH]
        self.type = msg_type
        self.timestamp = timestamp or datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "user": self.user,
            "message": self.message,
            "type": self.type,
            "timestamp": self.timestamp,
        }


class ChatRoom:
    """Represents a train-specific chat room"""

    def __init__(self, train_number: str):
        self.train_number = train_number
        self.room_id = f"{CHAT_ROOM_PREFIX}{train_number}"
        self.messages: List[ChatMessage] = []
        self.active_users: Dict[str, str] = {}  # {session_id: username}
        self.journey_complete: bool = False  # Track if train reached destination
        self.created_at: datetime = datetime.now()

    def add_message(self, message: ChatMessage) -> None:
        """Add a message and maintain size limit"""
        self.messages.append(message)
        if len(self.messages) > MAX_MESSAGES_PER_ROOM:
            self.messages = self.messages[-MAX_MESSAGES_PER_ROOM:]

    def add_user(self, session_id: str, username: str) -> None:
        """Add a user to the room"""
        self.active_users[session_id] = username

    def remove_user(self, session_id: str) -> Optional[str]:
        """Remove a user and return their username"""
        return self.active_users.pop(session_id, None)

    def get_user_count(self) -> int:
        """Get current active user count"""
        return len(self.active_users)

    def get_recent_messages(self, limit: int = MAX_CHAT_HISTORY) -> List[Dict]:
        """Get recent messages as dictionaries"""
        return [msg.to_dict() for msg in self.messages[-limit:]]

    def mark_journey_complete(self) -> None:
        """Mark journey as complete and clear messages"""
        self.journey_complete = True
        self.messages.clear()
        self.active_users.clear()

    def reset_if_complete(self) -> bool:
        """Reset room if journey was marked complete. Returns True if reset occurred."""
        if self.journey_complete:
            self.messages.clear()
            self.active_users.clear()
            self.journey_complete = False
            self.created_at = datetime.now()
            return True
        return False


class ChatService:
    """
    Service for managing multi-train chat rooms with complete isolation.
    Each train has its own room, and passengers can only see messages
    from their specific train.
    """

    def __init__(self):
        self._rooms: Dict[str, ChatRoom] = {}

    def get_or_create_room(self, train_number: str) -> ChatRoom:
        """Get existing room or create new one"""
        room_id = f"{CHAT_ROOM_PREFIX}{train_number}"
        if room_id not in self._rooms:
            self._rooms[room_id] = ChatRoom(train_number)
        return self._rooms[room_id]

    def get_room_id(self, train_number: str) -> str:
        """Generate room ID for a train number"""
        return f"{CHAT_ROOM_PREFIX}{train_number}"

    def add_message(
        self, train_number: str, username: str, message: str, msg_type: str = "user"
    ) -> ChatMessage:
        """Add a message to a specific train's chat room"""
        room = self.get_or_create_room(train_number)
        chat_msg = ChatMessage(username, message, msg_type)
        room.add_message(chat_msg)
        return chat_msg

    def add_system_message(self, train_number: str, message: str) -> ChatMessage:
        """Add a system message to a specific train's chat room"""
        return self.add_message(train_number, "System", message, "system")

    def join_room(
        self, train_number: str, session_id: str, username: str, silent: bool = False
    ) -> Dict[str, any]:
        """
        Handle user joining a chat room.
        Returns join info and system message.
        If silent=True, skip system message (for reconnects).
        """
        room = self.get_or_create_room(train_number)
        room.add_user(session_id, username)

        result = {
            "room_id": room.room_id,
            "user_count": room.get_user_count(),
            "recent_messages": room.get_recent_messages(),
        }

        if not silent:
            system_msg = self.add_system_message(
                train_number, f"{username} joined the chat"
            )
            result["system_message"] = system_msg.to_dict()

        return result

    def leave_room(
        self, train_number: str, session_id: str, silent: bool = False
    ) -> Dict[str, any]:
        """
        Handle user leaving a chat room.
        Returns leave info and system message.
        If silent=True, skip system message (for disconnects).
        """
        room = self.get_or_create_room(train_number)
        username = room.remove_user(session_id)

        result = {
            "room_id": room.room_id,
            "user_count": room.get_user_count(),
            "username": username if username else "Anonymous",
        }

        if username and not silent:
            system_msg = self.add_system_message(
                train_number, f"{username} left the chat"
            )
            result["system_message"] = system_msg.to_dict()

        return result

    def find_user_room(self, session_id: str) -> Optional[str]:
        """Find which train room a user is in"""
        for room_id, room in self._rooms.items():
            if session_id in room.active_users:
                return room.train_number
        return None

    def get_chat_history(
        self, train_number: str, limit: int = MAX_CHAT_HISTORY
    ) -> List[Dict]:
        """Get chat history for a specific train"""
        room = self.get_or_create_room(train_number)
        return room.get_recent_messages(limit)

    def get_user_count(self, train_number: str) -> int:
        """Get active user count for a specific train"""
        room = self.get_or_create_room(train_number)
        return room.get_user_count()

    def check_and_reset_journey(self, train_number: str, train_status: Dict) -> bool:
        """
        Check if train has reached final destination and reset chat if needed.
        Returns True if journey was complete and chat was reset.
        """
        if not JOURNEY_CHECK_ENABLED or not train_status.get("success"):
            return False

        room = self.get_or_create_room(train_number)
        data = train_status.get("data", {})
        stations = data.get("stations", [])

        if not stations:
            return False

        # Check if train reached final station (last station in list)
        last_station = stations[-1]
        actual_arrival = last_station.get("actArr", "--")

        # If last station has actual arrival time (not "--"), journey is complete
        if actual_arrival and actual_arrival != "--":
            if not room.journey_complete:
                room.mark_journey_complete()
                return True

        return False

    def mark_journey_complete(self, train_number: str) -> None:
        """Manually mark a train journey as complete"""
        room = self.get_or_create_room(train_number)
        room.mark_journey_complete()
