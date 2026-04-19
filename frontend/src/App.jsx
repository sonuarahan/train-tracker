import { useState } from "react"
import TrainStatus from "./components/TrainStatus"
import CoPassengerChat from "./components/CoPassengerChat"
import "./App.css"

function App() {
  const [activeTab, setActiveTab] = useState("status")

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>Indian Rail Tracker</h1>
          <p>Live Train Status & Co-Passenger Chat</p>
        </div>
      </header>

      <nav className="tab-nav">
        <button
          className={`tab-btn ${activeTab === "status" ? "active" : ""}`}
          onClick={() => setActiveTab("status")}
        >
          Train Status
        </button>
        <button
          className={`tab-btn ${activeTab === "chat" ? "active" : ""}`}
          onClick={() => setActiveTab("chat")}
        >
          Co-Passenger Chat
        </button>
      </nav>

      <main className="main-content">
        {activeTab === "status" ? <TrainStatus /> : <CoPassengerChat />}
      </main>

      <footer className="app-footer">
        <p>Data sourced from Indian Railways. For informational purposes only.</p>
      </footer>
    </div>
  )
}

export default App
