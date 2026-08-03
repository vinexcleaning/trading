import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, useApi } from '../api'
import {
  ago,
  Badge,
  Card,
  Empty,
  ErrorNote,
  Loading,
  money,
  Notice,
  RiskFlags,
  shortAddress,
  StatusBadge,
} from '../components/ui'

export default function Wallets() {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const wallets = useApi(
    () => api.wallets({ search: search || undefined, status: status || undefined, limit: 300 }),
    [search, status],
  )

  const [address, setAddress] = useState('')
  const [nickname, setNickname] = useState('')

  const addWallet = async (event: React.FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setMessage(null)
    try {
      const wallet = await api.createWallet({ address, nickname: nickname || null })
      setMessage(`Added ${wallet.address}. Sync it to download its history.`)
      setAddress('')
      setNickname('')
      wallets.reload()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  const importCsv = async (file: File) => {
    setBusy(true)
    setMessage(null)
    try {
      const result = await api.importWallets(file)
      setMessage(
        `Imported ${result.added} wallet(s), skipped ${result.skipped_existing} existing.` +
          (result.errors.length ? ` ${result.errors.length} row(s) rejected.` : ''),
      )
      wallets.reload()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const discover = async () => {
    setBusy(true)
    setMessage(null)
    try {
      const result = await api.discoverWallets({ source: 'tennis_markets' })
      setMessage(result.message)
      wallets.reload()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  const sync = async (id: number) => {
    setBusy(true)
    setMessage(null)
    try {
      const result = await api.syncWallet(id, { run_analytics: true })
      setMessage(result.message)
      wallets.reload()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>Wallet registry</h1>
        <p>
          Wallets can be added by hand, imported from CSV, or discovered from public tennis-market
          activity. Discovery is never treated as evidence of skill — nothing is approved
          automatically.
        </p>
      </div>

      <div className="grid grid-2" style={{ marginBottom: 18 }}>
        <Card title="Add a wallet">
          <form onSubmit={addWallet}>
            <label className="field">
              <span>Wallet address</span>
              <input
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="0x…"
                required
              />
            </label>
            <label className="field">
              <span>Nickname (optional)</span>
              <input
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                placeholder="e.g. clay-court specialist"
              />
            </label>
            <button className="btn btn-primary" disabled={busy || !address}>
              Add wallet
            </button>
          </form>
        </Card>

        <Card title="Bulk actions" subtitle="CSV needs an 'address' column; other columns optional">
          <div className="btn-row">
            <input
              ref={fileRef}
              type="file"
              accept=".csv,text/csv"
              style={{ display: 'none' }}
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) void importCsv(file)
              }}
            />
            <button className="btn" onClick={() => fileRef.current?.click()} disabled={busy}>
              Import CSV
            </button>
            <button className="btn" onClick={discover} disabled={busy}>
              Discover from tennis markets
            </button>
          </div>
          <div style={{ marginTop: 12 }}>
            <Notice tone="info">
              Discovered wallets arrive unapproved and unscored. They must be synced and analysed
              before they can produce a signal.
            </Notice>
          </div>
        </Card>
      </div>

      {message && (
        <div style={{ marginBottom: 14 }}>
          <Notice tone="info">{message}</Notice>
        </div>
      )}

      <div className="filters">
        <label className="field">
          <span>Search</span>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="address or nickname"
          />
        </label>
        <label className="field">
          <span>Status</span>
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="blocked">Blocked</option>
          </select>
        </label>
      </div>

      {wallets.error ? (
        <ErrorNote message={wallets.error} onRetry={wallets.reload} />
      ) : wallets.loading && !wallets.data ? (
        <Loading rows={5} />
      ) : !wallets.data?.length ? (
        <Card>
          <Empty
            title="No wallets tracked"
            hint="Add an address above, import a CSV, or discover wallets from recent tennis-market activity."
          />
        </Card>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Wallet</th>
                <th>Status</th>
                <th>Source</th>
                <th>Approved</th>
                <th className="num">Portfolio</th>
                <th>Last activity</th>
                <th>Last sync</th>
                <th>Risk flags</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {wallets.data.map((w) => (
                <tr key={w.id}>
                  <td>
                    <Link to={`/wallets/${w.id}`}>
                      {w.nickname ?? <span className="mono">{shortAddress(w.address)}</span>}
                    </Link>
                    {w.on_watchlist && (
                      <>
                        {' '}
                        <Badge tone="info">watchlist</Badge>
                      </>
                    )}
                  </td>
                  <td>
                    <StatusBadge status={w.status} />
                  </td>
                  <td className="faint">{w.source.replace(/_/g, ' ')}</td>
                  <td>
                    {w.manually_approved ? (
                      <Badge tone="good">yes</Badge>
                    ) : (
                      <Badge tone="neutral">no</Badge>
                    )}
                  </td>
                  <td className="num">{money(w.observed_portfolio_value, 0)}</td>
                  <td className="faint">{ago(w.last_activity_at)}</td>
                  <td className="faint">
                    {w.last_sync_error ? (
                      <Badge tone="bad" title={w.last_sync_error}>
                        failed
                      </Badge>
                    ) : (
                      ago(w.last_sync_success_at)
                    )}
                  </td>
                  <td>
                    <RiskFlags flags={w.risk_flags} max={2} />
                  </td>
                  <td>
                    <button className="btn btn-sm" onClick={() => sync(w.id)} disabled={busy}>
                      Sync
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
