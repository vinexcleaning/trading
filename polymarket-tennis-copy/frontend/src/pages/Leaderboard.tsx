import { useState } from 'react'
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
  RiskFlags,
  ScoreBar,
  shortAddress,
  signClass,
  Tooltip,
} from '../components/ui'

/** Several rankings, deliberately. One list would imply a single answer. */
const RANKING_KEYS = [
  'best_overall',
  'best_copyable',
  'best_live',
  'best_prematch',
  'best_match_winner',
  'best_set_market',
  'best_recent',
  'most_consistent',
  'highest_confidence',
  'highest_raw_profit',
  'highest_adjusted_roi',
  'lowest_drawdown',
  'watchlist',
  'emerging',
]

export default function Leaderboard() {
  const [selected, setSelected] = useState('best_copyable')
  const [qualifiedOnly, setQualifiedOnly] = useState(false)
  const [minSample, setMinSample] = useState(0)

  const rankings = useApi(
    () =>
      api.rankings({
        keys: RANKING_KEYS.join(','),
        limit: 50,
        qualified_only: qualifiedOnly,
        min_sample: minSample,
      }),
    [qualifiedOnly, minSample],
  )

  const active = rankings.data?.find((r) => r.key === selected) ?? rankings.data?.[0]

  return (
    <>
      <div className="page-header">
        <h1>Wallet leaderboard</h1>
        <p>
          Ranked by realistically copyable performance, not raw profit. A wallet with eight lucky
          wins should not outrank one with three hundred consistent, copyable trades — the scoring
          shrinks small samples toward the population mean to make sure it doesn't.
        </p>
      </div>

      <div className="filters">
        <label className="field">
          <span>Ranking</span>
          <select value={selected} onChange={(e) => setSelected(e.target.value)}>
            {(rankings.data ?? []).map((r) => (
              <option key={r.key} value={r.key}>
                {r.label}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Minimum completed trades</span>
          <select value={minSample} onChange={(e) => setMinSample(Number(e.target.value))}>
            <option value={0}>Any</option>
            <option value={20}>20+</option>
            <option value={30}>30+</option>
            <option value={100}>100+</option>
          </select>
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={qualifiedOnly}
            onChange={(e) => setQualifiedOnly(e.target.checked)}
          />
          Alert-qualified only
        </label>
      </div>

      {rankings.error ? (
        <ErrorNote message={rankings.error} onRetry={rankings.reload} />
      ) : rankings.loading && !rankings.data ? (
        <Loading rows={6} />
      ) : !active ? (
        <Card>
          <Empty title="No rankings available" />
        </Card>
      ) : (
        <>
          <div style={{ marginBottom: 14 }}>
            <Notice tone="warn">{active.caveat}</Notice>
          </div>

          {!active.rows.length ? (
            <Card>
              <Empty
                title="No wallets in this ranking yet"
                hint="Wallets appear once they have been synced and scored. Add wallets, sync them, then run the analytics job."
              />
            </Card>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Wallet</th>
                    <th className="num">
                      <Tooltip text="Adjusted Tennis Skill Score: copyable return, sample confidence, consistency, drawdown, recency, liquidity fit, concentration and data quality — with penalties applied.">
                        <span>Skill</span>
                      </Tooltip>
                    </th>
                    <th className="num">Trades</th>
                    <th className="num">Raw ROI</th>
                    <th className="num">
                      <Tooltip text="Return for a follower entering after the benchmark delay, with modelled slippage.">
                        <span>Copyable ROI</span>
                      </Tooltip>
                    </th>
                    <th className="num">
                      <Tooltip text="Copyable ROI shrunk toward the population mean by sample size. This is the honest estimate for a small sample.">
                        <span>Shrunk</span>
                      </Tooltip>
                    </th>
                    <th className="num">Coverage</th>
                    <th className="num">Net P&L</th>
                    <th className="num">Max DD</th>
                    <th>Confidence</th>
                    <th>Risk flags</th>
                    <th>Last seen</th>
                  </tr>
                </thead>
                <tbody>
                  {active.rows.map((row) => (
                    <tr key={row.wallet_id}>
                      <td className="faint">{row.rank}</td>
                      <td>
                        <Link to={`/wallets/${row.wallet_id}`}>
                          {row.nickname ?? <span className="mono">{shortAddress(row.address)}</span>}
                        </Link>
                        {row.qualified && (
                          <>
                            {' '}
                            <Badge tone="good">qualified</Badge>
                          </>
                        )}
                        {row.cluster_id && (
                          <>
                            {' '}
                            <Badge tone="warn" title="Shares behaviour with another tracked wallet">
                              cluster {row.cluster_id}
                            </Badge>
                          </>
                        )}
                      </td>
                      <td className="num">
                        <ScoreBar value={row.skill_score} />
                      </td>
                      <td className="num">{row.completed_positions}</td>
                      <td className={`num ${signClass(row.roi)}`}>{pct(row.roi)}</td>
                      <td className={`num ${signClass(row.copyable_roi)}`}>
                        {row.copyable_roi === null ? (
                          <span className="faint" title="Not enough price evidence">
                            n/a
                          </span>
                        ) : (
                          pct(row.copyable_roi)
                        )}
                      </td>
                      <td className={`num ${signClass(row.shrunk_copyable_roi)}`}>
                        {row.shrunk_copyable_roi === null ? '—' : pct(row.shrunk_copyable_roi)}
                      </td>
                      <td className="num">
                        <span
                          style={{
                            color:
                              row.copyable_coverage !== null && row.copyable_coverage < 0.5
                                ? 'var(--warn)'
                                : undefined,
                          }}
                        >
                          {row.copyable_coverage === null ? '—' : pct(row.copyable_coverage, 0)}
                        </span>
                      </td>
                      <td className={`num ${signClass(Number(row.net_profit))}`}>
                        {money(row.net_profit, 0)}
                      </td>
                      <td className="num">{row.max_drawdown === null ? '—' : pct(row.max_drawdown, 0)}</td>
                      <td>
                        <ConfidenceBadge level={row.confidence_level} />
                      </td>
                      <td>
                        <RiskFlags flags={row.risk_flags} max={2} />
                      </td>
                      <td className="faint">{ago(row.last_activity_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="section">
            <Card title="How to read this table">
              <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--text-dim)', fontSize: 13 }}>
                <li>
                  <strong>Raw vs copyable</strong> is the whole point. A large gap means the wallet's
                  edge evaporates by the time a follower can act.
                </li>
                <li>
                  <strong>Coverage</strong> below 50% means the copyable figure rests on a minority of
                  trades — treat it as indicative, not measured.
                </li>
                <li>
                  <strong>n/a copyable ROI</strong> is deliberate: without sufficient price evidence
                  the system refuses to invent a number.
                </li>
                <li>
                  <strong>Cluster badges</strong> mean the wallet may not be an independent opinion.
                </li>
              </ul>
            </Card>
          </div>
        </>
      )}
    </>
  )
}

function ConfidenceBadge({ level }: { level: string }) {
  const tone =
    level === 'high' ? 'good' : level === 'moderate' ? 'info' : level === 'low' ? 'warn' : 'neutral'
  return <Badge tone={tone as never}>{level}</Badge>
}
