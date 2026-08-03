import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, useApi } from '../api'
import {
  Badge,
  Card,
  Empty,
  ErrorNote,
  humanize,
  Loading,
  money,
  Notice,
  price,
  ScoreBar,
} from '../components/ui'

export default function Markets() {
  const [search, setSearch] = useState('')
  const [openOnly, setOpenOnly] = useState(true)
  const [marketType, setMarketType] = useState('')
  const [showReview, setShowReview] = useState(false)

  const markets = useApi(
    () =>
      api.markets({
        q: search || undefined,
        closed: openOnly ? false : undefined,
        market_type: marketType || undefined,
        limit: 200,
      }),
    [search, openOnly, marketType],
  )
  const review = useApi(() => api.reviewQueue(), [], {})

  const rows = showReview ? (review.data ?? []) : (markets.data ?? [])
  const loading = showReview ? review.loading : markets.loading
  const error = showReview ? review.error : markets.error

  return (
    <>
      <div className="page-header">
        <h1>Tennis markets</h1>
        <p>
          Markets are classified by official sports metadata, tags, event data and title parsing,
          each with a confidence score. Anything ambiguous is queued for review rather than silently
          trusted — a misclassified market would pollute every wallet metric that touches it.
        </p>
      </div>

      <div className="filters">
        <label className="field">
          <span>Search</span>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="player, tournament or question"
            disabled={showReview}
          />
        </label>
        <label className="field">
          <span>Market type</span>
          <select
            value={marketType}
            onChange={(e) => setMarketType(e.target.value)}
            disabled={showReview}
          >
            <option value="">All types</option>
            <option value="match_winner">Match winner</option>
            <option value="set_winner">Set winner</option>
            <option value="game_winner">Game winner</option>
            <option value="handicap">Handicap</option>
            <option value="total_games">Total games</option>
            <option value="completed_match">Completed match</option>
            <option value="tournament_future">Tournament future</option>
          </select>
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={openOnly}
            onChange={(e) => setOpenOnly(e.target.checked)}
            disabled={showReview}
          />
          Open markets only
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={showReview}
            onChange={(e) => setShowReview(e.target.checked)}
          />
          Review queue ({review.data?.length ?? 0})
        </label>
      </div>

      {showReview && (
        <div style={{ marginBottom: 14 }}>
          <Notice tone="warn">
            These markets were classified with low confidence or an unrecognised shape. They are
            excluded from alerting until reviewed.
          </Notice>
        </div>
      )}

      {error ? (
        <ErrorNote message={error} onRetry={showReview ? review.reload : markets.reload} />
      ) : loading && !rows.length ? (
        <Loading rows={5} />
      ) : !rows.length ? (
        <Card>
          <Empty
            title={showReview ? 'Review queue is empty' : 'No markets match'}
            hint={
              showReview
                ? 'Every classified market met the confidence threshold.'
                : 'Run the market sync job to ingest tennis events from Polymarket.'
            }
          />
        </Card>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Market</th>
                <th>Type</th>
                <th>Tour</th>
                <th>Starts</th>
                <th className="num">Best bid / ask</th>
                <th className="num">Liquidity</th>
                <th className="num">24h volume</th>
                <th className="num">Confidence</th>
                <th>State</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((m) => (
                <tr key={m.id}>
                  <td style={{ maxWidth: 300 }}>
                    <Link to={`/markets/${m.id}`}>{m.question ?? m.condition_id}</Link>
                    {m.tournament && (
                      <div className="faint" style={{ fontSize: 11.5 }}>
                        {m.tournament}
                        {m.best_of ? ` · best of ${m.best_of}` : ''}
                        {m.surface ? ` · ${m.surface}` : ''}
                      </div>
                    )}
                  </td>
                  <td>
                    <Badge tone="neutral">{humanize(m.tennis_market_type)}</Badge>
                  </td>
                  <td className="faint">{m.tour ?? '—'}</td>
                  <td className="faint">
                    {m.game_start_time ? new Date(m.game_start_time).toLocaleString() : '—'}
                  </td>
                  <td className="num">
                    {price(m.best_bid)} / {price(m.best_ask)}
                  </td>
                  <td className="num">{money(m.liquidity, 0)}</td>
                  <td className="num">{money(m.volume_24hr, 0)}</td>
                  <td className="num">
                    <ScoreBar value={m.classification_confidence} />
                  </td>
                  <td>
                    {m.resolved ? (
                      <Badge tone="neutral">resolved</Badge>
                    ) : m.closed ? (
                      <Badge tone="neutral">closed</Badge>
                    ) : (
                      <Badge tone="good">open</Badge>
                    )}
                    {m.needs_review && (
                      <>
                        {' '}
                        <Badge tone="warn">review</Badge>
                      </>
                    )}
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
