/** Typed API client plus the data-fetching hooks the pages use. */

import { useCallback, useEffect, useRef, useState } from 'react'
import type {
  AlertRow,
  BacktestRun,
  BacktestTrade,
  DataQuality,
  Health,
  Market,
  MarketDetail,
  Overview,
  PaperSummary,
  PaperTrade,
  Position,
  Ranking,
  Settings,
  Signal,
  Transaction,
  Wallet,
  WalletDetail,
} from './types'

const BASE = import.meta.env.VITE_API_BASE ?? ''

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly detail?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })

  if (!response.ok) {
    let detail: unknown
    let message = `${response.status} ${response.statusText}`
    try {
      detail = await response.json()
      const asRecord = detail as { detail?: unknown }
      if (typeof asRecord?.detail === 'string') message = asRecord.detail
    } catch {
      // A non-JSON error body is still an error; keep the status line.
    }
    throw new ApiError(message, response.status, detail)
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

function query(params: Record<string, string | number | boolean | undefined | null>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value))
    }
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

export const api = {
  overview: () => request<Overview>('/api/overview'),
  health: () => request<Health>('/api/health'),
  dataQuality: () => request<DataQuality>('/api/data-quality'),
  settings: () => request<Settings>('/api/settings'),
  updateSetting: (key: string, value: string) =>
    request<{ message: string }>('/api/settings', {
      method: 'PATCH',
      body: JSON.stringify({ key, value }),
    }),
  clearSetting: (key: string) =>
    request<{ message: string }>(`/api/settings/${key}`, { method: 'DELETE' }),

  wallets: (params: Record<string, any> = {}) =>
    request<Wallet[]>(`/api/wallets${query(params)}`),
  wallet: (id: number) => request<WalletDetail>(`/api/wallets/${id}`),
  createWallet: (body: Record<string, unknown>) =>
    request<Wallet>('/api/wallets', { method: 'POST', body: JSON.stringify(body) }),
  updateWallet: (id: number, body: Record<string, unknown>) =>
    request<Wallet>(`/api/wallets/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteWallet: (id: number) =>
    request<{ message: string }>(`/api/wallets/${id}`, { method: 'DELETE' }),
  syncWallet: (id: number, params: Record<string, any> = {}) =>
    request<{ message: string; detail: Record<string, any> }>(
      `/api/wallets/${id}/sync${query(params)}`,
      { method: 'POST' },
    ),
  walletPositions: (id: number, params: Record<string, any> = {}) =>
    request<Position[]>(`/api/wallets/${id}/positions${query(params)}`),
  walletActivity: (id: number, params: Record<string, any> = {}) =>
    request<Transaction[]>(`/api/wallets/${id}/activity${query(params)}`),
  rankings: (params: Record<string, any> = {}) =>
    request<Ranking[]>(`/api/wallets/rankings${query(params)}`),
  importWallets: async (file: File) => {
    const form = new FormData()
    form.append('file', file)
    const response = await fetch(`${BASE}/api/wallets/import`, { method: 'POST', body: form })
    if (!response.ok) throw new ApiError('import failed', response.status)
    return (await response.json()) as { added: number; skipped_existing: number; errors: string[] }
  },
  discoverWallets: (params: Record<string, any> = {}) =>
    request<{ message: string; detail: Record<string, any> }>(
      `/api/wallets/discover${query(params)}`,
      { method: 'POST' },
    ),

  markets: (params: Record<string, any> = {}) =>
    request<Market[]>(`/api/markets${query(params)}`),
  market: (id: number) => request<MarketDetail>(`/api/markets/${id}`),
  reviewQueue: () => request<Market[]>('/api/markets/review-queue'),

  signals: (params: Record<string, any> = {}) =>
    request<Signal[]>(`/api/signals${query(params)}`),
  signal: (id: number) => request<Signal>(`/api/signals/${id}`),
  scanSignals: (params: Record<string, any> = {}) =>
    request<{ message: string; detail: Record<string, any> }>(
      `/api/signals/scan${query(params)}`,
      { method: 'POST' },
    ),
  alerts: (params: Record<string, any> = {}) =>
    request<AlertRow[]>(`/api/signals/alerts${query(params)}`),
  markAlertRead: (id: number) =>
    request<{ message: string }>(`/api/signals/alerts/${id}/read`, { method: 'POST' }),

  paperTrades: (params: Record<string, any> = {}) =>
    request<PaperTrade[]>(`/api/paper/trades${query(params)}`),
  paperSummary: (params: Record<string, any> = {}) =>
    request<PaperSummary>(`/api/paper/summary${query(params)}`),
  paperRisk: () => request<Record<string, any>>('/api/paper/risk'),
  managePaper: () =>
    request<{ message: string; detail: Record<string, any> }>('/api/paper/manage', {
      method: 'POST',
    }),

  backtests: () => request<BacktestRun[]>('/api/backtests'),
  backtest: (id: number) => request<BacktestRun>(`/api/backtests/${id}`),
  backtestTrades: (id: number, params: Record<string, any> = {}) =>
    request<BacktestTrade[]>(`/api/backtests/${id}/trades${query(params)}`),
  createBacktest: (body: Record<string, unknown>) =>
    request<BacktestRun>('/api/backtests', { method: 'POST', body: JSON.stringify(body) }),
  deleteBacktest: (id: number) =>
    request<{ message: string }>(`/api/backtests/${id}`, { method: 'DELETE' }),

  jobsStatus: () => request<Record<string, any>>('/api/jobs/status'),
  runJob: (id: string) =>
    request<Record<string, any>>(`/api/jobs/${id}/run`, { method: 'POST' }),
  report: (period: 'daily' | 'weekly') =>
    request<Record<string, any>>(`/api/reports/${period}`),
}

export interface AsyncState<T> {
  data: T | null
  error: string | null
  loading: boolean
  reload: () => void
}

/** Fetch on mount (and whenever `deps` change), with optional polling. */
export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
  options: { pollMs?: number } = {},
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [nonce, setNonce] = useState(0)
  // Keeping the fetcher in a ref lets callers pass an inline closure without
  // re-running the effect on every render.
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const reload = useCallback(() => setNonce((n) => n + 1), [])

  useEffect(() => {
    let cancelled = false

    const run = async () => {
      try {
        const result = await fetcherRef.current()
        if (!cancelled) {
          setData(result)
          setError(null)
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    setLoading(true)
    void run()

    if (options.pollMs) {
      const timer = setInterval(run, options.pollMs)
      return () => {
        cancelled = true
        clearInterval(timer)
      }
    }
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce, options.pollMs])

  return { data, error, loading, reload }
}

/**
 * Subscribe to the signal SSE stream.
 *
 * Falls back silently if the stream drops: the feed pages also poll, so a lost
 * stream degrades to slower updates rather than a blank screen.
 */
export function useSignalStream(onSignal: (signal: Signal) => void, enabled = true) {
  const [connected, setConnected] = useState(false)
  const handlerRef = useRef(onSignal)
  handlerRef.current = onSignal

  useEffect(() => {
    if (!enabled) return
    const source = new EventSource(`${BASE}/api/signals/stream`)

    source.addEventListener('connected', () => setConnected(true))
    source.addEventListener('signal', (event) => {
      try {
        handlerRef.current(JSON.parse((event as MessageEvent).data) as Signal)
      } catch {
        // A malformed frame should not kill the stream.
      }
    })
    source.onerror = () => setConnected(false)

    return () => source.close()
  }, [enabled])

  return connected
}
