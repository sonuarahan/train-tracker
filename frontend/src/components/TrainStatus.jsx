import { useState, useRef, useEffect } from "react"
import { useTranslation } from 'react-i18next';
import "./TrainStatus.css"
import { FaTrain, FaMapMarkerAlt, FaClock, FaCheckCircle, FaExclamationCircle, FaSyncAlt } from "react-icons/fa"

const API_BASE = "/api"

function TrainStatus() {
  const { t } = useTranslation();
  // Remove modal state

  const [query, setQuery] = useState("")
  const [searchResults, setSearchResults] = useState([])
  const [liveStatus, setLiveStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  // Store last train number for refresh
  const lastTrainNoRef = useRef(null)

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

  // Ref for scrolling to current station
  const currentStationRef = useRef(null)

  const handleGetStatus = async (trainNo, isRefresh = false) => {
    setLoading(true)
    setError("")
    if (!isRefresh) setSearchResults([])
    lastTrainNoRef.current = trainNo

    try {
      const today = new Date().toISOString().split("T")[0]
      const res = await fetch(
        `${API_BASE}/live-status?trainNo=${trainNo}&startDate=${today}`
      )
      const data = await res.json()
      if (data.success) {
        setLiveStatus(data.data)
        // Scroll to current station after a short delay (after DOM update)
        setTimeout(() => {
          if (currentStationRef.current) {
            currentStationRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
          }
        }, 300);
      } else {
        setError(data.error || "Failed to get live status")
      }
    } catch {
      setError("Could not connect to server. Make sure the backend is running.")
    } finally {
      setLoading(false)
    }
  }

  // Handler for refresh button
  const handleRefreshStatus = () => {
    if (lastTrainNoRef.current) {
      handleGetStatus(lastTrainNoRef.current, true)
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
        <h2>{t('check_live_train_status', 'Check Live Train Running Status')}</h2>
        <form onSubmit={handleDirectStatus} className="search-form">
          <div className="search-input-group">
            <input
              type="text"
              placeholder={t('search_placeholder')}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="search-input"
              maxLength={50}
            />
            <button type="submit" className="search-btn" disabled={loading}>
              {loading ? t('searching', 'Searching...') : t('search_button')}
            </button>
          </div>
        </form>
      </div>

      {error && <div className="error-msg">{t(error, error)}</div>}

      {searchResults.length > 0 && (
        <div className="search-results">
          <h3>{t('search_results', 'Search Results')}</h3>
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
                  <span>{t('departure')}: {train.departTime}</span>
                  <span>{t('arrival')}: {train.arriveTime}</span>
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
              {/* Latest Status button */}
              <button
                className="refresh-btn"
                title="Get latest train status"
                style={{
                  marginLeft: 16,
                  background: '#3949ab',
                  border: 'none',
                  color: '#fff',
                  borderRadius: 6,
                  padding: '4px 14px',
                  fontWeight: 500,
                  fontSize: 15,
                  cursor: loading ? 'not-allowed' : 'pointer',
                  outline: 'none',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  opacity: loading ? 0.7 : 1,
                  transition: 'background 0.2s, opacity 0.2s',
                  position: 'relative',
                  top: 2
                }}
                onClick={handleRefreshStatus}
                disabled={loading}
              >
                <FaSyncAlt className={loading ? 'refresh-spin' : ''} style={{marginRight: 4}} />
                Latest Status
              </button>
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
              <div className="info-label">{t('current_station')}</div>
              <a
                className="info-value highlight clickable"
                title="Click to view Google Images for this station"
                style={{cursor: 'pointer', textDecoration: 'none'}}
                href={`https://www.google.com/search?tbm=isch&q=${encodeURIComponent(liveStatus.currentStation + ' railway station')}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                <FaMapMarkerAlt style={{marginRight: 4, color: '#3949ab'}} />
                {liveStatus.currentStation}
              </a>
            </div>

            <div className={`info-card ${liveStatus.delay !== "On Time" ? "delay" : "ontime"}`}>
              <div className="info-label">{t('status')}</div>
              <div className="info-value">
                {liveStatus.delay !== "On Time" ? (
                  <><FaExclamationCircle style={{color: '#c62828', marginRight: 4}} />{liveStatus.delay}</>
                ) : (
                  <><FaCheckCircle style={{color: '#2e7d32', marginRight: 4}} />On Time</>
                )}
              </div>
            </div>
            <div className="info-card">
              <div className="info-label">{t('last_updated')}</div>
              <div className="info-value">
                <FaClock style={{marginRight: 4, color: '#3949ab'}} />
                {liveStatus.lastUpdated}
              </div>
            </div>
          </div>


          {liveStatus.stations && (
            <div className="timeline-section">
              <h4>Station-wise Status</h4>
              <div className="timeline">
                {(() => {
                  // Parse time in HH:mm or HH:mm AM/PM
                  function parseTime(t) {
                    if (!t) return null;
                    let [h, m] = t.split(":");
                    h = parseInt(h, 10);
                    m = parseInt(m, 10);
                    return h * 60 + m;
                  }
                  // Get current time in minutes
                  const now = new Date();
                  const currentMinutes = now.getHours() * 60 + now.getMinutes();

                  // Find the current station from API response
                  // Helper to parse "HH:mm" to minutes since midnight
                  function parseTimeToMinutes(t) {
                    if (!t) return null;
                    const [h, m] = t.split(":").map(Number);
                    return h * 60 + m;
                  }
                  // Get current time in minutes (declare once outside map)
                  const nowGlobal = new Date();
                  const currentMinutesGlobal = nowGlobal.getHours() * 60 + nowGlobal.getMinutes();

                  // --- Inject current station if missing ---
                  let stations = [...liveStatus.stations];
                  let currentIdx = -1;
                  let currentStationCode = null;
                  let currentStationName = null;
                  if (liveStatus.currentStation) {
                    // Parse code and name from "CODE - NAME"
                    const parts = liveStatus.currentStation.split("-");
                    currentStationCode = parts[0]?.trim();
                    currentStationName = parts[1]?.trim();
                  }

                  // Try to find the current station in the list
                  currentIdx = stations.findIndex(stn =>
                    (currentStationCode && stn.code.toLowerCase() === currentStationCode.toLowerCase()) ||
                    (currentStationName && stn.name.toLowerCase() === currentStationName.toLowerCase())
                  );

                  // Only inject if not present
                  if (currentIdx === -1 && currentStationCode && currentStationName) {
                    // --- New logic: inject based on current time and delay ---
                    function parseTimeToMinutes(t) {
                      if (!t) return null;
                      const [h, m] = t.split(":").map(Number);
                      return h * 60 + m;
                    }
                    function parseDelayToMinutes(delay) {
                      if (!delay || delay === "On Time") return 0;
                      const match = delay.match(/(\d+)/);
                      return match ? parseInt(match[1], 10) : 0;
                    }
                    const now = new Date();
                    const currentMinutes = now.getHours() * 60 + now.getMinutes();

                    let insertIdx = -1;
                    for (let i = 0; i < stations.length - 1; i++) {
                      // Previous station: scheduled departure + delay
                      const prevDep = parseTimeToMinutes(stations[i].schDep);
                      const prevDelay = parseDelayToMinutes(stations[i].delay);
                      const prevTime = prevDep !== null ? prevDep + prevDelay : null;

                      // Next station: scheduled arrival + delay
                      const nextArr = parseTimeToMinutes(stations[i + 1].schArr);
                      const nextDelay = parseDelayToMinutes(stations[i + 1].delay);
                      const nextTime = nextArr !== null ? nextArr + nextDelay : null;

                      if (
                        prevTime !== null && nextTime !== null &&
                        currentMinutes >= prevTime && currentMinutes < nextTime
                      ) {
                        insertIdx = i + 1;
                        break;
                      }
                    }
                    // If not found, append to the end
                    if (insertIdx === -1) insertIdx = stations.length;

                    const dummyStation = {
                      code: currentStationCode,
                      name: currentStationName,
                      platform: "-",
                      delay: liveStatus.delay || "-",
                      actArr: "-",
                      schArr: "-",
                      schDep: "-"
                    };
                    stations.splice(insertIdx, 0, dummyStation);
                    currentIdx = insertIdx;
                  }

                  return stations.map((stn, i) => {
                    const isCurrent = i === currentIdx;
                    const isPast = i < currentIdx;
                    const isFuture = i > currentIdx;
                    return (
                      <div
                        key={i}
                        className={`timeline-card${isCurrent ? " current-timeline-card current-timeline-green" : ""}${isPast ? " past-timeline-card" : ""}${isFuture ? " future-timeline-card" : ""}`}
                        ref={isCurrent ? currentStationRef : null}
                      >
                        <div className={`timeline-marker${isCurrent ? " timeline-marker-current" : ""}${isPast ? " timeline-marker-past" : ""}`}> 
                          {isCurrent ? <span className="timeline-train-pulse"><FaTrain className="timeline-train-icon" /></span> : <span className="timeline-dot" />}
                          {i !== stations.length - 1 && <div className={`timeline-line${isPast || isCurrent ? " timeline-line-current" : ""}`} />}
                        </div>
                        <div className="timeline-content">
                          <div className="timeline-station-row">
                            <span className="timeline-station-code"><strong>{stn.code}</strong></span>
                            <span className="timeline-station-name">{stn.name}</span>
                            {isCurrent && <span className="timeline-current-badge">{t('train_is_here')}</span>}
                            <span className="timeline-platform">• {t('platform')} {stn.platform}</span>
                            <span className={`timeline-delay ${stn.delay !== "On Time" ? "timeline-delay-late" : "timeline-delay-ontime"}`}>{stn.delay}</span>
                          </div>
                          <div className="timeline-times">
                            <div>
                              <span className="timeline-label">{t('arrival')}</span>
                              <span className="timeline-time">{stn.actArr || stn.schArr}</span>
                            </div>
                            <div>
                              <span className="timeline-label">{t('departure')}</span>
                              <span className="timeline-time">{(() => {
                                if (
                                  stn.actArr && stn.actArr !== "-" &&
                                  stn.schArr && stn.schArr !== "-" &&
                                  stn.schDep && stn.schDep !== "-"
                                ) {
                                  const [actH, actM] = stn.actArr.split(":").map(Number);
                                  const [schArrH, schArrM] = stn.schArr.split(":").map(Number);
                                  const [schDepH, schDepM] = stn.schDep.split(":").map(Number);
                                  const actArrMin = actH * 60 + actM;
                                  const schArrMin = schArrH * 60 + schArrM;
                                  const schDepMin = schDepH * 60 + schDepM;
                                  const offset = schDepMin - schArrMin;
                                  const depMin = actArrMin + offset;
                                  const depH = Math.floor(depMin / 60) % 24;
                                  const depM = depMin % 60;
                                  return `${depH.toString().padStart(2, "0")}:${depM.toString().padStart(2, "0")}`;
                                }
                                return stn.schDep || "-";
                              })()}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    )
                  });
                })()}
              </div>
            </div>
          )}

          <button className="back-btn" onClick={() => { setLiveStatus(null); setQuery("") }}>
            ← {t('search_another_train')}
          </button>
        </div>
      )}
    </div>
  )
}

export default TrainStatus
