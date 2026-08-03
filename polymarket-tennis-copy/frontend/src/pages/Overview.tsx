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
  pct,
  price,
  ScoreBar,
  signClass,
  Stat,
  StatusBadge,
} from '../components/ui'

export default function Overview() {
  const overview = useApi(() => api.overview(), [], { pollMs: 30_000 })
  const signals = useApi(() => api.signals({ limit: 8, hours: 48 }), [], { pollMs: 20_000 })
  const quality = useApi(() => api.dataQuality(), [])

  if (overview.loading && !overview.data) return <Loading rows={5} />
  if (overview.error) return <ErrorNote message={overview.error} onRetry={overview.reload} />
  const o = overview.data
  if (!o) return null

  const noWallets = o.wallets_tracked === 0

  return (
    <>
      <div className="page-header">
        <h1>Overview</h1>
        <p>
          The question here is not whether these wallets made money, but whether a follower
          arriving {o.benchmark_delay_seconds} seconds late could still have made money copying
          them.
        </p>
      </div>

      {noWallets && (
        <div style={{ marginBottom: 16 }}>
          <Notice tone="info">
            No wallets are being tracked yet. Add one on the{' '}
            <Link to="/wallets">Wallets</Link> page, import a CSV, or run discovery — then sync it
            to build history. Nothing is scored until a wallet has enough completed tennis trades.
          </Notice>
        </div>
      )}

      <div className="grid grid-4">
        <Stat
          label="Wallets tracked"
          value={o.wallets_tracked}
          hint={`${o.wallets_approved} approved · ${o.wallets_qualified} qualified`}
          tooltip="Qualified means the wallet currently passes every hard alert gate: sample size, skill score, copyable edge, drawdown and data confidence."
        />
        <Stat
          label="Median copyable ROI"
          value={o.median_qualified_copyable_roi === null ? 'n/a' : pct(o.median_qualified_copyable_roi)}
          tone={signClass(o.median_qualified_copyable_roi) as 'pos' | 'neg' | ''}
          hint={`Across qualified wallets, at ${o.benchmark_delay_seconds}s delay`}
          tooltip="Median return a delayed follower would have achieved. 'n/a' means no qualified wallet has enough price evidence to measure it honestly."
        />
        <Stat
          label="Active signals"
          value={o.active_signals}
          hint={`${o.qualified_signals_today} qualified / ${o.signals_today} seen today`}
          tooltip="Signals currently qualified or already paper-entered."
        />
        <Stat
          label="Rejected today"
          value={o.rejected_signals_today}
          hint="Filtered out by the alert gates"
          tooltip="Rejections are kept on purpose. Reading why candidates fail is how you calibrate the thresholds."
        />
      </div>

      <div className="section">
        <div className="section-title">
          <h2>Paper trading</h2>
          <Badge tone="neutral">Simulation only</Badge>
        </div>
        <div className="grid grid-4">
          <Stat
            label="Realised P&L"
            value={money(o.paper_realized_pnl)}
            tone={signClass(Number(o.paper_realized_pnl)) as 'pos' | 'neg' | ''}
            hint={`Unrealised ${money(o.paper_unrealized_pnl)}`}
          />
          <Stat
            label="Paper ROI"
            value={o.paper_roi === null ? '—' : pct(o.paper_roi)}
            tone={signClass(o.paper_roi) as 'pos' | 'neg' | ''}
            hint="Return on simulated capital staked"
          />
          <Stat
            label="Win rate"
            value={o.paper_win_rate === null ? '—' : pct(o.paper_win_rate, 0)}
            hint={`${o.paper_open_positions} open positions`}
            tooltip="Win rate alone is not evidence of edge: winning often at $0.95 can still lose money."
          />
          <Stat
            label="Current drawdown"
            value={o.current_drawdown === null ? '—' : pct(o.current_drawdown)}
            tone={o.current_drawdown && o.current_drawdown > 0.2 ? 'neg' : ''}
            hint="Peak-to-trough on simulated equity"
          />
        </div>
      </div>

      <div className="section grid grid-2">
        <Card
          title="Recent qualifying activity"
          subtitle="Newest candidates, including the ones that were filtered out"
          actions={<Link to="/signals" className="btn btn-sm">Open feed</Link>}
        >
          {signals.loading && !signals.data ? (
            <Loading />
          ) : !signals.data?.length ? (
            <Empty
              title="No candidate signals yet"
              hint="Signals appear once tracked wallets with computed scores trade a classified tennis market."
            />
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Outcome</th>
                    <th>Status</th>
                    <th className="num">Wallet entry</th>
                    <th className="num">Now</th>
                    <th className="num">Copyability</th>
                    <th>Age</th>
                  </tr>
                </thead>
                <tbody>
                  {signals.data.map((s) => (
                    <tr key={s.id}>
                      <td>
                        <div style={{ fontWeight: 550 }}>{s.outcome_label ?? '—'}</div>
                        <div className="faint" style={{ fontSize: 11.5 }}>
                          {s.market_question ?? '—'}
                        </div>
                      </td>
                      <td>
                        <StatusBadge status={s.status} />
                      </td>
                      <td className="num">{price(s.wallet_entry_price_median)}</td>
                      <td className="num">{price(s.current_price)}</td>
                      <td className="num">
                        <ScoreBar value={s.copyability_score} />
                      </td>
                      <td className="faint">{ago(s.detected_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <div className="vstack" style={{ gap: 14 }}>
          <Card title="Data freshness">
            <dl className="kv">
              <dt>Markets synced</dt>
              <dd>{ago(o.last_market_sync)}</dd>
              <dt>Wallets synced</dt>
              <dd>{ago(o.last_wallet_sync)}</dd>
              <dt>Tennis markets</dt>
              <dd>
                {o.tennis_markets_tracked.toLocaleString()}{' '}
                <span className="faint">({o.tennis_markets_open} open)</span>
              </dd>
              <dt>Benchmark delay</dt>
              <dd>{o.benchmark_delay_seconds}s</dd>
            </dl>
          </Card>

          <Card
            title="Data quality"
            actions={<Link to="/health" className="btn btn-sm">Details</Link>}
          >
            {quality.loading && !quality.data ? (
              <Loading rows={2} />
            ) : quality.data ? (
              <>
                <dl className="kv">
                  <dt>Avg price confidence</dt>
                  <dd>
                    {quality.data.avg_data_confidence === null
                      ? '—'
                      : `${quality.data.avg_data_confidence.toFixed(0)}/100`}
                  </dd>
                  <dt>Markets to review</dt>
                  <dd>{quality.data.markets_needing_review}</dd>
                  <dt>Positions tracked</dt>
                  <dd>{quality.data.positions_total.toLocaleString()}</dd>
                </dl>
                {quality.data.warnings.length > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <Notice tone="warn">
                      <ul style={{ margin: 0, paddingLeft: 16 }}>
                        {quality.data.warnings.slice(0, 3).map((w) => (
                          <li key={w}>{w}</li>
                        ))}
                      </ul>
                    </Notice>
                  </div>
                )}
              </>
            ) : null}
          </Card>
        </div>
      </div>

      <div className="section">
        <Notice tone="info">{o.disclaimer}</Notice>
      </div>
    </>
  )
}
