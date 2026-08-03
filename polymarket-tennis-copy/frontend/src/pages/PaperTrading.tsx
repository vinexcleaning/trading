import { useState } from 'react'
import { api, useApi } from '../api'
import {
  ago,
  Badge,
  Card,
  Empty,
  ErrorNote,
  humanize,
  Loading,
  money,
  Notice,
  pct,
  price,
  signClass,
  Stat,
  StatusBadge,
  Tooltip,
} from '../components/ui'
import { EvidenceBadge } from './WalletDetail'

export default function PaperTrading() {
  const [includeRejected, setIncludeRejected] = useState(true)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const summary = useApi(() => api.paperSummary(), [], { pollMs: 30_000 })
  const risk = useApi(() => api.paperRisk(), [], { pollMs: 30_000 })
  const trades = useApi(
    () => api.paperTrades({ include_rejected: includeRejected, limit: 200 }),
    [includeRejected],
    { pollMs: 30_000 },
  )

  const manage = async () => {
    setBusy(true)
    setMessage(null)
    try {
      const result = await api.managePaper()
      setMessage(result.message)
      trades.reload()
      summary.reload()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  const s = summary.data
  const r = risk.data

  return (
    <>
      <div className="page-header">
        <h1>Paper trading</h1>
        <p>
          Simulated follower positions opened from qualified signals, filled at the price available
          after the configured execution delay. No real orders are placed anywhere in this system.
        </p>
      </div>

      <div style={{ marginBottom: 16 }}>
        <Notice tone="warn">
          {s?.disclaimer ??
            'Simulated results. Fills are modelled from observed prices and order-book depth, so they may differ materially from real execution.'}
        </Notice>
      </div>

      {summary.error ? (
        <ErrorNote message={summary.error} onRetry={summary.reload} />
      ) : summary.loading && !s ? (
        <Loading rows={4} />
      ) : s ? (
        <div className="grid grid-4">
          <Stat
            label="Net P&L"
            value={money(s.net_pnl)}
            tone={signClass(Number(s.net_pnl)) as 'pos' | 'neg' | ''}
            hint={`Realised ${money(s.realized_pnl)} · unrealised ${money(s.unrealized_pnl)}`}
          />
          <Stat
            label="Paper ROI"
            value={s.roi === null ? '—' : pct(s.roi)}
            tone={signClass(s.roi) as 'pos' | 'neg' | ''}
            hint={`Staked ${money(s.total_staked, 0)}`}
          />
          <Stat
            label="Record"
            value={`${s.wins}W / ${s.losses}L`}
            hint={`${s.open_trades} open · ${s.closed_trades} closed`}
          />
          <Stat
            label="Cost of following"
            value={s.avg_roi_gap_vs_wallet === null ? '—' : pct(s.avg_roi_gap_vs_wallet)}
            tone={signClass(s.avg_roi_gap_vs_wallet) as 'pos' | 'neg' | ''}
            hint="Follower ROI minus source-wallet ROI"
            tooltip="The measured price of being late. Negative means the follower captured less than the wallet did."
          />
        </div>
      ) : null}

      <div className="section grid grid-2">
        {r && (
          <Card title="Risk limits" subtitle="Simulation defaults, not recommendations">
            <dl className="kv">
              <dt>Paper trading</dt>
              <dd>
                {r.enabled ? <Badge tone="good">enabled</Badge> : <Badge tone="neutral">off</Badge>}
              </dd>
              <dt>Open positions</dt>
              <dd>
                {r.open_positions} / {r.max_open_positions}
              </dd>
              <dt>Total exposure</dt>
              <dd>
                {money(r.total_exposure, 0)} / {money(r.max_total_exposure, 0)}
              </dd>
              <dt>Per-market cap</dt>
              <dd>{money(r.max_exposure_per_market, 0)}</dd>
              <dt>Stake per signal</dt>
              <dd>{money(r.stake_per_signal, 0)}</dd>
              <dt>Execution delay</dt>
              <dd>{r.execution_delay_seconds}s</dd>
              <dt>Realised today</dt>
              <dd className={signClass(Number(r.realized_pnl_today))}>
                {money(r.realized_pnl_today)} <span className="faint">(cap {money(r.daily_loss_cap, 0)})</span>
              </dd>
              <dt>Exit strategy</dt>
              <dd>{humanize(r.default_exit_strategy)}</dd>
            </dl>
            <div className="btn-row" style={{ marginTop: 12 }}>
              <button className="btn" onClick={manage} disabled={busy}>
                {busy ? 'Working…' : 'Mark & apply exit rules'}
              </button>
            </div>
          </Card>
        )}

        {s && (
          <Card
            title="Entries refused"
            subtitle={`${s.rejected} simulated entries were blocked`}
            tooltip="Refusals are recorded rather than hidden: a strategy that only looks good because impossible fills were assumed is not a strategy."
          >
            {Object.keys(s.rejection_reasons).length === 0 ? (
              <Empty title="No refused entries" />
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Reason</th>
                      <th className="num">Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(s.rejection_reasons).map(([reason, count]) => (
                      <tr key={reason}>
                        <td>{humanize(reason)}</td>
                        <td className="num">{count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        )}
      </div>

      {message && (
        <div className="section">
          <Notice tone="info">{message}</Notice>
        </div>
      )}

      <div className="section">
        <div className="section-title">
          <h2>Simulated positions</h2>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={includeRejected}
              onChange={(e) => setIncludeRejected(e.target.checked)}
            />
            Include refused entries
          </label>
        </div>

        {trades.loading && !trades.data ? (
          <Loading rows={4} />
        ) : !trades.data?.length ? (
          <Card>
            <Empty
              title="No paper trades yet"
              hint="A paper trade opens only when a signal passes every alert gate and the risk limits allow it."
            />
          </Card>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Opened</th>
                  <th>Outcome</th>
                  <th>Status</th>
                  <th className="num">Wallet entry</th>
                  <th className="num">
                    <Tooltip text="Price the simulated order filled at, after delay, spread and slippage.">
                      <span>Fill</span>
                    </Tooltip>
                  </th>
                  <th className="num">Exit</th>
                  <th className="num">Stake</th>
                  <th className="num">P&L</th>
                  <th className="num">ROI</th>
                  <th className="num">vs wallet</th>
                  <th>Evidence</th>
                  <th>Exit reason</th>
                </tr>
              </thead>
              <tbody>
                {trades.data.map((t) => (
                  <tr key={t.id}>
                    <td className="faint">{ago(t.entered_at ?? t.signal_detected_at)}</td>
                    <td style={{ maxWidth: 220 }}>
                      <div style={{ fontWeight: 550 }}>{t.outcome_label ?? '—'}</div>
                      <div className="faint" style={{ fontSize: 11.5 }}>
                        {t.market_question ?? '—'}
                      </div>
                    </td>
                    <td>
                      <StatusBadge status={t.status} />
                      {t.stake_reduced_for_liquidity && (
                        <>
                          {' '}
                          <Badge tone="warn" title="Modelled depth could not absorb the full stake">
                            partial
                          </Badge>
                        </>
                      )}
                    </td>
                    <td className="num">{price(t.wallet_entry_price)}</td>
                    <td className="num">{price(t.fill_price)}</td>
                    <td className="num">{price(t.exit_price)}</td>
                    <td className="num">{money(t.stake_usdc, 0)}</td>
                    <td className={`num ${signClass(Number(t.realized_pnl ?? t.unrealized_pnl))}`}>
                      {money(t.realized_pnl ?? t.unrealized_pnl)}
                    </td>
                    <td className={`num ${signClass(t.roi)}`}>{pct(t.roi)}</td>
                    <td className={`num ${signClass(t.roi_gap_vs_wallet)}`}>
                      {t.roi_gap_vs_wallet === null ? '—' : pct(t.roi_gap_vs_wallet)}
                    </td>
                    <td>
                      <EvidenceBadge quality={t.price_source_quality} />
                    </td>
                    <td className="faint">
                      {t.rejection_reason ? (
                        <Badge tone="bad" title={t.notes ?? undefined}>
                          {humanize(t.rejection_reason)}
                        </Badge>
                      ) : (
                        humanize(t.exit_reason)
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  )
}
