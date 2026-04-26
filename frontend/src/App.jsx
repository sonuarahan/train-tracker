import { useState } from "react"
import { useTranslation } from 'react-i18next';
import TrainStatus from "./components/TrainStatus"
import CoPassengerChat from "./components/CoPassengerChat"
import "./App.css"

function App() {
  const [activeTab, setActiveTab] = useState("status")
  const { t, i18n } = useTranslation();

  const languages = [
    { code: 'en', label: 'English' },
    { code: 'hi', label: 'हिन्दी' },
    { code: 'kn', label: 'ಕನ್ನಡ' },
    { code: 'ur', label: 'اردو' },
    { code: 'te', label: 'తెలుగు' },
    { code: 'bn', label: 'বাংলা' },
    { code: 'bho', label: 'भोजपुरी' },
  ];

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>{t('indian_rail_tracker', 'Indian Rail Tracker')}</h1>
          <p>{t('live_train_status_and_chat', 'Live Train Status & Co-Passenger Chat')}</p>
        </div>
        <div className="lang-switcher" style={{ marginTop: 12 }}>
          <select
            value={i18n.language}
            onChange={e => i18n.changeLanguage(e.target.value)}
            style={{ fontSize: 16, padding: '4px 12px', borderRadius: 6 }}
          >
            {languages.map(lang => (
              <option key={lang.code} value={lang.code}>{lang.label}</option>
            ))}
          </select>
        </div>
      </header>

      <nav className="tab-nav">
        <button
          className={`tab-btn ${activeTab === "status" ? "active" : ""}`}
          onClick={() => setActiveTab("status")}
        >
          {t('train_status', 'Train Status')}
        </button>
        <button
          className={`tab-btn ${activeTab === "chat" ? "active" : ""}`}
          onClick={() => setActiveTab("chat")}
        >
          {t('co_passenger_chat', 'Co-Passenger Chat')}
        </button>
      </nav>

      <main className="main-content">
        {activeTab === "status" ? <TrainStatus /> : <CoPassengerChat />}
      </main>

      <footer className="app-footer">
        <p>{t('footer_disclaimer', 'Data sourced from Indian Railways. For informational purposes only.')}</p>
      </footer>
    </div>
  )
}

export default App
