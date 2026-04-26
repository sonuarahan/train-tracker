import { useState } from "react"
import "./TrainStatus.css"
import { FaTrain, FaMapMarkerAlt, FaClock, FaCheckCircle, FaExclamationCircle } from "react-icons/fa"

const API_BASE = "/api"

function TrainStatus() {
  const [query, setQuery] = useState("")
  const [searchResults, setSearchResults] = useState([])
  const [liveStatus, setLiveStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setError("")
    setLiveStatus(null)
    setSearchResults([])

    try {
      const res = await fetch(`${API_BASE}/search?query=${encodeURIComponent(query.trim())}`)
      const data = await res.json()
      if (data.success) {
        setSearchResults(data.data || [])
        if ((data.data || []).length === 0) {
          setError("No trains found. Try a different search term.")
        }
      } else {
        setError(data.error || "Failed to search trains")
      }
    } catch {
      setError("Could not connect to server. Make sure the backend is running.")
    } finally {
      setLoading(false)
    }
  }

  const handleGetStatus = async (trainNo) => {
    setLoading(true)
    setError("")
    setSearchResults([])

    try {
      const today = new Date().toISOString().split("T")[0]
      const res = await fetch(
        `${API_BASE}/live-status?trainNo=${trainNo}&startDate=${today}`
      )
      const data = await res.json()
      if (data.success) {
        setLiveStatus(data.data)
      } else {
        setError(data.error || "Failed to get live status")
      }
    } catch {
      setError("Could not connect to server. Make sure the backend is running.")
    } finally {
      setLoading(false)
    }
  }

  const handleDirectStatus = async (e) => {
    e.preventDefault()
    const trimmed = query.trim()
    if (/^\d{4,5}$/.test(trimmed)) {
      await handleGetStatus(trimmed)
    } else {
      await handleSearch(e)
    }
  }

  return (
    <div className="train-status">
      <div className="search-section">
        <h2>Check Live Train Running Status</h2>
        <form onSubmit={handleDirectStatus} className="search-form">
          <div className="search-input-group">
            <input
              type="text"
              placeholder="Enter train number (e.g. 12951) or train name"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="search-input"
              maxLength={50}
            />
            <button type="submit" className="search-btn" disabled={loading}>
              {loading ? "Searching..." : "Search"}
            </button>
          </div>
        </form>
      </div>

      {error && <div className="error-msg">{error}</div>}

      {searchResults.length > 0 && (
        <div className="search-results">
          <h3>Search Results</h3>
          <div className="results-list">
            {searchResults.map((train, i) => (
              <div key={i} className="train-card" onClick={() => handleGetStatus(train.trainNo)}>
                <div className="train-card-header">
                  <span className="train-no">#{train.trainNo}</span>
                  <span className="train-name">{train.trainName}</span>
                </div>
                <div className="train-card-route">
                  <span>{train.fromStn}</span>
                  <span className="route-arrow">→</span>
                  <span>{train.toStn}</span>
                </div>
                <div className="train-card-time">
                  <span>Dep: {train.departTime}</span>
                  <span>Arr: {train.arriveTime}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {liveStatus && (
        <div className="live-status-section">
          <div className="status-header">
            <h3>
              <FaTrain style={{marginRight: 8, color: '#1a237e'}} />
              {liveStatus.trainName} <span style={{fontWeight: 400}}>({liveStatus.trainNo})</span>
            </h3>
            <div className="route-info">
              <span className="station start"><FaMapMarkerAlt style={{marginRight: 4}} />{liveStatus.fromStn}</span>
              <span className="route-line">────────────</span>
              <span className="station end"><FaMapMarkerAlt style={{marginRight: 4}} />{liveStatus.toStn}</span>
            </div>
            <div className="journey-summary">
              <span><FaClock style={{marginRight: 4}} />Journey Date: {liveStatus.journeyDate}</span>
              <span style={{marginLeft: 16}}><FaClock style={{marginRight: 4}} />Last Updated: {liveStatus.lastUpdated}</span>
            </div>
          </div>

          {/* Progress Bar */}
          {liveStatus.stations && (
            <div className="progress-bar-section">
              <div className="progress-bar">
                {liveStatus.stations.map((stn, idx) => {
                  const isCurrent = stn.name === liveStatus.currentStation
                  return (
                    <div key={idx} className={`progress-station${isCurrent ? " current" : ""}`}> 
                      <div className="station-marker">
                        {isCurrent ? <FaTrain className="current-train-icon" /> : <span className="dot" />}
                      </div>
                      <div className="station-label">{stn.code}</div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          <div className="status-cards">
            <div className="info-card">
              <div className="info-label">Current Station</div>
              <div className="info-value highlight">
                <FaMapMarkerAlt style={{marginRight: 4, color: '#3949ab'}} />
                {liveStatus.currentStation}
              </div>
            </div>
            <div className={`info-card ${liveStatus.delay !== "On Time" ? "delay" : "ontime"}`}>
              <div className="info-label">Status</div>
              <div className="info-value">
                {liveStatus.delay !== "On Time" ? (
                  <><FaExclamationCircle style={{color: '#c62828', marginRight: 4}} />{liveStatus.delay}</>
                ) : (
                  <><FaCheckCircle style={{color: '#2e7d32', marginRight: 4}} />On Time</>
                )}
              </div>
            </div>
            <div className="info-card">
              <div className="info-label">Last Updated</div>
              <div className="info-value">
                <FaClock style={{marginRight: 4, color: '#3949ab'}} />
                {liveStatus.lastUpdated}
              </div>
            </div>
          </div>

          {liveStatus.stations && (
            <div className="station-list">
              <h4>Station-wise Status</h4>
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Station</th>
                      <th>Sch. Arr</th>
                      <th>Sch. Dep</th>
                      <th>Act. Arr</th>
                      <th>Delay</th>
                      <th>Platform</th>
                    </tr>
                  </thead>
                  <tbody>
                    {liveStatus.stations.map((stn, i) => {
                      const isCurrent = stn.name === liveStatus.currentStation
                      return (
                        <tr key={i} className={isCurrent ? "current-row" : ""}>
                          <td>
                            <strong>{stn.code}</strong> - {stn.name}
                            {isCurrent && <span className="current-badge">Current</span>}
                          </td>
                          <td>{stn.schArr}</td>
                          <td>{stn.schDep}</td>
                          <td>{stn.actArr}</td>
                          <td className={stn.delay !== "On Time" ? "text-red" : "text-green"}>
                            {stn.delay}
                          </td>
                          <td>{stn.platform}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <button className="back-btn" onClick={() => { setLiveStatus(null); setQuery("") }}>
            ← Search Another Train
          </button>
        </div>
      )}
    </div>
  )
}

export default TrainStatus
