import { useState } from 'react'
import { api, useApi } from '../api'
import {
  ago,
  Badge,
  BarChart,
  Card,
  Empty,
  ErrorNote,
  humanize,
  Loading,
  Notice,
  Stat,
  StatusBadge,
  Tooltip,
} from '../components/ui'

const JOBS = [
  'market_sync',
  'wallet_sync',
  'price_backfill',
  'analytics',
  'signal_scan',
  'paper_manage',
  'data_quality',
]

export default function SystemHealth() {
  const [busy, setBusy] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const health = useApi(() => api.health(), [], { pollMs: 15_000 })
  const quality = useApi(() => api.dataQuality(), [])
  const jobs = useApi(() => api.jobsStatus(), [], { pollMs: 15_000 })

  const run = async (job: string) => {
    setBusy(job)
    setMessage(null)
    try {
      const result = await api.runJob(job)
      setMessage(`${job}: ${JSON.stringify(result.result ?? {})}`)
      health.reload()
      jobs.reload()
      quality.reload()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(null)
    }
  }

  if (health.loading && !health.data) return <Loading rows={5} />
  if (health.error) return <ErrorNote message={health.error} onRetry={health.reload} />
  const h = health.data
  if (!h) return null

  const q = quality.data
  const evidence = Object.entries(q?.price_quality_breakdown ?? {})

  return (
    <>
      <div className="page-header">
        <h1>System health</h1>
        <p>
          Pipeline state, data freshness and the evidence mix behind every copyable number. Weak
          price evidence is the single most likely cause of misleading results, so it is reported
          here rather than buried.
        </p>
      </div>

      <div className="grid grid-4">
        <Stat
          label="Status"
          value={<StatusBadge status={h.status} />}
          hint={`${h.environment} · v${h.version}`}
        />
        <Stat
          label="Database"
          value={h.database === 'ok' ? 'Connected' : 'Error'}
          tone={h.database === 'ok' ? '' : 'neg'}
          hint={h.database !== 'ok' ? h.database : undefined}
        />
        <Stat
          label="Scheduler"
          value={h.scheduler_running ? 'Running' : 'Stopped'}
          tone={h.scheduler_running ? '' : 'neg'}
          hint={`${h.jobs.length} jobs registered`}
        />
        <Stat
          label="Unresolved errors"
          value={h.recent_errors}
          tone={h.recent_errors > 0 ? 'neg' : ''}
          hint={h.unacknowledged_drift > 0 ? `${h.unacknowledged_drift} schema drift events` : 'Last 24h'}
        />
      </div>

      {h.unacknowledged_drift > 0 && (
        <div className="section">
          <Notice tone="warn">
            {h.unacknowledged_drift} upstream schema change(s) detected. A silent change in the
            Polymarket payloads is the most likely way this system starts producing quietly wrong
            numbers — check the ingestion logs before trusting recent results.
          </Notice>
        </div>
      )}

      <div className="section grid grid-2">
        <Card title="Data freshness">
          <dl className="kv">
            {Object.entries(h.freshness ?? {})
              .filter(([key]) => !key.endsWith('_age_seconds'))
              .map(([key, value]) => (
                <div key={key} style={{ display: 'contents' }}>
                  <dt>{humanize(key)}</dt>
                  <dd>{typeof value === 'string' ? ago(value) : String(value ?? '—')}</dd>
                </div>
              ))}
          </dl>
        </Card>

        <Card
          title="Price evidence mix"
          tooltip="Observed trade prints are strongest. Modelled prices are assumptions and are excluded from headline copyable ROI."
        >
          {evidence.length ? (
            <BarChart
              data={evidence.map(([kind, count]) => ({
                label: humanize(kind),
                value: count,
                hint: `${count} copyability rows`,
              }))}
              format={(v) => v.toFixed(0)}
              colorFor={() => 'var(--accent)'}
            />
          ) : (
            <Empty
              title="No copyability rows yet"
              hint="These appear once positions have been reconstructed and priced."
            />
          )}
          {q?.avg_data_confidence !== null && q?.avg_data_confidence !== undefined && (
            <div style={{ marginTop: 12 }} className="faint">
              Average data confidence: {q.avg_data_confidence.toFixed(1)}/100
            </div>
          )}
        </Card>
      </div>

      <div className="section">
        <Card title="Background jobs" subtitle="Run any job immediately to force a refresh">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Job</th>
                  <th>Next run</th>
                  <th>Last run</th>
                  <th>Result</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {JOBS.map((job) => {
                  const info = (jobs.data?.jobs ?? []).find(
                    (j: Record<string, any>) => j.id === job || j.job === job,
                  )
                  return (
                    <tr key={job}>
                      <td>{humanize(job)}</td>
                      <td className="faint">
                        {info?.next_run ? new Date(info.next_run).toLocaleTimeString() : '—'}
                      </td>
                      <td className="faint">{info?.last_run_at ? ago(info.last_run_at) : 'never'}</td>
                      <td>
                        {info?.last_run_ok === undefined ? (
                          <span className="faint">—</span>
                        ) : info.last_run_ok ? (
                          <Badge tone="good">ok</Badge>
                        ) : (
                          <Badge tone="bad" title={info.last_error}>
                            failed
                          </Badge>
                        )}
                      </td>
                      <td>
                        <button
                          className="btn btn-sm"
                          disabled={busy !== null}
                          onClick={() => run(job)}
                        >
                          {busy === job ? 'Running…' : 'Run now'}
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          {!h.scheduler_running && (
            <div style={{ marginTop: 12 }}>
              <Notice tone="warn">
                The scheduler is not running, so nothing refreshes automatically. Jobs can still be
                triggered manually here.
              </Notice>
            </div>
          )}
        </Card>
      </div>

      {message && (
        <div className="section">
          <Notice tone="info">
            <span className="mono" style={{ fontSize: 12 }}>
              {message}
            </span>
          </Notice>
        </div>
      )}

      {q && (
        <div className="section grid grid-2">
          <Card title="Pipeline coverage">
            <dl className="kv">
              <dt>Wallets tracked</dt>
              <dd>
                {q.wallets_tracked} <span className="faint">({q.wallets_stale} stale)</span>
              </dd>
              <dt>Markets tracked</dt>
              <dd>
                {q.markets_tracked.toLocaleString()}{' '}
                <span className="faint">({q.markets_needing_review} need review)</span>
              </dd>
              <dt>Transactions</dt>
              <dd>{q.transactions_total.toLocaleString()}</dd>
              <dt>
                Unmatched to a market{' '}
                <Tooltip text="Expected: wallets trade far more non-tennis than tennis, and only the tennis universe is fully synced." />
              </dt>
              <dd>{q.transactions_unmatched_market.toLocaleString()}</dd>
              <dt>Positions</dt>
              <dd>
                {q.positions_total.toLocaleString()}{' '}
                <span className="faint">({q.positions_low_confidence} low confidence)</span>
              </dd>
            </dl>
          </Card>

          <Card title="Warnings">
            {q.warnings.length ? (
              <div className="vstack">
                {q.warnings.map((w, i) => (
                  <Notice key={i} tone="warn">
                    {w}
                  </Notice>
                ))}
              </div>
            ) : (
              <Empty title="No data-quality warnings" />
            )}
          </Card>
        </div>
      )}

      <div className="section">
        <Card title="Notification channels">
          <div className="hstack">
            {h.notification_channels.map((c) => (
              <Badge key={c} tone={c === 'in_app' ? 'neutral' : 'good'}>
                {c}
              </Badge>
            ))}
          </div>
          {h.notification_channels.length <= 1 && (
            <div style={{ marginTop: 10 }}>
              <Notice tone="info">
                Only in-app notifications are configured. Set DISCORD_WEBHOOK_URL, Telegram or SMTP
                environment variables to receive alerts outside the dashboard.
              </Notice>
            </div>
          )}
        </Card>
      </div>
    </>
  )
}
