import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, useApi } from '../api'
import {
  ago,
  Badge,
  BarChart,
  Card,
  duration,
  Empty,
  ErrorNote,
  humanize,
  LineChart,
  Loading,
  money,
  Notice,
  num,
  pct,
  price,
  RawVsCopyable,
  RiskFlags,
  ScoreBar,
  shortAddress,
  signClass,
  Stat,
  StatusBadge,
  Tooltip,
} from '../components/ui'
import type { Position, WalletMetrics } from '../types'

const SCORE_COMPONENT_HELP: Record<string, string> = {
  copyable_roi: 'Return achievable by a delayed follower, shrunk for sample size.',
  profit_factor: 'Gross profit divided by gross loss.',
  sample_confidence: 'How much the record can be trusted given the number of completed trades.',
  consistency: 'Stability of results across time periods and market types.',
  drawdown: 'Penalty for large peak-to-trough declines.',
  recency: 'Weighting toward recent performance.',
  liquidity_fit: 'Whether the wallet trades in markets deep enough to copy.',
  concentration: 'Penalty for profit depending on one or two trades.',
  data_quality: 'Strength of the price evidence behind the copyable figures.',
}

export default function WalletDetail() {
  const { id } = useParams()
  const walletId = Number(id)
  const [tab, setTab] = useState<'positions' | 'activity'>('positions')

  const detail = useApi(() => api.wallet(walletId), [walletId])
  const positions = useApi(
    () => api.walletPositions(walletId, { tennis_only: true, limit: 300 }),
    [walletId],
  )
  const activity = useApi(
    () => api.walletActivity(walletId, { tennis_only: true, limit: 200 }),
    [walletId],
  )

  if (detail.loading && !detail.data) return <Loading rows={6} />
  if (detail.error) return <ErrorNote message={detail.error} onRetry={detail.reload} />
  const d = detail.data
  if (!d) return null

  const tennis: WalletMetrics | undefined = d.metrics.tennis
  const score = d.score
  const profile = d.behavioural_profile ?? {}

  return (
    <>
      <div className="page-header">
        <div className="split" style={{ justifyContent: 'space-between' }}>
          <div>
            <h1>{d.wallet.nickname ?? shortAddress(d.wallet.address)}</h1>
            <p className="mono faint" style={{ marginTop: 4 }}>
              {d.wallet.address}
            </p>
          </div>
          <div className="hstack">
            <StatusBadge status={d.wallet.status} />
            {score?.qualified ? (
              <Badge tone="good">Alert-qualified</Badge>
            ) : (
              <Badge tone="neutral">Not qualified</Badge>
            )}
          </div>
        </div>
      </div>

      {!tennis && (
        <div style={{ marginBottom: 16 }}>
          <Notice tone="warn">
            No tennis metrics computed yet. Sync this wallet and run the analytics job — metrics
            appear once its activity has been reconstructed into positions.
          </Notice>
        </div>
      )}

      {score?.disqualification_reasons?.length ? (
        <div style={{ marginBottom: 16 }}>
          <Notice tone="warn">
            <strong>Not eligible for alerts.</strong>{' '}
            {score.disqualification_reasons.map(humanize).join('; ')}.
          </Notice>
        </div>
      ) : null}

      {tennis && (
        <Card title="Raw versus copyable" tooltip="The comparison this product exists to make.">
          <RawVsCopyable
            raw={tennis.roi}
            copyable={tennis.copyable_roi}
            coverage={tennis.copyable_coverage}
            delaySeconds={tennis.benchmark_delay_seconds}
          />
          {tennis.copyable_roi === null && (
            <div style={{ marginTop: 12 }}>
              <Notice tone="warn">
                Copyable ROI is unavailable: too few of this wallet's trades have price evidence
                strong enough to model a follower's fill. Running the price-backfill job for the
                markets it trades will populate this.
              </Notice>
            </div>
          )}
        </Card>
      )}

      {tennis && (
        <div className="section grid grid-4">
          <Stat
            label="Skill score"
            value={score ? score.skill_score.toFixed(1) : '—'}
            hint={score ? `${score.confidence_level} confidence` : undefined}
            tooltip="Adjusted Tennis Skill Score, 0-100. Every component is shown below."
          />
          <Stat
            label="Completed trades"
            value={tennis.completed_positions}
            hint={`${tennis.open_positions} open · ${tennis.total_positions} total`}
          />
          <Stat
            label="Net profit"
            value={money(tennis.net_profit)}
            tone={signClass(Number(tennis.net_profit)) as 'pos' | 'neg' | ''}
            hint={`Volume ${money(tennis.volume_usdc, 0)}`}
          />
          <Stat
            label="Win rate"
            value={pct(tennis.win_rate, 0)}
            hint={`Profit factor ${num(tennis.profit_factor, 2)}`}
            tooltip="Win rate is not edge. A wallet winning 90% of the time at $0.95 can still lose money."
          />
          <Stat
            label="Max drawdown"
            value={pct(tennis.max_drawdown, 0)}
            hint={money(tennis.max_drawdown_usdc, 0)}
          />
          <Stat
            label="Hold before selling"
            value={duration(profile.median_hold_seconds_traded_out)}
            hint={
              profile.pct_held_to_settlement
                ? `${pct(profile.pct_held_to_settlement, 0)} held to settlement instead`
                : `Avg entry ${price(tennis.avg_entry_price)}`
            }
            tooltip="Median time held before actually selling out. Positions held to settlement are counted separately, because their close is timed to settlement bookkeeping (days after the match) rather than a trading decision."
          />
          <Stat
            label="Profit concentration"
            value={pct(tennis.pct_profit_from_largest_trade, 0)}
            hint={`Top 5 trades: ${pct(tennis.pct_profit_from_top5_trades, 0)}`}
            tooltip="Share of total profit from the single best trade. High values mean the record depends on an outlier."
          />
          <Stat
            label="P(positive edge)"
            value={tennis.prob_positive_edge === null ? 'withheld' : pct(tennis.prob_positive_edge, 0)}
            hint={
              tennis.prob_positive_edge === null
                ? 'Sample too small to estimate'
                : 'Bootstrap estimate'
            }
            tooltip="Bootstrap probability that the wallet's copyable edge is genuinely positive. Withheld on small samples, where it would be meaningless."
          />
        </div>
      )}

      {tennis && (
        <div className="section grid grid-2">
          <Card
            title="Performance by follower delay"
            subtitle="How quickly the edge decays once you are late"
            tooltip="Each point is the ROI a follower would have achieved entering after that delay. 0s is theoretical only."
          >
            <DelayChart metrics={tennis} />
          </Card>

          {score && (
            <Card title="Score breakdown" subtitle={`Formula ${score.formula_version}`}>
              <BarChart
                data={Object.entries(score.components).map(([key, value]) => ({
                  label: humanize(key),
                  value: value as number,
                  hint: SCORE_COMPONENT_HELP[key],
                }))}
                format={(v) => v.toFixed(0)}
                colorFor={(v) => (v >= 75 ? 'var(--good)' : v >= 50 ? 'var(--warn)' : 'var(--bad)')}
              />
              <div style={{ marginTop: 14 }}>
                <dl className="kv">
                  <dt>Base score</dt>
                  <dd>{score.base_score.toFixed(1)}</dd>
                  <dt>Penalty multiplier</dt>
                  <dd className={score.total_penalty_multiplier < 1 ? 'neg' : ''}>
                    ×{score.total_penalty_multiplier.toFixed(3)}
                  </dd>
                  <dt>Final score</dt>
                  <dd style={{ fontWeight: 600 }}>{score.skill_score.toFixed(1)}</dd>
                </dl>
                {Object.keys(score.penalties_applied ?? {}).length > 0 && (
                  <div style={{ marginTop: 10 }}>
                    <div className="stat-label" style={{ marginBottom: 5 }}>
                      Penalties applied
                    </div>
                    <div className="flag-list">
                      {Object.entries(score.penalties_applied).map(([key, value]) => (
                        <Badge key={key} tone="warn">
                          {humanize(key)} ×{Number(value).toFixed(2)}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                {score.explanation && (
                  <div style={{ marginTop: 12 }}>
                    <Notice tone="info">{score.explanation}</Notice>
                  </div>
                )}
              </div>
            </Card>
          )}
        </div>
      )}

      {tennis && (
        <div className="section grid grid-2">
          <Card title="Cumulative profit" subtitle="Completed tennis positions, in order">
            <EquityCurve positions={positions.data ?? []} />
          </Card>
          <Card title="Performance by market type">
            <BreakdownTable data={tennis.performance_by_market_type} />
          </Card>
        </div>
      )}

      <div className="section grid grid-2">
        <Card title="Behavioural profile" subtitle="Descriptive, not a verdict">
          {profile.positions ? (
            <dl className="kv">
              <dt>Median position</dt>
              <dd>{money(profile.median_position_usdc, 0)}</dd>
              <dt>Largest position</dt>
              <dd>{money(profile.largest_position_usdc, 0)}</dd>
              <dt>
                Median hold before selling{' '}
                <Tooltip text="Only positions the wallet actually sold out of. Settlement closes are excluded because their timestamp reflects redemption bookkeeping, not a trading decision." />
              </dt>
              <dd>{duration(profile.median_hold_seconds_traded_out)}</dd>
              <dt>Traded out / held to settlement</dt>
              <dd>
                {profile.positions_traded_out ?? 0} / {profile.positions_held_to_settlement ?? 0}
              </dd>
              <dt>Scales into positions</dt>
              <dd>{pct(profile.scales_into_positions, 0)}</dd>
              <dt>Averages down</dt>
              <dd>{pct(profile.averages_down, 0)}</dd>
              <dt>Holds both outcomes</dt>
              <dd>
                {pct(profile.holds_both_outcomes, 0)}{' '}
                <Tooltip text="Holding both sides can indicate hedging or market-making rather than a directional view." />
              </dd>
              <dt>Large trades better?</dt>
              <dd>
                {profile.large_trades_outperform === null ||
                profile.large_trades_outperform === undefined ? (
                  '—'
                ) : profile.large_trades_outperform ? (
                  <Badge tone="good">yes</Badge>
                ) : (
                  <Badge tone="neutral">no</Badge>
                )}
              </dd>
            </dl>
          ) : (
            <Empty title="No reconstructed positions yet" />
          )}
        </Card>

        <div className="vstack" style={{ gap: 14 }}>
          <Card title="Risk flags">
            <RiskFlags flags={score?.risk_flags ?? d.wallet.risk_flags ?? []} />
          </Card>

          <Card
            title="Possible wallet relationships"
            tooltip="Related wallets are not independent confirmations. Three addresses run by one person is one opinion."
          >
            {d.cluster ? (
              <>
                <div className="hstack" style={{ marginBottom: 10 }}>
                  <Badge tone="warn">{humanize(d.cluster.relation)}</Badge>
                  <span className="faint">confidence {d.cluster.confidence.toFixed(0)}%</span>
                </div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Wallet</th>
                        <th className="num">Shared markets</th>
                        <th className="num">Overlap</th>
                        <th className="num">Timing</th>
                      </tr>
                    </thead>
                    <tbody>
                      {d.cluster.members.map((m) => (
                        <tr key={m.wallet_id}>
                          <td>
                            <Link to={`/wallets/${m.wallet_id}`} className="mono">
                              {shortAddress(m.address)}
                            </Link>
                          </td>
                          <td className="num">{m.shared_market_count}</td>
                          <td className="num">{pct(m.jaccard_similarity, 0)}</td>
                          <td className="num">{pct(m.timing_correlation, 0)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {d.cluster.evidence && (
                  <div style={{ marginTop: 10 }} className="faint">
                    {d.cluster.evidence}
                  </div>
                )}
              </>
            ) : (
              <Empty
                title="No related wallets detected"
                hint="Absence of evidence is not evidence of independence — only that no shared pattern was found among tracked wallets."
              />
            )}
          </Card>

          <Card title="Data quality">
            <dl className="kv">
              <dt>Backfill complete</dt>
              <dd>{d.wallet.backfill_complete ? 'yes' : 'no'}</dd>
              <dt>Last sync</dt>
              <dd>{ago(d.wallet.last_sync_success_at)}</dd>
              <dt>Evidence coverage</dt>
              <dd>{tennis ? pct(tennis.copyable_coverage, 0) : '—'}</dd>
              <dt>Data quality score</dt>
              <dd>{tennis?.data_quality_score === null || !tennis ? '—' : `${tennis.data_quality_score?.toFixed(0)}/100`}</dd>
            </dl>
            {d.wallet.last_sync_error && (
              <div style={{ marginTop: 10 }}>
                <Notice tone="bad">{d.wallet.last_sync_error}</Notice>
              </div>
            )}
          </Card>
        </div>
      </div>

      <div className="section">
        <div className="section-title">
          <button
            className={`btn btn-sm ${tab === 'positions' ? 'btn-primary' : ''}`}
            onClick={() => setTab('positions')}
          >
            Positions
          </button>
          <button
            className={`btn btn-sm ${tab === 'activity' ? 'btn-primary' : ''}`}
            onClick={() => setTab('activity')}
          >
            Raw activity
          </button>
        </div>

        {tab === 'positions' ? (
          positions.loading && !positions.data ? (
            <Loading rows={4} />
          ) : !positions.data?.length ? (
            <Card>
              <Empty title="No reconstructed tennis positions" />
            </Card>
          ) : (
            <PositionsTable positions={positions.data} />
          )
        ) : activity.loading && !activity.data ? (
          <Loading rows={4} />
        ) : !activity.data?.length ? (
          <Card>
            <Empty title="No tennis activity recorded" />
          </Card>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Market</th>
                  <th>Outcome</th>
                  <th>Side</th>
                  <th className="num">Price</th>
                  <th className="num">Size</th>
                  <th>Phase</th>
                </tr>
              </thead>
              <tbody>
                {activity.data.map((t) => (
                  <tr key={t.id}>
                    <td className="faint">{ago(t.occurred_at)}</td>
                    <td>{t.market_question ?? '—'}</td>
                    <td>{t.outcome_label ?? '—'}</td>
                    <td>
                      <Badge tone={t.side === 'BUY' ? 'good' : 'neutral'}>{t.side ?? '—'}</Badge>
                    </td>
                    <td className="num">{price(t.price)}</td>
                    <td className="num">{money(t.usdc_size, 0)}</td>
                    <td className="faint">{humanize(t.market_phase)}</td>
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

function DelayChart({ metrics }: { metrics: WalletMetrics }) {
  const { points, excluded, sample } = useMemo(() => {
    const entries = Object.entries(metrics.roi_by_delay ?? {})
      .map(([delay, breakdown]) => ({
        x: Number(delay),
        y: breakdown?.roi ?? null,
        excluded: breakdown?.excluded_weak_evidence ?? 0,
        n: breakdown?.n ?? 0,
      }))
      .filter((p) => p.y !== null && Number.isFinite(p.x) && Number.isFinite(p.y as number))
      .sort((a, b) => a.x - b.x)

    return {
      points: entries.map((e) => ({ x: e.x, y: e.y as number })),
      excluded: Math.max(0, ...entries.map((e) => e.excluded)),
      sample: entries.length ? entries[entries.length - 1].n : 0,
    }
  }, [metrics.roi_by_delay])

  if (points.length < 2) {
    return (
      <Empty
        title="Not enough delay data"
        hint="Delay curves need price evidence around each entry. Run the price-backfill job for this wallet's markets."
      />
    )
  }

  const first = points[0].y
  const benchmark = points.find((p) => p.x === metrics.benchmark_delay_seconds)?.y

  return (
    <>
      <LineChart
        series={points}
        zeroLine
        yFormat={(v) => `${(v * 100).toFixed(0)}%`}
        xFormat={(v) => `${v}s`}
        color="var(--accent)"
        ariaLabel="ROI by follower delay"
      />
      <div className="chart-legend">
        <span>
          <span className="swatch" style={{ background: 'var(--accent)' }} /> ROI at delay
        </span>
        <span className="faint">
          Benchmark {metrics.benchmark_delay_seconds}s
          {benchmark !== undefined && first !== undefined
            ? ` · costs ${pct(first - benchmark)} versus instant`
            : ''}{' '}
          · 0s is theoretical only
        </span>
        <span className="faint">
          {sample} trades{excluded > 0 ? ` · ${excluded} excluded for weak evidence` : ''}
        </span>
      </div>
    </>
  )
}

function EquityCurve({ positions }: { positions: Position[] }) {
  const points = useMemo(() => {
    const closed = positions
      .filter((p) => p.closed_at && p.net_pnl !== null)
      .sort((a, b) => new Date(a.closed_at!).getTime() - new Date(b.closed_at!).getTime())
    let total = 0
    return closed.map((p, i) => {
      total += Number(p.net_pnl ?? 0)
      return { x: i + 1, y: total }
    })
  }, [positions])

  if (points.length < 2) return <Empty title="Not enough closed positions to plot" />

  const final = points[points.length - 1].y
  return (
    <>
      <LineChart
        series={points}
        zeroLine
        color={final >= 0 ? 'var(--good)' : 'var(--bad)'}
        yFormat={(v) => `$${v.toFixed(0)}`}
        xFormat={(v) => `#${v.toFixed(0)}`}
        ariaLabel="Cumulative profit"
      />
      <div className="chart-legend">
        <span className="faint">
          {points.length} closed positions · final {money(final)}
        </span>
      </div>
    </>
  )
}

function BreakdownTable({ data }: { data: Record<string, any> }) {
  const rows = Object.entries(data ?? {})
  if (!rows.length) return <Empty title="No breakdown available" />

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Segment</th>
            <th className="num">Trades</th>
            <th className="num">ROI</th>
            <th className="num">Net P&L</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([key, value]) => (
            <tr key={key}>
              <td>{humanize(key)}</td>
              <td className="num">{value?.trades ?? value?.count ?? '—'}</td>
              <td className={`num ${signClass(value?.roi)}`}>{pct(value?.roi)}</td>
              <td className={`num ${signClass(Number(value?.net_profit))}`}>
                {money(value?.net_profit, 0)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function PositionsTable({ positions }: { positions: Position[] }) {
  const benchmark = (p: Position) =>
    p.copyability.find((c) => c.delay_seconds === 15) ?? p.copyability[0]

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Market</th>
            <th>Outcome</th>
            <th>Status</th>
            <th className="num">Entry</th>
            <th className="num">Exit</th>
            <th className="num">Size</th>
            <th className="num">Net P&L</th>
            <th className="num">ROI</th>
            <th className="num">
              <Tooltip text="Follower ROI at the benchmark delay, after modelled slippage.">
                <span>Copyable ROI</span>
              </Tooltip>
            </th>
            <th className="num">Copyability</th>
            <th>Evidence</th>
            <th>Behaviour</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((p) => {
            const c = benchmark(p)
            return (
              <tr key={p.id}>
                <td style={{ maxWidth: 240 }}>{p.market_question ?? '—'}</td>
                <td>{p.outcome_label ?? '—'}</td>
                <td>
                  <StatusBadge status={p.status} />
                </td>
                <td className="num">{price(p.avg_entry_price)}</td>
                <td className="num">{price(p.avg_exit_price)}</td>
                <td className="num">{money(p.capital_committed, 0)}</td>
                <td className={`num ${signClass(Number(p.net_pnl))}`}>{money(p.net_pnl)}</td>
                <td className={`num ${signClass(p.roi)}`}>{pct(p.roi)}</td>
                <td className={`num ${signClass(c?.follower_roi ?? null)}`}>
                  {c?.follower_roi === null || c?.follower_roi === undefined
                    ? '—'
                    : pct(c.follower_roi)}
                </td>
                <td className="num">
                  <ScoreBar value={c?.copyability_score ?? null} />
                </td>
                <td>
                  <EvidenceBadge quality={c?.price_source_quality ?? null} />
                </td>
                <td className="faint">{humanize(p.behaviour)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export function EvidenceBadge({ quality }: { quality: string | null }) {
  if (!quality) return <span className="faint">—</span>
  const tone =
    quality === 'observed_trade'
      ? 'good'
      : quality === 'interpolated_trade' || quality === 'minute_bar'
        ? 'info'
        : 'warn'
  const help: Record<string, string> = {
    observed_trade: 'A real trade print at the target time. Strongest evidence.',
    interpolated_trade: 'Between two real prints.',
    minute_bar: 'From 1-minute price history — the finest the platform provides.',
    nearest_trade: 'Closest print, outside the tolerance window. Weak.',
    modeled: 'Heuristic estimate, not an observation. Excluded from headline copyable ROI.',
    unavailable: 'No usable price evidence.',
  }
  return (
    <Badge tone={tone as never} title={help[quality] ?? quality}>
      {humanize(quality)}
    </Badge>
  )
}
