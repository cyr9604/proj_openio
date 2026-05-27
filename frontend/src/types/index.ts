export interface StockSearchItem {
  symbol: string
  name: string
  exchange: string
}

export interface WatchlistItem {
  symbol: string
  name: string
  added_at: string
}

export interface ChartBar {
  trade_date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  ma5: number | null
  ma20: number | null
}

export interface TrendInfo {
  direction: string
  description: string
}

export interface SignalPoint {
  date: string
  type: string
  description: string
  price: number
}

export interface PositionAdvice {
  recommended_pct: number
  max_pct: number
  advice_text: string
}

export interface RiskWarning {
  stop_loss: number | null
  stop_loss_desc: string
  risk_level: string
}

export interface AnalysisResult {
  symbol: string
  name: string
  last_date: string
  last_close: number
  trend: TrendInfo
  signals: SignalPoint[]
  position: PositionAdvice
  risk: RiskWarning
  chart_data: ChartBar[]
}

export interface BacktestTrade {
  date: string
  action: string
  price: number
  shares: number
  amount: number
  reason: string
}

export interface BacktestResult {
  symbol: string
  start_date: string
  end_date: string
  initial_capital: number
  final_capital: number
  total_return: number
  annual_return: number
  max_drawdown: number
  win_rate: number
  total_trades: number
  total_fees: number
  trades: BacktestTrade[]
  equity_curve: { date: string; equity: number; position: number }[]
}

export interface ProviderStatus {
  name: string
  available: boolean
  configured: boolean
  last_sync: string | null
  error: string
}

export interface GoldenCrossItem {
  symbol: string
  name: string
  price: number
  date: string
  signal_type: string
  description: string
}

export interface FullScanStatus {
  scan_id: string
  status: string
  total: number
  processed: number
  results: GoldenCrossItem[]
}

export interface WatchlistSignalInfo {
  symbol: string
  name: string
  signals: SignalPoint[]
}

export interface ProviderStatusResponse {
  providers: ProviderStatus[]
  current_priority: string[]
}

export interface StrategyRule {
  type: string
  condition: string
  action: string
  priority: number
}

export interface StrategyDetail {
  name: string
  description: string
  buy_rules: StrategyRule[]
  sell_rules: StrategyRule[]
  add_rules: StrategyRule[]
}

export interface StrategySummary {
  name: string
  description: string
}
