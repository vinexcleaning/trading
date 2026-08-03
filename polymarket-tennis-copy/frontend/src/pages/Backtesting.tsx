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
  LineChart,
  Loading,
  money,
  Notice,
  num,
  pct,
  price,
  ScoreBar,
  signClass,
  Stat,
  StatusBadge,
  Tooltip,
} from '../components/ui'
import type { BacktestRun } from '../types'

const EXIT_STRATEGIES = [
  'hold_to_resolution',
  'follow_wallet_exit',
  'profit_target',
  'stop_loss',
  'fixed_hold',
  'consensus_gone',
  'wallet_reduces',
  'trailing_stop',
]

function isoDaysAgo(days: number): string {
  return new Date(Date.now() - days * 86_400_000).toISOString().slice(0, 10)
}

export default function Backtesting() {
  const [form, setForm] = useState({
    name: 'Copyability check',
    period_start: isoDaysAgo(180),
    period_end: isoDaysAgo(0),
    delay_seconds: 15,
    slippage_bps: 150,
    fee_bps: 0,
    stake_usdc: '5',
    exit_strategy: 'hold_to_resolution',
    min_wallet_trades: 30,
    min_wallet_score: 75,
    min_copyable_roi: 0,
    max_price_deterioration: '0.03',
    min_liquidity_usdc: '500',
    min_copyability: 60,
    consensus_required: 1,
    train_fraction: 0.5,
    validation_fraction: 0.25,
  })
  const [selected, setSelected] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const runs = useApi(() => api.backtests(), [], { pollMs: 5_000 })
  const detail = useApi(
    () => (selected ? api.backtest(selected) : Promise.resolve(null as never)),
    [selected],
    { pollMs: selected ? 4_000 : undefined },
  )
  const trades = useApi(
    () => (selected ? api.backtestTrades(selected, { limit: 500 }) : Promise.resolve([])),
    [selected],
  )

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setMessage(null)
    try {
      const run = await api.createBacktest({
        ...form,
        period_start: new Date(form.period_start).toISOString(),
        period_end: new Date(form.period_end).toISOString(),
        stake_usdc: form.stake_usdc,
        max_price_deterioration: form.max_price_deterioration,
        min_liquidity_usdc: form.min_liquidity_usdc,
        wallet_ids: [],
      })
      setSelected(run.id)
      setMessage(`Queued run #${run.id}. Results appear as it progresses.`)
      runs.reload()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  const set = (key: string, value: unknown) => setForm((f) => ({ ...f, [key]: value }))

  return (
    <>
      <div className="page-header">
        <h1>Backtesting</h1>
        <p>
          Replays historical wallet entries as follower trades using only information available at
          each decision moment. Results are split chronologically into train, validation and test
          periods — reporting an in-sample number as proof is the easiest way to make a copy-trading
          system look profitable when it is not.
        </p>
      </div>

      <div className="grid grid-2">
        <Card title="Configure a run">
          <form onSubmit={submit}>
            <label className="field">
              <span>Name</span>
              <input value={form.name} onChange={(e) => set('name', e.target.value)} required />
            </label>

            <div className="grid grid-2" style={{ gap: 10 }}>
              <label className="field">
                <span>Period start</span>
                <input
                  type="date"
                  value={form.period_start}
                  onChange={(e) => set('period_start', e.target.value)}
                />
              </label>
              <label className="field">
                <span>Period end</span>
                <input
                  type="date"
                  value={form.period_end}
                  onChange={(e) => set('period_end', e.target.value)}
                />
              </label>
              <label className="field">
                <span>
                  Follower delay (s){' '}
                  <Tooltip text="0 is a theoretical reference only — no follower can detect, decide and execute instantly." />
                </span>
                <select
                  value={form.delay_seconds}
                  onChange={(e) => set('delay_seconds', Number(e.target.value))}
                >
                  {[0, 2, 5, 10, 15, 30, 60, 120, 300].map((d) => (
                    <option key={d} value={d}>
                      {d}s{d === 0 ? ' (theoretical)' : ''}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Slippage (bps)</span>
                <input
                  type="number"
                  value={form.slippage_bps}
                  onChange={(e) => set('slippage_bps', Number(e.target.value))}
                />
              </label>
              <label className="field">
                <span>Fees (bps)</span>
                <input
                  type="number"
                  value={form.fee_bps}
                  onChange={(e) => set('fee_bps', Number(e.target.value))}
                />
              </label>
              <label className="field">
                <span>Stake per trade ($)</span>
                <input
                  value={form.stake_usdc}
                  onChange={(e) => set('stake_usdc', e.target.value)}
                />
              </label>
              <label className="field">
                <span>Exit strategy</span>
                <select
                  value={form.exit_strategy}
                  onChange={(e) => set('exit_strategy', e.target.value)}
                >
                  {EXIT_STRATEGIES.map((s) => (
                    <option key={s} value={s}>
                      {humanize(s)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Consensus required</span>
                <select
                  value={form.consensus_required}
                  onChange={(e) => set('consensus_required', Number(e.target.value))}
                >
                  <option value={1}>1 wallet</option>
                  <option value={2}>2 independent groups</option>
                  <option value={3}>3 independent groups</option>
                </select>
              </label>
              <label className="field">
                <span>Min wallet trades</span>
                <input
                  type="number"
                  value={form.min_wallet_trades}
                  onChange={(e) => set('min_wallet_trades', Number(e.target.value))}
                />
              </label>
              <label className="field">
                <span>Min wallet score</span>
                <input
                  type="number"
                  value={form.min_wallet_score}
                  onChange={(e) => set('min_wallet_score', Number(e.target.value))}
                />
              </label>
              <label className="field">
                <span>Max price deterioration ($)</span>
                <input
                  value={form.max_price_deterioration}
                  onChange={(e) => set('max_price_deterioration', e.target.value)}
                />
              </label>
              <label className="field">
                <span>Min liquidity ($)</span>
                <input
                  value={form.min_liquidity_usdc}
                  onChange={(e) => set('min_liquidity_usdc', e.target.value)}
                />
              </label>
              <label className="field">
                <span>Min copyability</span>
                <input
                  type="number"
                  value={form.min_copyability}
                  onChange={(e) => set('min_copyability', Number(e.target.value))}
                />
              </label>
            </div>

            <button className="btn btn-primary" disabled={busy}>
              {busy ? 'Queuing…' : 'Run backtest'}
            </button>
          </form>
        </Card>

        <Card title="Previous runs">
          {runs.loading && !runs.data ? (
            <Loading rows={3} />
          ) : !runs.data?.length ? (
            <Empty title="No runs yet" hint="Configure a period and press Run backtest." />
          ) : (
            <div className="table-wrap scroll-y">
              <table>
                <thead>
                  <tr>
                    <th>Run</th>
                    <th>Status</th>
                    <th className="num">Trades</th>
                    <th className="num">Return</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {runs.data.map((r) => (
                    <tr key={r.id}>
                      <td>
                        <div style={{ fontWeight: 550 }}>{r.name}</div>
                        <div className="faint" style={{ fontSize: 11.5 }}>
                          {r.delay_seconds}s delay · {ago(r.started_at)}
                        </div>
                      </td>
                      <td>
                        <StatusBadge status={r.status} />
                        {r.status === 'running' && (
                          <div className="faint" style={{ fontSize: 11 }}>
                            {r.progress_pct.toFixed(0)}%
                          </div>
                        )}
                      </td>
                      <td className="num">{r.total_trades}</td>
                      <td className={`num ${signClass(r.total_return)}`}>{pct(r.total_return)}</td>
                      <td>
                        <button className="btn btn-sm" onClick={() => setSelected(r.id)}>
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      {message && (
        <div className="section">
          <Notice tone="info">{message}</Notice>
        </div>
      )}

      {selected && detail.data && (
        <div className="section">
          <RunResults run={detail.data} trades={trades.data ?? []} />
        </div>
      )}

      {selected && detail.error && (
        <div className="section">
          <ErrorNote message={detail.error} onRetry={detail.reload} />
        </div>
      )}
    </>
  )
}

function RunResults({ run, trades }: { run: BacktestRun; trades: any[] }) {
  const equity = run.equity_curve.map((y, i) => ({ x: i + 1, y }))
  const drawdown = run.drawdown_curve.map((y, i) => ({ x: i + 1, y }))
  const delayRows = Object.entries(run.delay_sensitivity ?? {})
    .map(([delay, value]) => ({
      label: `${delay}s`,
      value: typeof value === 'object' && value ? Number((value as any).total_return ?? 0) : 0,
      hint: `Return at ${delay}s follower delay`,
    }))
    .sort((a, b) => parseInt(a.label) - parseInt(b.label))

  return (
    <>
      <div className="section-title">
        <h2>{run.name}</h2>
        <StatusBadge status={run.status} />
        <span className="faint">
          {new Date(run.period_start).toLocaleDateString()} –{' '}
          {new Date(run.period_end).toLocaleDateString()} · {run.delay_seconds}s delay
        </span>
      </div>

      {run.lookahead_violations > 0 && (
        <div style={{ marginBottom: 14 }}>
          <Notice tone="bad">
            <strong>{run.lookahead_violations} look-ahead violation(s) detected.</strong> This run
            read information that would not have been available at decision time. The results are
            not usable.
          </Notice>
        </div>
      )}

      {run.warnings.length > 0 && (
        <div style={{ marginBottom: 14 }}>
          <Notice tone="warn">
            <ul style={{ margin: 0, paddingLeft: 16 }}>
              {run.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </Notice>
        </div>
      )}

      {run.error && (
        <div style={{ marginBottom: 14 }}>
          <Notice tone="bad">{run.error}</Notice>
        </div>
      )}

      <div className="grid grid-4">
        <Stat
          label="Total return"
          value={pct(run.total_return)}
          tone={signClass(run.total_return) as 'pos' | 'neg' | ''}
          hint={
            run.return_ci_low !== null && run.return_ci_high !== null
              ? `95% CI ${pct(run.return_ci_low)} – ${pct(run.return_ci_high)}`
              : undefined
          }
          tooltip="Confidence interval from bootstrap resampling. A CI spanning zero means the result is not distinguishable from luck."
        />
        <Stat label="Trades" value={run.total_trades} hint={`${run.wins}W / ${run.losses}L`} />
        <Stat label="P&L" value={money(run.total_pnl)} hint={`Staked ${money(run.total_staked, 0)}`} />
        <Stat
          label="Max drawdown"
          value={pct(run.max_drawdown, 0)}
          hint={`Profit factor ${num(run.profit_factor, 2)}`}
        />
      </div>

      <div className="section grid grid-3">
        <Stat
          label="In-sample (train)"
          value={pct(run.in_sample_return)}
          tone={signClass(run.in_sample_return) as 'pos' | 'neg' | ''}
          tooltip="Where thresholds may have been tuned. Not evidence on its own."
        />
        <Stat
          label="Validation"
          value={pct(run.validation_return)}
          tone={signClass(run.validation_return) as 'pos' | 'neg' | ''}
        />
        <Stat
          label="Out-of-sample (test)"
          value={pct(run.out_of_sample_return)}
          tone={signClass(run.out_of_sample_return) as 'pos' | 'neg' | ''}
          tooltip="The only split that constitutes evidence the approach generalises."
        />
      </div>

      <div className="section grid grid-2">
        <Card title="Equity curve" subtitle="Cumulative simulated P&L">
          {equity.length > 1 ? (
            <LineChart
              series={equity}
              zeroLine
              color={Number(run.total_pnl ?? 0) >= 0 ? 'var(--good)' : 'var(--bad)'}
              yFormat={(v) => `$${v.toFixed(0)}`}
              xFormat={(v) => `#${v.toFixed(0)}`}
              ariaLabel="Equity curve"
            />
          ) : (
            <Empty title="Not enough trades to plot" />
          )}
        </Card>

        <Card title="Drawdown" subtitle="Peak-to-trough decline">
          {drawdown.length > 1 ? (
            <LineChart
              series={drawdown}
              color="var(--bad)"
              yFormat={(v) => `${(v * 100).toFixed(0)}%`}
              xFormat={(v) => `#${v.toFixed(0)}`}
              ariaLabel="Drawdown curve"
            />
          ) : (
            <Empty title="No drawdown data" />
          )}
        </Card>
      </div>

      <div className="section grid grid-2">
        <Card
          title="Delay sensitivity"
          subtitle="Return at each follower delay"
          tooltip="If the strategy only works at 0s, it is not a strategy — it is a measurement of the wallet, not of what you could have captured."
        >
          {delayRows.length ? (
            <BarChart data={delayRows} format={(v) => pct(v)} />
          ) : (
            <Empty title="No delay sensitivity computed" />
          )}
        </Card>

        <Card title="Why candidates were skipped" subtitle={`${run.skipped_trades} skipped`}>
          {Object.keys(run.skip_reasons ?? {}).length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Reason</th>
                    <th className="num">Count</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(run.skip_reasons)
                    .sort((a, b) => b[1] - a[1])
                    .map(([reason, count]) => (
                      <tr key={reason}>
                        <td>{humanize(reason)}</td>
                        <td className="num">{count}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty title="Nothing was skipped" />
          )}
        </Card>
      </div>

      {run.pct_pnl_from_top_trade !== null && (
        <div className="section">
          <Notice tone={run.pct_pnl_from_top_trade > 0.4 ? 'warn' : 'info'}>
            The single best trade produced {pct(run.pct_pnl_from_top_trade, 0)} of total P&L.
            {run.pct_pnl_from_top_trade > 0.4 &&
              ' A result this dependent on one outcome should not be treated as a repeatable edge.'}
          </Notice>
        </div>
      )}

      {trades.length > 0 && (
        <div className="section">
          <Card title="Trade log" subtitle={`${trades.length} simulated trades`}>
            <div className="table-wrap scroll-y">
              <table>
                <thead>
                  <tr>
                    <th>Decision</th>
                    <th>Split</th>
                    <th className="num">Wallet entry</th>
                    <th className="num">Fill</th>
                    <th className="num">Exit</th>
                    <th className="num">P&L</th>
                    <th className="num">ROI</th>
                    <th className="num">Copyability</th>
                    <th>Evidence</th>
                    <th>Type</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.map((t, i) => (
                    <tr key={i}>
                      <td className="faint">{new Date(t.decision_at).toLocaleDateString()}</td>
                      <td>
                        <Badge tone={t.split === 'test' ? 'good' : 'neutral'}>{t.split}</Badge>
                      </td>
                      <td className="num">{price(t.wallet_entry_price)}</td>
                      <td className="num">{price(t.fill_price)}</td>
                      <td className="num">{price(t.exit_price)}</td>
                      <td className={`num ${signClass(Number(t.pnl))}`}>{money(t.pnl)}</td>
                      <td className={`num ${signClass(t.roi)}`}>{pct(t.roi)}</td>
                      <td className="num">
                        <ScoreBar value={t.copyability_score} />
                      </td>
                      <td className="faint" style={{ fontSize: 11.5 }}>
                        {humanize(t.price_source_quality)}
                      </td>
                      <td className="faint">{humanize(t.market_type)}</td>
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
