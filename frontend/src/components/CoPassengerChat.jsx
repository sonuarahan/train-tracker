import { useState, useEffect, useRef } from "react"
import { io } from "socket.io-client"
import "./CoPassengerChat.css"

const API_BASE = "/api"
const SOCKET_URL = window.location.origin

function CoPassengerChat() {
  const [pnr, setPnr] = useState("")
  const [username, setUsername] = useState("")
  const [pnrData, setPnrData] = useState(null)
  const [joined, setJoined] = useState(false)
  const [messages, setMessages] = useState([])
  const [newMessage, setNewMessage] = useState("")
  const [userCount, setUserCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const socketRef = useRef(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect()
      }
    }
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleVerifyPnr = async (e) => {
    e.preventDefault()
    if (!pnr.trim() || !username.trim()) return

    setLoading(true)
    setError("")

    try {
      const res = await fetch(`${API_BASE}/pnr-status?pnr=${encodeURIComponent(pnr.trim())}`)
      const data = await res.json()

      if (data.success) {
        setPnrData(data.data)
        // Load chat history
        const histRes = await fetch(`${API_BASE}/chat-history/${data.data.trainNo}`)
        const histData = await histRes.json()
        if (histData.success) {
          setMessages(histData.messages)
        }
        // Connect to WebSocket
        joinChat(data.data.trainNo)
      } else {
        setError(data.error || "Failed to verify PNR")
      }
    } catch {
      setError("Could not connect to server. Make sure the backend is running.")
    } finally {
      setLoading(false)
    }
  }

  const joinChat = (trainNo) => {
    const socket = io(SOCKET_URL, {
      transports: ["websocket", "polling"],
    })

    socket.on("connect", () => {
      socket.emit("join_chat", {
        trainNo,
        username: username.trim(),
      })
      setJoined(true)
    })

    socket.on("message", (msg) => {
      setMessages((prev) => [...prev, msg])
    })

    socket.on("user_count", (data) => {
      setUserCount(data.count)
    })

    socket.on("error", (data) => {
      setError(data.message)
    })

    socket.on("disconnect", () => {
      setJoined(false)
    })

    socketRef.current = socket
  }

  const handleSendMessage = (e) => {
    e.preventDefault()
    if (!newMessage.trim() || !socketRef.current) return

    socketRef.current.emit("send_message", {
      trainNo: pnrData.trainNo,
      message: newMessage.trim(),
      username: username.trim(),
    })

    setNewMessage("")
  }

  const handleLeaveChat = () => {
    if (socketRef.current && pnrData) {
      socketRef.current.emit("leave_chat", { trainNo: pnrData.trainNo })
      socketRef.current.disconnect()
      socketRef.current = null
    }
    setJoined(false)
    setPnrData(null)
    setMessages([])
    setUserCount(0)
  }

  const formatTime = (timestamp) => {
    try {
      return new Date(timestamp).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })
    } catch {
      return ""
    }
  }

  if (!joined) {
    return (
      <div className="chat-container">
        <div className="pnr-section">
          <h2>Co-Passenger Chat</h2>
          <p className="chat-description">
            Chat with fellow passengers on your train! Enter your PNR number to
            join the chat room for your train.
          </p>

          <form onSubmit={handleVerifyPnr} className="pnr-form">
            <div className="form-group">
              <label htmlFor="username">Your Name</label>
              <input
                id="username"
                type="text"
                placeholder="Enter your name"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="form-input"
                maxLength={30}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="pnr">PNR Number</label>
              <input
                id="pnr"
                type="text"
                placeholder="Enter 10-digit PNR number"
                value={pnr}
                onChange={(e) => setPnr(e.target.value.replace(/\D/g, ""))}
                className="form-input"
                maxLength={10}
                required
              />
            </div>
            <button type="submit" className="join-btn" disabled={loading || pnr.length !== 10 || !username.trim()}>
              {loading ? "Verifying PNR..." : "Verify & Join Chat"}
            </button>
          </form>

          {error && <div className="error-msg">{error}</div>}

          <div className="chat-info">
            <h4>How it works:</h4>
            <ol>
              <li>Enter your name and 10-digit PNR number</li>
              <li>We verify your PNR and find your train</li>
              <li>You join a chat room with other passengers on the same train</li>
              <li>Chat about delays, platform info, food, and more!</li>
            </ol>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="chat-container">
      <div className="chat-room-wrapper">
      <div className="chat-header">
        <div className="chat-header-info">
          <h3>
            {pnrData.trainName} ({pnrData.trainNo})
          </h3>
          <span className="route-badge">
            {pnrData.fromStn} → {pnrData.toStn}
          </span>
        </div>
        <div className="chat-header-actions">
          <span className="user-count">{userCount} online</span>
          <button onClick={handleLeaveChat} className="leave-btn">
            Leave Chat
          </button>
        </div>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="empty-chat">
            <p>No messages yet. Start the conversation!</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`message ${msg.type === "system" ? "system-msg" : ""} ${
              msg.user === username.trim() ? "own-msg" : ""
            }`}
          >
            {msg.type === "system" ? (
              <span className="system-text">{msg.message}</span>
            ) : (
              <>
                <div className="msg-header">
                  <span className="msg-user">{msg.user}</span>
                  <span className="msg-time">{formatTime(msg.timestamp)}</span>
                </div>
                <div className="msg-body">{msg.message}</div>
              </>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSendMessage} className="chat-input-form">
        <input
          type="text"
          placeholder="Type a message..."
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          className="chat-input"
          maxLength={500}
          autoFocus
        />
        <button type="submit" className="send-btn" disabled={!newMessage.trim()}>
          Send
        </button>
      </form>
      </div>
    </div>
  )
}

export default CoPassengerChat
