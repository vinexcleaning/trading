import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { api, useApi } from './api'
import { ago, Badge } from './components/ui'
import Backtesting from './pages/Backtesting'
import Leaderboard from './pages/Leaderboard'
import MarketDetail from './pages/MarketDetail'
import Markets from './pages/Markets'
import Overview from './pages/Overview'
import PaperTrading from './pages/PaperTrading'
import SettingsPage from './pages/Settings'
import SignalFeed from './pages/SignalFeed'
import SystemHealth from './pages/SystemHealth'
import WalletDetail from './pages/WalletDetail'
import Wallets from './pages/Wallets'

const NAV = [
  { to: '/overview', label: 'Overview', icon: '◎', section: 'Monitor' },
  { to: '/signals', label: 'Signal feed', icon: '⚡', section: null },
  { to: '/paper', label: 'Paper trading', icon: '◫', section: null },
  { to: '/leaderboard', label: 'Leaderboard', icon: '▤', section: 'Analyse' },
  { to: '/wallets', label: 'Wallets', icon: '◈', section: null },
  { to: '/markets', label: 'Markets', icon: '◍', section: null },
  { to: '/backtesting', label: 'Backtesting', icon: '⟲', section: null },
  { to: '/health', label: 'System health', icon: '✚', section: 'Operate' },
  { to: '/settings', label: 'Settings', icon: '⚙', section: null },
]

function HealthPill() {
  // Polls rather than streams: health is a slow-moving signal and a failed poll
  // must not take the shell down with it.
  const { data } = useApi(() => api.health(), [], { pollMs: 30_000 })
  if (!data) return null

  const tone = data.status === 'ok' ? 'good' : data.status === 'degraded' ? 'warn' : 'bad'
  const freshness = data.freshness ?? {}

  return (
    <div className="hstack" style={{ gap: 10 }}>
      <Badge tone={tone}>
        <span className={`dot dot-${tone === 'good' ? 'good' : tone === 'warn' ? 'warn' : 'bad'}`} />
        {data.status === 'ok' ? 'Healthy' : data.status}
      </Badge>
      <span className="faint desktop-only" style={{ fontSize: 12 }}>
        {data.scheduler_running ? 'Scheduler on' : 'Scheduler off'} · wallets synced{' '}
        {ago(freshness.last_wallet_sync)}
      </span>
    </div>
  )
}

export default function App() {
  return (
    <div className="app">
      <nav className="sidebar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            🎾
          </div>
          <div>
            <div className="brand-text">Copy-Trade Intel</div>
            <div className="brand-sub">Polymarket tennis</div>
          </div>
        </div>

        {NAV.map((item) => (
          <div key={item.to}>
            {item.section && <div className="nav-section">{item.section}</div>}
            <NavLink
              to={item.to}
              className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
            >
              <span className="nav-icon" aria-hidden="true">
                {item.icon}
              </span>
              {item.label}
            </NavLink>
          </div>
        ))}
      </nav>

      <div className="main">
        <header className="topbar">
          <div className="hstack">
            <strong style={{ fontSize: 14 }}>Tennis Copy-Trade Intelligence</strong>
            <Badge tone="neutral" title="This build cannot place real orders.">
              Read-only · paper only
            </Badge>
          </div>
          <HealthPill />
        </header>

        <main className="content">
          <Routes>
            <Route path="/" element={<Navigate to="/overview" replace />} />
            <Route path="/overview" element={<Overview />} />
            <Route path="/signals" element={<SignalFeed />} />
            <Route path="/paper" element={<PaperTrading />} />
            <Route path="/leaderboard" element={<Leaderboard />} />
            <Route path="/wallets" element={<Wallets />} />
            <Route path="/wallets/:id" element={<WalletDetail />} />
            <Route path="/markets" element={<Markets />} />
            <Route path="/markets/:id" element={<MarketDetail />} />
            <Route path="/backtesting" element={<Backtesting />} />
            <Route path="/health" element={<SystemHealth />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route
              path="*"
              element={
                <div className="empty">
                  <div className="empty-title">Page not found</div>
                </div>
              }
            />
          </Routes>
        </main>
      </div>
    </div>
  )
}
