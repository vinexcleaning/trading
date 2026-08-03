import { useState } from 'react'
import { api, useApi } from '../api'
import {
  Badge,
  Card,
  ErrorNote,
  humanize,
  Loading,
  Notice,
  pct,
  Tooltip,
} from '../components/ui'

/** Only these keys are runtime-editable; the backend enforces the same list. */
const EDITABLE: Array<{ key: string; label: string; group: string; help?: string }> = [
  { key: 'alert_min_tennis_trades', label: 'Min completed tennis trades', group: 'Alert gates' },
  { key: 'alert_min_skill_score', label: 'Min skill score', group: 'Alert gates' },
  {
    key: 'alert_min_copyable_roi',
    label: 'Min copyable ROI',
    group: 'Alert gates',
    help: 'Expressed as a fraction, e.g. 0.02 for 2%.',
  },
  { key: 'alert_min_data_confidence', label: 'Min data confidence', group: 'Alert gates' },
  { key: 'alert_max_drawdown', label: 'Max drawdown', group: 'Alert gates' },
  {
    key: 'alert_max_price_deterioration',
    label: 'Max price deterioration ($)',
    group: 'Alert gates',
    help: 'How much worse than the wallet entry the follower price may be.',
  },
  { key: 'alert_min_liquidity_usdc', label: 'Min liquidity ($)', group: 'Alert gates' },
  { key: 'alert_max_spread', label: 'Max spread ($)', group: 'Alert gates' },
  { key: 'alert_max_age_live_seconds', label: 'Max signal age, live (s)', group: 'Alert gates' },
  {
    key: 'alert_max_age_prematch_seconds',
    label: 'Max signal age, prematch (s)',
    group: 'Alert gates',
  },
  { key: 'alert_min_copyability_score', label: 'Min copyability score', group: 'Alert gates' },
  { key: 'alert_min_position_usdc', label: 'Min wallet position ($)', group: 'Alert gates' },

  { key: 'consensus_min_wallets', label: 'Min wallets', group: 'Consensus' },
  {
    key: 'consensus_min_independent_clusters',
    label: 'Min independent groups',
    group: 'Consensus',
    help: 'Wallets in one behavioural cluster count once. Three related addresses are one opinion.',
  },
  { key: 'consensus_window_seconds', label: 'Agreement window (s)', group: 'Consensus' },
  { key: 'consensus_min_median_skill', label: 'Min median skill', group: 'Consensus' },
  {
    key: 'consensus_min_median_copyability',
    label: 'Min median copyability',
    group: 'Consensus',
  },

  {
    key: 'benchmark_delay_seconds',
    label: 'Benchmark follower delay (s)',
    group: 'Execution model',
    help: 'The delay used for every headline copyable figure. Must be one of the configured delays and cannot be zero.',
  },
  { key: 'modeled_slippage_bps', label: 'Modelled slippage (bps)', group: 'Execution model' },
  {
    key: 'min_copyable_data_confidence',
    label: 'Min evidence confidence to count',
    group: 'Execution model',
    help: 'Trades below this confidence are excluded from copyable ROI rather than averaged in.',
  },

  { key: 'paper_trading_enabled', label: 'Paper trading enabled', group: 'Paper trading' },
  { key: 'paper_stake_usdc', label: 'Stake per signal ($)', group: 'Paper trading' },
  {
    key: 'paper_execution_delay_seconds',
    label: 'Execution delay (s)',
    group: 'Paper trading',
  },
  {
    key: 'paper_max_exposure_per_market_usdc',
    label: 'Max exposure per market ($)',
    group: 'Paper trading',
  },
  {
    key: 'paper_max_total_exposure_usdc',
    label: 'Max total exposure ($)',
    group: 'Paper trading',
  },
  { key: 'paper_max_open_positions', label: 'Max open positions', group: 'Paper trading' },
  { key: 'paper_daily_loss_cap_usdc', label: 'Daily loss cap ($)', group: 'Paper trading' },
  { key: 'paper_default_exit_strategy', label: 'Default exit strategy', group: 'Paper trading' },
  {
    key: 'paper_allow_duplicate_signals',
    label: 'Allow duplicate entries',
    group: 'Paper trading',
  },

  { key: 'sync_interval_seconds', label: 'Wallet sync interval (s)', group: 'Scheduling' },
  { key: 'live_sync_interval_seconds', label: 'Signal scan interval (s)', group: 'Scheduling' },
  { key: 'market_refresh_interval_seconds', label: 'Market refresh (s)', group: 'Scheduling' },
  {
    key: 'metrics_recompute_interval_seconds',
    label: 'Analytics recompute (s)',
    group: 'Scheduling',
  },
  { key: 'max_wallets_per_sync_cycle', label: 'Wallets per sync cycle', group: 'Scheduling' },
  { key: 'raw_response_retention_days', label: 'Raw payload retention (days)', group: 'Scheduling' },
  { key: 'log_level', label: 'Log level', group: 'Scheduling' },
  { key: 'notifications_enabled', label: 'Notifications enabled', group: 'Scheduling' },
]

const GROUPS = ['Alert gates', 'Consensus', 'Execution model', 'Paper trading', 'Scheduling']

export default function SettingsPage() {
  const settings = useApi(() => api.settings(), [])
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const save = async (key: string) => {
    const value = drafts[key]
    if (value === undefined) return
    setBusy(true)
    setMessage(null)
    try {
      const result = await api.updateSetting(key, value)
      setMessage(result.message)
      setDrafts((d) => {
        const next = { ...d }
        delete next[key]
        return next
      })
      settings.reload()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  if (settings.loading && !settings.data) return <Loading rows={6} />
  if (settings.error) return <ErrorNote message={settings.error} onRetry={settings.reload} />
  const s = settings.data
  if (!s) return null

  const current = (key: string): string => {
    const pools = [s.alert_thresholds, s.consensus_thresholds, s.paper_settings] as Array<
      Record<string, any>
    >
    const short = key
      .replace(/^alert_/, '')
      .replace(/^consensus_/, '')
      .replace(/^paper_/, '')
    for (const pool of pools) {
      if (pool && short in pool) return String(pool[short])
    }
    if (key === 'benchmark_delay_seconds') return String(s.benchmark_delay_seconds)
    if (key === 'modeled_slippage_bps') return String(s.modeled_slippage_bps)
    if (key === 'min_copyable_data_confidence') return String(s.min_copyable_data_confidence)
    const syncKey: Record<string, keyof typeof s.sync_intervals> = {
      sync_interval_seconds: 'wallet_sync_seconds',
      live_sync_interval_seconds: 'live_sync_seconds',
      market_refresh_interval_seconds: 'market_refresh_seconds',
      metrics_recompute_interval_seconds: 'metrics_recompute_seconds',
    }
    if (key in syncKey) return String(s.sync_intervals[syncKey[key]])
    return ''
  }

  return (
    <>
      <div className="page-header">
        <h1>Settings</h1>
        <p>
          Every threshold that shapes scoring, alerting and simulation is editable here. Credentials
          are not: webhook URLs, tokens and SMTP passwords live in the environment and are never
          readable through the API or shown in this UI.
        </p>
      </div>

      {message && (
        <div style={{ marginBottom: 14 }}>
          <Notice tone="info">{message}</Notice>
        </div>
      )}

      <div className="grid grid-2" style={{ marginBottom: 18 }}>
        <Card title="Scoring weights" subtitle="Adjusted Tennis Skill Score, sums to 1.0">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Component</th>
                  <th className="num">Weight</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(s.score_weights).map(([key, weight]) => (
                  <tr key={key}>
                    <td>{humanize(key)}</td>
                    <td className="num">{pct(weight, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ marginTop: 10 }} className="faint">
            Weights are set in the environment because changing them invalidates stored scores.
          </div>
        </Card>

        <Card title="Execution assumptions">
          <dl className="kv">
            <dt>
              Follower delays tested{' '}
              <Tooltip text="Every trade is scored at each of these delays, so the decay of an edge is visible rather than assumed." />
            </dt>
            <dd className="mono">{s.follower_delays_seconds.join(', ')}s</dd>
            <dt>Benchmark delay</dt>
            <dd>{s.benchmark_delay_seconds}s</dd>
            <dt>Modelled slippage</dt>
            <dd>{s.modeled_slippage_bps} bps</dd>
            <dt>Min evidence confidence</dt>
            <dd>{s.min_copyable_data_confidence}</dd>
            <dt>Notification channels</dt>
            <dd className="hstack">
              {s.notification_channels_configured.map((c) => (
                <Badge key={c} tone={c === 'in_app' ? 'neutral' : 'good'}>
                  {c}
                </Badge>
              ))}
            </dd>
          </dl>
        </Card>
      </div>

      {GROUPS.map((group) => (
        <div className="section" key={group}>
          <Card title={group}>
            <div className="grid grid-2" style={{ gap: 12 }}>
              {EDITABLE.filter((f) => f.group === group).map((field) => {
                const value = drafts[field.key] ?? current(field.key)
                const dirty = drafts[field.key] !== undefined
                return (
                  <div key={field.key}>
                    <label className="field" style={{ marginBottom: 4 }}>
                      <span>
                        {field.label} {field.help && <Tooltip text={field.help} />}
                      </span>
                      <div className="hstack" style={{ gap: 6, flexWrap: 'nowrap' }}>
                        <input
                          value={value}
                          onChange={(e) =>
                            setDrafts((d) => ({ ...d, [field.key]: e.target.value }))
                          }
                        />
                        <button
                          className="btn btn-sm"
                          disabled={!dirty || busy}
                          onClick={() => save(field.key)}
                        >
                          Save
                        </button>
                      </div>
                    </label>
                    <div className="faint mono" style={{ fontSize: 11 }}>
                      {field.key}
                    </div>
                  </div>
                )
              })}
            </div>
          </Card>
        </div>
      ))}

      <div className="section">
        <Notice tone="warn">
          Overrides are stored in the database and take effect for jobs that read settings at run
          time. Components that cache configuration at startup pick them up after a restart.
        </Notice>
      </div>
    </>
  )
}
