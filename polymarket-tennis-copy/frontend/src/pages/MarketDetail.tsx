import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
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
  num,
  pct,
  price,
  ScoreBar,
  shortAddress,
  signClass,
  Stat,
  StatusBadge,
} from '../components/ui'
import type { MarketDetail as MarketDetailType } from '../types'

export default function MarketDetail() {
  const { id } = useParams()
  const marketId = Number(id)
  const detail = useApi(() => api.market(marketId), [marketId])

  if (detail.loading && !detail.data) return <Loading rows={6} />
  if (detail.error) return <ErrorNote message={detail.error} onRetry={detail.reload} />
  const d = detail.data
  if (!d) return null
  const m = d.market

  return (
    <>
      <div className="page-header">
        <div className="split" style={{ justifyContent: 'space-between' }}>
          <div>
            <h1>{m.question ?? m.condition_id}</h1>
            <p>
              {[m.tournament, m.tour, m.surface, m.best_of ? `best of ${m.best_of}` : null]
                .filter(Boolean)
                .join(' · ') || 'Tennis market'}
            </p>
          </div>
          <div className="hstack">
            <Badge tone="neutral">{humanize(m.tennis_market_type)}</Badge>
            {m.resolved ? (
              <Badge tone="neutral">resolved</Badge>
            ) : m.closed ? (
              <Badge tone="neutral">closed</Badge>
            ) : (
              <Badge tone="good">open</Badge>
            )}
            {m.needs_review && <Badge tone="warn">needs review</Badge>}
          </div>
        </div>
      </div>

      {m.needs_review && (
        <div style={{ marginBottom: 16 }}>
          <Notice tone="warn">
            This market's classification is uncertain ({m.classification_confidence.toFixed(0)}/100
            confidence). It is excluded from alerting until reviewed.
            {m.classification_notes ? ` ${m.classification_notes}` : ''}
          </Notice>
        </div>
      )}

      <div className="grid grid-4">
        <Stat
          label="Best bid / ask"
          value={`${price(m.best_bid)} / ${price(m.best_ask)}`}
          hint={m.spread === null ? undefined : `Spread ${Number(m.spread).toFixed(3)}`}
        />
        <Stat label="Liquidity" value={money(m.liquidity, 0)} hint="As reported by the venue" />
        <Stat label="24h volume" value={money(m.volume_24hr, 0)} />
        <Stat
          label="Classification"
          value={`${m.classification_confidence.toFixed(0)}/100`}
          hint={m.classification_methods.map(humanize).join(', ') || undefined}
          tooltip="How confident the classifier is that this is the tennis market type shown, and why."
        />
      </div>

      <div className="section grid grid-2">
        <Card
          title="Price history with wallet entries"
          subtitle="Tracked wallet buys and sells overlaid on observed prices"
          tooltip="Prices come from trade prints and 1-minute bars. Gaps mean no evidence was recorded, not that the price was flat."
        >
          <PriceChart detail={d} />
        </Card>

        <div className="vstack" style={{ gap: 14 }}>
          <Card title="Order book depth" tooltip="Depth near the touch is what a follower can actually take; total ladder depth flatters the market.">
            {d.liquidity ? (
              <dl className="kv">
                <dt>Observed</dt>
                <dd>{ago(d.liquidity.observed_at)}</dd>
                <dt>Midpoint</dt>
                <dd>{price(d.liquidity.midpoint)}</dd>
                <dt>Spread</dt>
                <dd>
                  {d.liquidity.spread === null ? '—' : Number(d.liquidity.spread).toFixed(3)}
                </dd>
                <dt>Ask depth within 1¢</dt>
                <dd>{money(d.liquidity.ask_depth_within_1c_usdc, 0)}</dd>
                <dt>Ask depth within 5¢</dt>
                <dd>{money(d.liquidity.ask_depth_within_5c_usdc, 0)}</dd>
                <dt>Total ask depth</dt>
                <dd className="faint">{money(d.liquidity.ask_depth_total_usdc, 0)}</dd>
              </dl>
            ) : (
              <Empty
                title="No depth snapshot"
                hint="Liquidity snapshots are captured for open markets during price backfill."
              />
            )}
          </Card>

          <Card title="Outcomes">
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Outcome</th>
                    <th className="num">Last price</th>
                    <th>Result</th>
                  </tr>
                </thead>
                <tbody>
                  {m.outcomes.map((o) => (
                    <tr key={o.token_id}>
                      <td>{o.label}</td>
                      <td className="num">{price(o.last_price)}</td>
                      <td>
                        {o.is_winner === null ? (
                          <span className="faint">—</span>
                        ) : o.is_winner ? (
                          <Badge tone="good">won</Badge>
                        ) : (
                          <Badge tone="neutral">lost</Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      </div>

      <div className="section grid grid-2">
        <Card title="Tracked wallet positions" subtitle="Currently open or partially closed">
          {!d.open_positions.length ? (
            <Empty title="No tracked wallet holds a position here" />
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Wallet</th>
                    <th className="num">Avg entry</th>
                    <th className="num">Shares</th>
                    <th className="num">Committed</th>
                    <th>Behaviour</th>
                  </tr>
                </thead>
                <tbody>
                  {d.open_positions.map((p, i) => (
                    <tr key={i}>
                      <td>
                        <Link to={`/wallets/${p.wallet_id}`} className="mono">
                          {p.address ? shortAddress(p.address) : `#${p.wallet_id}`}
                        </Link>
                      </td>
                      <td className="num">{price(p.avg_entry_price)}</td>
                      <td className="num">{num(Number(p.current_shares), 0)}</td>
                      <td className="num">{money(p.capital_committed, 0)}</td>
                      <td className="faint">{humanize(p.behaviour)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card title="Recent tracked transactions">
          {!d.wallet_activity.length ? (
            <Empty title="No tracked wallet activity in this market" />
          ) : (
            <div className="table-wrap scroll-y">
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Wallet</th>
                    <th>Side</th>
                    <th className="num">Price</th>
                    <th className="num">Size</th>
                  </tr>
                </thead>
                <tbody>
                  {[...d.wallet_activity].reverse().map((a, i) => (
                    <tr key={i}>
                      <td className="faint">
                        {new Date(a.timestamp * 1000).toLocaleTimeString()}
                      </td>
                      <td>
                        <Link to={`/wallets/${a.wallet_id}`} className="mono">
                          {a.nickname ?? (a.address ? shortAddress(a.address) : `#${a.wallet_id}`)}
                        </Link>
                      </td>
                      <td>
                        <Badge tone={a.side === 'BUY' ? 'good' : 'neutral'}>{a.side ?? '—'}</Badge>
                      </td>
                      <td className="num">{price(a.price)}</td>
                      <td className="num">{money(a.usdc_size, 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      <div className="section">
        <Card title="Alert qualification history" subtitle="Including candidates that were rejected">
          {!d.signals.length ? (
            <Empty title="No signals raised for this market" />
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Detected</th>
                    <th>Outcome</th>
                    <th>Status</th>
                    <th className="num">Wallets</th>
                    <th className="num">Entry</th>
                    <th className="num">Copyability</th>
                    <th>Why</th>
                  </tr>
                </thead>
                <tbody>
                  {d.signals.map((s) => (
                    <tr key={s.id}>
                      <td className="faint">{ago(s.detected_at)}</td>
                      <td>{s.outcome_label ?? '—'}</td>
                      <td>
                        <StatusBadge status={s.status} />
                      </td>
                      <td className="num">{s.wallet_count}</td>
                      <td className="num">{price(s.wallet_entry_price_median)}</td>
                      <td className="num">
                        <ScoreBar value={s.copyability_score} />
                      </td>
                      <td className="faint" style={{ maxWidth: 320, fontSize: 12 }}>
                        {s.rejection_reasons.length
                          ? s.rejection_reasons.map(humanize).join('; ')
                          : (s.explanation ?? '—')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      {d.paper_trades.length > 0 && (
        <div className="section">
          <Card title="Paper-trade history" subtitle="Simulation only">
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Opened</th>
                    <th>Status</th>
                    <th className="num">Fill</th>
                    <th className="num">Exit</th>
                    <th className="num">P&L</th>
                    <th className="num">ROI</th>
                    <th>Exit reason</th>
                  </tr>
                </thead>
                <tbody>
                  {d.paper_trades.map((t) => (
                    <tr key={t.id}>
                      <td className="faint">{ago(t.entered_at ?? t.signal_detected_at)}</td>
                      <td>
                        <StatusBadge status={t.status} />
                      </td>
                      <td className="num">{price(t.fill_price)}</td>
                      <td className="num">{price(t.exit_price)}</td>
                      <td className={`num ${signClass(Number(t.realized_pnl))}`}>
                        {money(t.realized_pnl)}
                      </td>
                      <td className={`num ${signClass(t.roi)}`}>{pct(t.roi)}</td>
                      <td className="faint">{humanize(t.exit_reason ?? t.rejection_reason)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </>
  )
}

/**
 * Price chart with wallet entry/exit markers.
 *
 * Each outcome token gets its own line; buys and sells are plotted as markers at
 * the price the wallet actually paid, which is what makes "the wallet got a
 * price nobody else could" visible at a glance.
 */
function PriceChart({ detail }: { detail: MarketDetailType }) {
  const { series, markers, bounds } = useMemo(() => {
    const byToken = new Map<string, Array<{ t: number; p: number }>>()
    for (const point of detail.price_history) {
      const list = byToken.get(point.token_id) ?? []
      list.push({ t: point.timestamp, p: Number(point.price) })
      byToken.set(point.token_id, list)
    }

    const all = [...byToken.values()].flat()
    const times = all.map((p) => p.t)
    const marks = detail.wallet_activity
      .filter((a) => a.price !== null && a.price !== undefined)
      .map((a) => ({ t: a.timestamp as number, p: Number(a.price), side: a.side as string }))

    return {
      series: [...byToken.entries()],
      markers: marks,
      bounds: {
        tMin: Math.min(...times, ...marks.map((m) => m.t)),
        tMax: Math.max(...times, ...marks.map((m) => m.t)),
      },
    }
  }, [detail])

  if (!detail.price_history.length) {
    return (
      <Empty
        title="No price observations stored"
        hint="Run the price-backfill job to fetch trade prints and 1-minute bars for this market."
      />
    )
  }

  const W = 800
  const H = 240
  const padL = 44
  const padR = 12
  const padT = 12
  const padB = 22
  const span = bounds.tMax - bounds.tMin || 1

  const sx = (t: number) => padL + ((t - bounds.tMin) / span) * (W - padL - padR)
  const sy = (p: number) => padT + (1 - p) * (H - padT - padB)

  const colors = ['var(--accent)', 'var(--warn)', 'var(--good)', 'var(--bad)']

  return (
    <>
      <svg
        className="chart"
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        style={{ height: H, width: '100%' }}
        role="img"
        aria-label="Price history with wallet entries"
      >
        {[0, 0.25, 0.5, 0.75, 1].map((p) => (
          <g key={p}>
            <line className="chart-grid" x1={padL} x2={W - padR} y1={sy(p)} y2={sy(p)} />
            <text className="chart-axis-label" x={padL - 6} y={sy(p) + 3} textAnchor="end">
              ${p.toFixed(2)}
            </text>
          </g>
        ))}

        {series.map(([token, points], i) => (
          <path
            key={token}
            d={points
              .sort((a, b) => a.t - b.t)
              .map((pt, j) => `${j === 0 ? 'M' : 'L'}${sx(pt.t)},${sy(pt.p)}`)
              .join(' ')}
            fill="none"
            stroke={colors[i % colors.length]}
            strokeWidth={1.6}
            vectorEffect="non-scaling-stroke"
            opacity={0.9}
          />
        ))}

        {markers.map((mk, i) => (
          <circle
            key={i}
            cx={sx(mk.t)}
            cy={sy(mk.p)}
            r={3.5}
            fill={mk.side === 'BUY' ? 'var(--good)' : 'var(--bad)'}
            stroke="var(--bg)"
            strokeWidth={1}
          >
            <title>{`${mk.side} at $${mk.p.toFixed(3)}`}</title>
          </circle>
        ))}

        <text className="chart-axis-label" x={padL} y={H - 4} textAnchor="start">
          {new Date(bounds.tMin * 1000).toLocaleString()}
        </text>
        <text className="chart-axis-label" x={W - padR} y={H - 4} textAnchor="end">
          {new Date(bounds.tMax * 1000).toLocaleString()}
        </text>
      </svg>

      <div className="chart-legend">
        {series.map(([token], i) => (
          <span key={token}>
            <span className="swatch" style={{ background: colors[i % colors.length] }} />
            {detail.market.outcomes.find((o) => o.token_id === token)?.label ?? 'price'}
          </span>
        ))}
        <span>
          <span
            className="swatch"
            style={{ background: 'var(--good)', width: 8, height: 8, borderRadius: '50%' }}
          />
          Wallet buy
        </span>
        <span>
          <span
            className="swatch"
            style={{ background: 'var(--bad)', width: 8, height: 8, borderRadius: '50%' }}
          />
          Wallet sell
        </span>
      </div>
    </>
  )
}
