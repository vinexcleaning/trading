import { Fragment, useCallback, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, useApi, useSignalStream } from '../api'
import {
  ago,
  Badge,
  Card,
  Empty,
  ErrorNote,
  Loading,
  money,
  Notice,
  num,
  pct,
  price,
  RiskFlags,
  ScoreBar,
  shortAddress,
  signClass,
  StatusBadge,
  Tooltip,
  humanize,
} from '../components/ui'
import type { Signal } from '../types'

const STATUSES = [
  '',
  'observed',
  'evaluating',
  'qualified',
  'rejected',
  'expired',
  'paper_entered',
  'paper_exited',
]

export default function SignalFeed() {
  const [status, setStatus] = useState('')
  const [qualifiedOnly, setQualifiedOnly] = useState(false)
  const [hours, setHours] = useState(48)
  const [expanded, setExpanded] = useState<number | null>(null)
  const [live, setLive] = useState<Signal[]>([])
  const [scanning, setScanning] = useState(false)
  const [scanMessage, setScanMessage] = useState<string | null>(null)

  const feed = useApi(
    () =>
      api.signals({
        limit: 100,
        hours,
        status: status || undefined,
        qualified: qualifiedOnly ? true : undefined,
      }),
    [status, qualifiedOnly, hours],
    { pollMs: 25_000 },
  )

  // The stream is an accelerator, not the source of truth: polling still runs,
  // so a dropped connection slows updates instead of emptying the page.
  const onSignal = useCallback((signal: Signal) => {
    setLive((current) => [signal, ...current.filter((s) => s.id !== signal.id)].slice(0, 30))
  }, [])
  const connected = useSignalStream(onSignal)

  const rows = useMemo(() => {
    const seen = new Set<number>()
    const merged: Signal[] = []
    for (const signal of [...live, ...(feed.data ?? [])]) {
      if (seen.has(signal.id)) continue
      seen.add(signal.id)
      if (status && signal.status !== status) continue
      if (qualifiedOnly && !signal.qualified) continue
      merged.push(signal)
    }
    return merged
  }, [live, feed.data, status, qualifiedOnly])

  const runScan = async () => {
    setScanning(true)
    setScanMessage(null)
    try {
      const result = await api.scanSignals({})
      setScanMessage(result.message)
      feed.reload()
    } catch (err) {
      setScanMessage(err instanceof Error ? err.message : String(err))
    } finally {
      setScanning(false)
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>
          Live signal feed{' '}
          <Badge tone={connected ? 'good' : 'neutral'}>
            <span className={`dot ${connected ? 'dot-good live-dot' : 'dot-idle'}`} />
            {connected ? 'Streaming' : 'Polling'}
          </Badge>
        </h1>
        <p>
          Every candidate is shown, not just the ones that passed. Reading the rejections — and the
          reason each one failed — is how the alert thresholds get calibrated.
        </p>
      </div>

      <div className="filters">
        <label className="field">
          <span>Status</span>
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s ? humanize(s) : 'All statuses'}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Window</span>
          <select value={hours} onChange={(e) => setHours(Number(e.target.value))}>
            <option value={6}>Last 6 hours</option>
            <option value={24}>Last 24 hours</option>
            <option value={48}>Last 2 days</option>
            <option value={168}>Last week</option>
            <option value={720}>Last 30 days</option>
          </select>
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={qualifiedOnly}
            onChange={(e) => setQualifiedOnly(e.target.checked)}
          />
          Qualified only
        </label>
        <button className="btn" onClick={runScan} disabled={scanning}>
          {scanning ? 'Scanning…' : 'Scan now'}
        </button>
      </div>

      {scanMessage && (
        <div style={{ marginBottom: 14 }}>
          <Notice tone="info">{scanMessage}</Notice>
        </div>
      )}

      {feed.error ? (
        <ErrorNote message={feed.error} onRetry={feed.reload} />
      ) : feed.loading && !feed.data ? (
        <Loading rows={6} />
      ) : !rows.length ? (
        <Card>
          <Empty
            title="No signals in this window"
            hint="Signals require a tracked wallet with a computed tennis score to trade a classified tennis market. Sync some wallets and run the analytics job first."
          />
        </Card>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Detected</th>
                <th>Market / outcome</th>
                <th>Type</th>
                <th>Status</th>
                <th className="num">Wallet entry</th>
                <th className="num">Now</th>
                <th className="num">
                  <Tooltip text="Estimated price a follower would actually pay after spread and modelled slippage.">
                    <span>Est. fill</span>
                  </Tooltip>
                </th>
                <th className="num">Deterioration</th>
                <th className="num">Liquidity</th>
                <th className="num">Copyability</th>
                <th className="num">Skill</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((s) => (
                // The key belongs on the fragment: each row expands into two
                // sibling <tr>s, so keying the inner elements is not enough.
                <Fragment key={s.id}>
                  <tr>
                    <td className="faint" style={{ whiteSpace: 'nowrap' }}>
                      {ago(s.detected_at)}
                    </td>
                    <td style={{ minWidth: 200 }}>
                      <div style={{ fontWeight: 550 }}>{s.outcome_label ?? '—'}</div>
                      <div className="faint" style={{ fontSize: 11.5 }}>
                        {s.market_question ?? '—'}
                      </div>
                    </td>
                    <td>
                      <Badge tone={s.signal_type === 'consensus' ? 'info' : 'neutral'}>
                        {s.wallet_count} wallet{s.wallet_count === 1 ? '' : 's'}
                        {s.signal_type === 'consensus' &&
                          ` · ${s.independent_cluster_count} group${
                            s.independent_cluster_count === 1 ? '' : 's'
                          }`}
                      </Badge>
                    </td>
                    <td>
                      <StatusBadge status={s.status} />
                    </td>
                    <td className="num">{price(s.wallet_entry_price_median)}</td>
                    <td className="num">{price(s.current_price)}</td>
                    <td className="num">{price(s.estimated_follower_price)}</td>
                    <td className={`num ${Number(s.price_deterioration) > 0 ? 'neg' : 'pos'}`}>
                      {s.price_deterioration === null
                        ? '—'
                        : `${Number(s.price_deterioration) > 0 ? '+' : ''}${Number(
                            s.price_deterioration,
                          ).toFixed(3)}`}
                    </td>
                    <td className="num">{money(s.available_liquidity, 0)}</td>
                    <td className="num">
                      <ScoreBar value={s.copyability_score} />
                    </td>
                    <td className="num">{num(s.median_skill_score, 0)}</td>
                    <td>
                      <button
                        className="btn btn-sm"
                        onClick={() => setExpanded(expanded === s.id ? null : s.id)}
                      >
                        {expanded === s.id ? 'Hide' : 'Why?'}
                      </button>
                    </td>
                  </tr>
                  {expanded === s.id && (
                    <tr>
                      <td colSpan={12} style={{ background: 'var(--bg)' }}>
                        <SignalDetail signal={s} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

function SignalDetail({ signal }: { signal: Signal }) {
  const checks = signal.qualification_detail ?? []
  const failed = checks.filter((c) => c.passed === false)
  const passed = checks.filter((c) => c.passed === true)

  return (
    <div className="vstack" style={{ gap: 14, padding: '6px 2px 12px' }}>
      {signal.explanation && (
        <Notice tone={signal.qualified ? 'info' : 'warn'}>{signal.explanation}</Notice>
      )}

      <div className="grid grid-2">
        <Card title="Decision inputs">
          <dl className="kv">
            <dt>Signal age</dt>
            <dd>{signal.signal_age_seconds === null ? '—' : `${signal.signal_age_seconds}s`}</dd>
            <dt>Market phase</dt>
            <dd>{humanize(signal.market_phase)}</dd>
            <dt>Spread</dt>
            <dd>{signal.spread === null ? '—' : Number(signal.spread).toFixed(3)}</dd>
            <dt>Wallet position size</dt>
            <dd>{money(signal.total_wallet_position_usdc, 0)}</dd>
            <dt>Median copyable ROI</dt>
            <dd className={signClass(signal.median_copyable_roi)}>
              {signal.median_copyable_roi === null ? 'n/a' : pct(signal.median_copyable_roi)}
            </dd>
            <dt>
              Estimated edge{' '}
              <Tooltip text="A transparent heuristic, not a calibrated probability. It blends wallet quality, agreement and price context." />
            </dt>
            <dd>
              {signal.estimated_edge === null ? '—' : pct(signal.estimated_edge)}{' '}
              <span className="faint">({signal.edge_method ?? 'n/a'})</span>
            </dd>
            <dt>Data confidence</dt>
            <dd>{signal.data_confidence === null ? '—' : `${signal.data_confidence.toFixed(0)}/100`}</dd>
            <dt>Consensus score</dt>
            <dd>{signal.consensus_score === null ? '—' : num(signal.consensus_score, 0)}</dd>
          </dl>
          <div style={{ marginTop: 12 }}>
            <div className="stat-label" style={{ marginBottom: 5 }}>
              Risk flags
            </div>
            <RiskFlags flags={signal.risk_flags} />
          </div>
        </Card>

        <Card
          title="Contributing wallets"
          subtitle="Wallets in the same behavioural cluster count once, not once each"
        >
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Wallet</th>
                  <th className="num">Entry</th>
                  <th className="num">Size</th>
                  <th className="num">Skill</th>
                  <th className="num">Trades</th>
                  <th>Counts?</th>
                </tr>
              </thead>
              <tbody>
                {signal.wallets.map((w) => (
                  <tr key={w.wallet_id}>
                    <td>
                      <Link to={`/wallets/${w.wallet_id}`} className="mono">
                        {w.nickname ?? shortAddress(w.address)}
                      </Link>
                      {w.has_begun_exiting && (
                        <>
                          {' '}
                          <Badge tone="bad">exiting</Badge>
                        </>
                      )}
                    </td>
                    <td className="num">{price(w.entry_price)}</td>
                    <td className="num">{money(w.position_usdc, 0)}</td>
                    <td className="num">{num(w.skill_score, 0)}</td>
                    <td className="num">{w.tennis_trade_count ?? '—'}</td>
                    <td>
                      {w.counted_as_independent ? (
                        <Badge tone="good">independent</Badge>
                      ) : (
                        <Badge tone="warn" title="Suppressed as a cluster duplicate">
                          duplicate
                        </Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {checks.length > 0 && (
        <Card
          title="Qualification checks"
          subtitle={`${passed.length} passed · ${failed.length} failed`}
        >
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Check</th>
                  <th className="num">Value</th>
                  <th className="num">Threshold</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                {[...failed, ...passed].map((c, i) => (
                  <tr key={i}>
                    <td>{humanize(String(c.check))}</td>
                    <td className="num mono">{String(c.value ?? '—')}</td>
                    <td className="num mono">{String(c.threshold ?? '—')}</td>
                    <td>
                      {c.passed ? <Badge tone="good">pass</Badge> : <Badge tone="bad">fail</Badge>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}
