const BASE = '/api'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const fullUrl = `${BASE}${url}`
  const method = options?.method || 'GET'
  console.debug(`[API] ${method} ${fullUrl}`)
  const res = await fetch(fullUrl, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const errMsg = `HTTP ${res.status}: ${res.statusText}`
    console.error(`[API] ${errMsg} for ${method} ${fullUrl}`)
    throw new Error(errMsg)
  }
  return res.json()
}

export const api = {
  searchStocks: (q: string) =>
    request<{ symbol: string; name: string; exchange: string }[]>(
      `/stocks/search?q=${encodeURIComponent(q)}`
    ),

  getWatchlist: () =>
    request<{ symbol: string; name: string; added_at: string }[]>('/watchlist'),

  addWatchlist: (symbol: string, name: string) =>
    request('/watchlist', {
      method: 'POST',
      body: JSON.stringify({ symbol, name }),
    }),

  removeWatchlist: (symbol: string) =>
    request(`/watchlist/${symbol}`, { method: 'DELETE' }),

  analyzeStock: (symbol: string, adjust = 'forward') =>
    request<import('../types').AnalysisResult>(
      `/analysis/${symbol}?adjust=${adjust}`
    ),

  runBacktest: (params: {
    symbol: string
    start_date: string
    end_date: string
    initial_capital: number
    adjust?: string
  }) =>
    request<import('../types').BacktestResult>('/backtest', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  getGoldenCrossStocks: () =>
    request<import('../types').GoldenCrossItem[]>('/stocks/golden-cross'),

  startFullScan: () =>
    request<{ scan_id: string }>('/stocks/golden-cross/full-scan', { method: 'POST' }),

  getFullScanStatus: (scanId: string) =>
    request<import('../types').FullScanStatus>(`/stocks/golden-cross/full-scan/${scanId}`),

  pauseFullScan: (scanId: string) =>
    request<{ status: string }>(`/stocks/golden-cross/full-scan/${scanId}/pause`, { method: 'POST' }),

  resumeFullScan: (scanId: string) =>
    request<{ status: string }>(`/stocks/golden-cross/full-scan/${scanId}/resume`, { method: 'POST' }),

  seekFullScan: (scanId: string, index: number) =>
    request<{ status: string }>(`/stocks/golden-cross/full-scan/${scanId}/seek?index=${index}`, { method: 'POST' }),

  checkFullScanExists: (scanId: string) =>
    request<{ exists: boolean; status?: string }>(`/stocks/golden-cross/full-scan/${scanId}/exists`),

  getWatchlistSignals: () =>
    request<import('../types').WatchlistSignalInfo[]>('/watchlist/signals'),

  getProviderStatus: () =>
    request<import('../types').ProviderStatusResponse>('/providers/status'),

  getSettings: () => request('/settings/provider'),

  saveSettings: (data: Record<string, unknown>) =>
    request('/settings/provider', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
}