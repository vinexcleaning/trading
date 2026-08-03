/** Shared presentational components. */

import type { ReactNode } from 'react'

/* ------------------------------------------------------------- formatting */

export function pct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${(value * 100).toFixed(digits)}%`
}

export function money(value: string | number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || value === '') return '—'
  const n = typeof value === 'string' ? Number(value) : value
  if (Number.isNaN(n)) return '—'
  const sign = n < 0 ? '-' : ''
  return `${sign}$${Math.abs(n).toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`
}

export function price(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—'
  const n = typeof value === 'string' ? Number(value) : value
  if (Number.isNaN(n)) return '—'
  return `$${n.toFixed(3).replace(/0$/, '')}`
}

export function num(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toFixed(digits)
}

export function duration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '—'
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  if (seconds < 86400) return `${(seconds / 3600).toFixed(1)}h`
  return `${(seconds / 86400).toFixed(1)}d`
}

export function ago(iso: string | null | undefined): string {
  if (!iso) return 'never'
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return '—'
  const secs = (Date.now() - then) / 1000
  if (secs < 0) return 'in ' + duration(-secs)
  if (secs < 10) return 'just now'
  return `${duration(secs)} ago`
}

export function shortAddress(address: string): string {
  return `${address.slice(0, 6)}…${address.slice(-4)}`
}

/** Turn a snake_case enum value into readable prose. */
export function humanize(value: string | null | undefined): string {
  if (!value) return '—'
  return value.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())
}

export function signClass(value: number | null | undefined): string {
  if (value === null || value === undefined) return ''
  return value > 0 ? 'pos' : value < 0 ? 'neg' : ''
}

/* ------------------------------------------------------------- primitives */

export function Tooltip({ text, children }: { text: string; children?: ReactNode }) {
  return (
    <span className="tip">
      {children ?? <span className="tip-icon">?</span>}
      <span className="tip-body">{text}</span>
    </span>
  )
}

export function Stat({
  label,
  value,
  hint,
  tone,
  tooltip,
}: {
  label: string
  value: ReactNode
  hint?: ReactNode
  tone?: 'pos' | 'neg' | ''
  tooltip?: string
}) {
  return (
    <div className="stat">
      <div className="stat-label">
        {label}
        {tooltip && <Tooltip text={tooltip} />}
      </div>
      <div className={`stat-value ${tone ?? ''}`}>{value}</div>
      {hint && <div className="stat-hint">{hint}</div>}
    </div>
  )
}

export function Card({
  title,
  subtitle,
  actions,
  children,
  tooltip,
}: {
  title?: string
  subtitle?: ReactNode
  actions?: ReactNode
  children: ReactNode
  tooltip?: string
}) {
  return (
    <div className="card">
      {(title || actions) && (
        <div className="card-header">
          <div>
            {title && (
              <div className="card-title">
                {title} {tooltip && <Tooltip text={tooltip} />}
              </div>
            )}
            {subtitle && <div className="card-sub">{subtitle}</div>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </div>
  )
}

export function Badge({
  tone = 'neutral',
  children,
  title,
}: {
  tone?: 'good' | 'bad' | 'warn' | 'info' | 'neutral'
  children: ReactNode
  title?: string
}) {
  return (
    <span className={`badge badge-${tone}`} title={title}>
      {children}
    </span>
  )
}

const STATUS_TONE: Record<string, 'good' | 'bad' | 'warn' | 'info' | 'neutral'> = {
  qualified: 'good',
  paper_entered: 'good',
  paper_exited: 'info',
  rejected: 'bad',
  expired: 'neutral',
  observed: 'neutral',
  evaluating: 'warn',
  open: 'info',
  closed: 'neutral',
  settled: 'good',
  pending: 'warn',
  active: 'good',
  inactive: 'neutral',
  blocked: 'bad',
  success: 'good',
  failed: 'bad',
  running: 'warn',
  partial: 'warn',
  ok: 'good',
  degraded: 'warn',
  error: 'bad',
}

export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={STATUS_TONE[status] ?? 'neutral'}>{humanize(status)}</Badge>
}

/** Risk flags are always rendered in full: hiding them would defeat the point. */
export function RiskFlags({ flags, max }: { flags: string[]; max?: number }) {
  if (!flags?.length) return <span className="faint">none</span>
  const shown = max ? flags.slice(0, max) : flags
  return (
    <div className="flag-list">
      {shown.map((flag) => (
        <Badge key={flag} tone="warn" title={RISK_FLAG_HELP[flag] ?? flag}>
          {humanize(flag)}
        </Badge>
      ))}
      {max && flags.length > max && (
        <Badge tone="neutral" title={flags.slice(max).join(', ')}>
          +{flags.length - max}
        </Badge>
      )}
    </div>
  )
}

export const RISK_FLAG_HELP: Record<string, string> = {
  small_sample: 'Too few completed trades to separate skill from luck.',
  profit_concentration: 'Most of the profit came from one or two trades.',
  severe_drawdown: 'The wallet has suffered a large peak-to-trough decline.',
  negative_recent_trend: 'Recent performance is worse than the lifetime record.',
  negative_copyable_roi: 'A delayed follower would have lost money copying this wallet.',
  likely_market_making: 'Behaviour looks like quoting both sides, not directional betting.',
  low_liquidity_markets: 'Trades happen in markets too thin to copy at size.',
  ambiguous_reconstruction: 'Position history could not be reconstructed with confidence.',
  suspected_related_wallet: 'May share an operator with another tracked wallet.',
  stale_activity: 'No recent trading activity.',
  thin_data: 'Price evidence is sparse; delay figures are weak here.',
  rapid_exit_pattern: 'The wallet exits fast, leaving little time to follow.',
  hedging_behaviour: 'Positions look like hedges rather than directional views.',
  fast_moving_market: 'The market is repricing quickly; the quoted price may not hold.',
  ambiguous_classification: 'Market classification is uncertain.',
  wide_spread: 'The spread makes crossing expensive.',
  survivorship_risk: 'Visible wallets over-represent winners; treat rankings with caution.',
  tail_risk_asymmetry:
    'Wins small and often, loses big and rarely — the favourite-longshot shape. The record looks strong because the losses that define its risk have barely occurred yet, so its true loss rate is unmeasured.',
}

export function Loading({ rows = 3 }: { rows?: number }) {
  return (
    <div className="vstack" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton" style={{ width: `${100 - i * 12}%` }} />
      ))}
    </div>
  )
}

export function Empty({ title, hint }: { title: string; hint?: ReactNode }) {
  return (
    <div className="empty">
      <div className="empty-title">{title}</div>
      {hint && <div className="empty-hint">{hint}</div>}
    </div>
  )
}

export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="notice notice-bad">
      <span>⚠</span>
      <div>
        <div>{message}</div>
        {onRetry && (
          <button className="btn btn-sm" style={{ marginTop: 8 }} onClick={onRetry}>
            Retry
          </button>
        )}
      </div>
    </div>
  )
}

export function Notice({
  tone = 'info',
  children,
}: {
  tone?: 'info' | 'warn' | 'bad'
  children: ReactNode
}) {
  const icon = tone === 'bad' ? '⚠' : tone === 'warn' ? '!' : 'i'
  return (
    <div className={`notice notice-${tone}`}>
      <span aria-hidden="true">{icon}</span>
      <div>{children}</div>
    </div>
  )
}

/** A 0-100 score with a proportional bar. */
export function ScoreBar({ value, max = 100 }: { value: number | null; max?: number }) {
  if (value === null || value === undefined) return <span className="faint">—</span>
  const ratio = Math.max(0, Math.min(1, value / max))
  const color = ratio >= 0.75 ? 'var(--good)' : ratio >= 0.5 ? 'var(--warn)' : 'var(--bad)'
  return (
    <div style={{ minWidth: 74 }}>
      <div className="nums" style={{ fontSize: 12, marginBottom: 3 }}>
        {value.toFixed(0)}
        <span className="faint">/{max}</span>
      </div>
      <div className="bar-track">
        <div className="bar-fill" style={{ width: `${ratio * 100}%`, background: color }} />
      </div>
    </div>
  )
}

/**
 * The product's central comparison, always shown as a pair.
 *
 * Showing raw ROI alone is the exact mistake this application exists to prevent,
 * so the component refuses to render one without the other.
 */
export function RawVsCopyable({
  raw,
  copyable,
  coverage,
  delaySeconds,
}: {
  raw: number | null
  copyable: number | null
  coverage?: number | null
  delaySeconds?: number
}) {
  const gap = raw !== null && copyable !== null ? copyable - raw : null
  return (
    <div className="hstack" style={{ gap: 16 }}>
      <div>
        <div className="stat-label">Raw ROI</div>
        <div className={`nums ${signClass(raw)}`} style={{ fontSize: 17, fontWeight: 600 }}>
          {pct(raw)}
        </div>
      </div>
      <div style={{ color: 'var(--text-faint)', fontSize: 17 }}>→</div>
      <div>
        <div className="stat-label">
          Copyable ROI
          <Tooltip
            text={`What a follower delayed by ${
              delaySeconds ?? 15
            }s would have made, after modelled slippage. Only trades with real price evidence count.`}
          />
        </div>
        <div className={`nums ${signClass(copyable)}`} style={{ fontSize: 17, fontWeight: 600 }}>
          {copyable === null ? (
            <span className="faint" title="Not enough price evidence to measure">
              n/a
            </span>
          ) : (
            pct(copyable)
          )}
        </div>
      </div>
      {gap !== null && (
        <div>
          <div className="stat-label">Cost of delay</div>
          <div className={`nums ${gap < 0 ? 'neg' : 'pos'}`} style={{ fontSize: 17 }}>
            {pct(gap)}
          </div>
        </div>
      )}
      {coverage !== null && coverage !== undefined && (
        <div>
          <div className="stat-label">
            Evidence coverage
            <Tooltip text="Share of completed trades with price evidence good enough to measure a follower's fill. A low figure means the copyable number rests on a subset." />
          </div>
          <div
            className="nums"
            style={{ fontSize: 17, color: coverage < 0.5 ? 'var(--warn)' : 'inherit' }}
          >
            {pct(coverage, 0)}
          </div>
        </div>
      )}
    </div>
  )
}

/* ---------------------------------------------------------------- charts */

interface SeriesPoint {
  x: number
  y: number
}

/** Minimal line chart. Hand-rolled to avoid a charting dependency. */
export function LineChart({
  series,
  height = 170,
  color = 'var(--accent)',
  fill = true,
  zeroLine = false,
  yFormat = (v: number) => v.toFixed(2),
  xFormat,
  ariaLabel,
}: {
  series: SeriesPoint[]
  height?: number
  color?: string
  fill?: boolean
  zeroLine?: boolean
  yFormat?: (v: number) => string
  xFormat?: (v: number) => string
  ariaLabel?: string
}) {
  // Guard at the component boundary rather than trusting every caller: a single
  // null or NaN propagates into the axis maths and renders the whole chart as
  // NaN coordinates, which fails silently as a blank frame.
  const clean = series.filter((p) => Number.isFinite(p.x) && Number.isFinite(p.y))
  if (clean.length < 2) {
    return <Empty title="No data to chart yet" />
  }
  series = clean

  const W = 800
  const H = height
  const padL = 52
  const padR = 12
  const padT = 12
  const padB = xFormat ? 26 : 14

  const xs = series.map((p) => p.x)
  const ys = series.map((p) => p.y)
  const xMin = Math.min(...xs)
  const xMax = Math.max(...xs)
  let yMin = Math.min(...ys)
  let yMax = Math.max(...ys)
  if (zeroLine) {
    yMin = Math.min(yMin, 0)
    yMax = Math.max(yMax, 0)
  }
  if (yMin === yMax) {
    yMin -= 0.5
    yMax += 0.5
  }
  const pad = (yMax - yMin) * 0.08
  yMin -= pad
  yMax += pad

  const sx = (x: number) =>
    padL + ((x - xMin) / (xMax - xMin || 1)) * (W - padL - padR)
  const sy = (y: number) => padT + (1 - (y - yMin) / (yMax - yMin)) * (H - padT - padB)

  const path = series.map((p, i) => `${i === 0 ? 'M' : 'L'}${sx(p.x)},${sy(p.y)}`).join(' ')
  const area =
    `M${sx(series[0].x)},${sy(Math.max(yMin, 0))} ` +
    series.map((p) => `L${sx(p.x)},${sy(p.y)}`).join(' ') +
    ` L${sx(series[series.length - 1].x)},${sy(Math.max(yMin, 0))} Z`

  const ticks = 4
  const yTicks = Array.from({ length: ticks + 1 }, (_, i) => yMin + ((yMax - yMin) * i) / ticks)

  return (
    <svg
      className="chart"
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      style={{ height, width: '100%' }}
      role="img"
      aria-label={ariaLabel ?? 'chart'}
    >
      {yTicks.map((t, i) => (
        <g key={i}>
          <line className="chart-grid" x1={padL} x2={W - padR} y1={sy(t)} y2={sy(t)} />
          <text className="chart-axis-label" x={padL - 6} y={sy(t) + 3} textAnchor="end">
            {yFormat(t)}
          </text>
        </g>
      ))}
      {zeroLine && yMin < 0 && yMax > 0 && (
        <line
          x1={padL}
          x2={W - padR}
          y1={sy(0)}
          y2={sy(0)}
          stroke="var(--text-faint)"
          strokeDasharray="3 3"
        />
      )}
      {fill && <path d={area} fill={color} opacity={0.13} />}
      <path d={path} fill="none" stroke={color} strokeWidth={2} vectorEffect="non-scaling-stroke" />
      {xFormat && (
        <>
          <text className="chart-axis-label" x={padL} y={H - 4} textAnchor="start">
            {xFormat(xMin)}
          </text>
          <text className="chart-axis-label" x={W - padR} y={H - 4} textAnchor="end">
            {xFormat(xMax)}
          </text>
        </>
      )}
    </svg>
  )
}

/** Horizontal bar chart for categorical breakdowns. */
export function BarChart({
  data,
  format = (v: number) => v.toFixed(2),
  colorFor,
}: {
  data: Array<{ label: string; value: number; hint?: string }>
  format?: (v: number) => string
  colorFor?: (value: number) => string
}) {
  if (!data.length) return <Empty title="No data" />
  const max = Math.max(...data.map((d) => Math.abs(d.value)), 1e-9)

  return (
    <div className="vstack" style={{ gap: 9 }}>
      {data.map((d) => {
        const ratio = Math.abs(d.value) / max
        const color = colorFor
          ? colorFor(d.value)
          : d.value >= 0
            ? 'var(--good)'
            : 'var(--bad)'
        return (
          <div key={d.label} title={d.hint}>
            <div
              className="split"
              style={{ justifyContent: 'space-between', fontSize: 12, marginBottom: 3 }}
            >
              <span className="muted">{d.label}</span>
              <span className={`nums ${d.value < 0 ? 'neg' : ''}`}>{format(d.value)}</span>
            </div>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${ratio * 100}%`, background: color }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}
