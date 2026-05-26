export function formatPrice(v: number): string {
  return v.toFixed(2)
}

export function formatPercent(v: number): string {
  return `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`
}

export function formatVolume(v: number): string {
  if (v >= 1e8) return `${(v / 1e8).toFixed(2)}亿`
  if (v >= 1e4) return `${(v / 1e4).toFixed(2)}万`
  return v.toFixed(0)
}

export const SIGNAL_COLORS: Record<string, string> = {
  golden_cross: '#f5222d',
  pullback: '#1890ff',
  convergence: '#faad14',
  macd_plus: '#722ed1',
  combined_gc_macd: '#eb2f96',
  stop_loss_ma5: '#ff7a45',
  stop_loss_ma20: '#f5222d',
  death_cross: '#52c41a',
  backtest_buy: '#52c41a',
  backtest_sell: '#f5222d',
}

export const SIGNAL_LABELS: Record<string, string> = {
  golden_cross: '金叉买点',
  pullback: '回踩买点',
  convergence: '均线粘合',
  macd_plus: 'MACD+买点',
  combined_gc_macd: '金叉+MACD+共振',
  stop_loss_ma5: '止损(跌破MA5)',
  stop_loss_ma20: '止损(放量破MA20)',
  death_cross: '死叉卖出',
  backtest_buy: '回测买入',
  backtest_sell: '回测卖出',
}
