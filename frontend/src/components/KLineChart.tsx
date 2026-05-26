import { useRef, useEffect, useState } from 'react'
import { Checkbox } from 'antd'
import * as echarts from 'echarts'
import type { ChartBar, SignalPoint } from '../types'

const SIGNAL_OPTIONS = [
  { type: 'golden_cross', label: '金叉', color: '#f5222d' },
  { type: 'pullback', label: '回踩', color: '#1890ff' },
  { type: 'convergence', label: '粘合', color: '#faad14' },
  { type: 'macd_plus', label: 'MACD+', color: '#722ed1' },
  { type: 'combined_gc_macd', label: '共振', color: '#eb2f96' },
  { type: 'stop_loss_ma5', label: '止损MA5', color: '#ff7a45' },
  { type: 'stop_loss_ma20', label: '止损MA20', color: '#f5222d' },
  { type: 'death_cross', label: '死叉', color: '#52c41a' },
  { type: 'take_profit_normal', label: '止盈', color: '#eb2f96' },
]

const BT_SIGNAL_OPTIONS = [
  { type: 'backtest_buy', label: '回测买入', color: '#52c41a' },
  { type: 'backtest_sell', label: '回测卖出', color: '#f5222d' },
]

interface Props {
  data: ChartBar[]
  signals?: SignalPoint[]
  backtestSignals?: SignalPoint[]
  height?: number
  symbol?: string
  name?: string
}

export default function KLineChart({ data, signals = [], backtestSignals = [], height = 500, symbol, name }: Props) {
  const chartRef = useRef<HTMLDivElement>(null)
  const instanceRef = useRef<echarts.ECharts>()
  const [enabledTypes, setEnabledTypes] = useState<string[]>(['golden_cross'])
  const [btEnabledTypes, setBtEnabledTypes] = useState<string[]>(['backtest_buy', 'backtest_sell'])

  const toggleType = (type: string) => {
    setEnabledTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type],
    )
  }

  const toggleBtType = (type: string) => {
    setBtEnabledTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type],
    )
  }

  const signalColors: Record<string, string> = {
    golden_cross: '#f5222d',
    pullback: '#1890ff',
    convergence: '#faad14',
    macd_plus: '#722ed1',
    combined_gc_macd: '#eb2f96',
    stop_loss_ma5: '#ff7a45',
    stop_loss_ma20: '#f5222d',
    death_cross: '#52c41a',
    take_profit_normal: '#eb2f96',
    backtest_buy: '#52c41a',
    backtest_sell: '#f5222d',
  }
  const signalLabels: Record<string, string> = {
    golden_cross: '金叉',
    pullback: '回踩',
    convergence: '粘合',
    macd_plus: 'MACD+',
    combined_gc_macd: '共振',
    stop_loss_ma5: '止损MA5',
    stop_loss_ma20: '止损MA20',
    death_cross: '死叉',
    take_profit_normal: '止盈',
    backtest_buy: '买入',
    backtest_sell: '卖出',
  }

  const buildSignalPoints = (dates: string[], kdata: number[][]) => {
    const points: any[] = []
    const allSignals = [
      ...signals.filter((s) => enabledTypes.includes(s.type)),
      ...backtestSignals.filter((s) => btEnabledTypes.includes(s.type)),
    ]
    allSignals.forEach((s) => {
      const idx = dates.indexOf(s.date)
      if (idx === -1) return
      const color = signalColors[s.type] || '#999'
      const candle = kdata[idx]
      const isBt = s.type === 'backtest_buy' || s.type === 'backtest_sell'
      points.push({
        coord: [s.date, Math.max(candle[0], candle[1])],
        symbol: isBt ? 'pin' : 'diamond',
        symbolSize: isBt ? 24 : 12,
        symbolRotate: s.type === 'backtest_buy' ? 0 : 180,
        itemStyle: { color, borderColor: '#fff', borderWidth: 1.5 },
        label: {
          show: true,
          formatter: signalLabels[s.type] || s.type,
          position: s.type === 'backtest_buy' ? 'top' : 'bottom',
          fontSize: 9,
          color: '#fff',
          backgroundColor: color,
          padding: [1, 4],
          borderRadius: 2,
        },
      })
    })
    return points
  }

  useEffect(() => {
    if (!chartRef.current) return
    if (!instanceRef.current) {
      instanceRef.current = echarts.init(chartRef.current)
    }
    const chart = instanceRef.current

    const dates = data.map((d) => d.trade_date)
    const kdata = data.map((d) => [d.open, d.close, d.low, d.high])
    const volumes = data.map((d) => [d.trade_date, d.volume, d.open <= d.close ? 1 : -1])
    const ma5 = data.map((d) => d.ma5)
    const ma20 = data.map((d) => d.ma20)

    const signalPoints = buildSignalPoints(dates, kdata)

    chart.setOption({
      animation: false,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
      },
      legend: {
        data: [
          { name: 'MA5', textStyle: { color: '#f06292' } },
          { name: 'MA20', textStyle: { color: '#42a5f5' } },
        ],
        top: 5,
        left: 60,
        icon: 'line',
      },
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      grid: [
        { left: '8%', right: '8%', top: '5%', height: '60%' },
        { left: '8%', right: '8%', top: '73%', height: '20%' },
      ],
      xAxis: [
        {
          type: 'category',
          data: dates,
          gridIndex: 0,
          axisLine: { onZero: false },
          axisLabel: { show: false },
        },
        {
          type: 'category',
          data: dates,
          gridIndex: 1,
          axisLabel: { rotate: 45, fontSize: 10 },
        },
      ],
      yAxis: [
        { type: 'value', gridIndex: 0, scale: true, splitNumber: 5 },
        { type: 'value', gridIndex: 1, splitNumber: 3, axisLabel: { show: true } },
      ],
      dataZoom: [
        { type: 'inside', xAxisIndex: [0, 1], start: 70, end: 100 },
        { type: 'slider', xAxisIndex: [0, 1], start: 70, end: 100, bottom: 0 },
      ],
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          xAxisIndex: 0,
          yAxisIndex: 0,
          data: kdata,
          itemStyle: {
            color: '#ef5350',
            color0: '#26a69a',
            borderColor: '#ef5350',
            borderColor0: '#26a69a',
          },
          markPoint: {
            silent: true,
            data: signalPoints,
          },
        },
        {
          name: 'MA5',
          type: 'line',
          xAxisIndex: 0,
          yAxisIndex: 0,
          data: ma5,
          smooth: true,
          symbol: 'none',
          itemStyle: { color: '#f06292' },
          lineStyle: { width: 1.5, color: '#f06292' },
        },
        {
          name: 'MA20',
          type: 'line',
          xAxisIndex: 0,
          yAxisIndex: 0,
          data: ma20,
          smooth: true,
          symbol: 'none',
          itemStyle: { color: '#42a5f5' },
          lineStyle: { width: 1.5, color: '#42a5f5' },
        },
        {
          name: '成交量',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: volumes,
          itemStyle: {
            color: (params: any) => (params.data[2] > 0 ? '#ef5350' : '#26a69a'),
          },
        },
      ],
    }, true)

    const resize = () => chart.resize()
    window.addEventListener('resize', resize)
    return () => window.removeEventListener('resize', resize)
  }, [data])

  useEffect(() => {
    const chart = instanceRef.current
    if (!chart || !data.length) return
    const dates = data.map((d) => d.trade_date)
    const kdata = data.map((d) => [d.open, d.close, d.low, d.high])
    const signalPoints = buildSignalPoints(dates, kdata)
    chart.setOption({ series: [{ markPoint: { data: signalPoints } }] })
  }, [signals, backtestSignals, enabledTypes, btEnabledTypes, data])

  return (
    <div>
      <div style={{ position: 'relative' }}>
        {symbol && (
          <div style={{ position: 'absolute', top: 4, right: 16, zIndex: 10, fontSize: 13, fontWeight: 600, color: '#333' }}>
            {name ? `${name} (${symbol})` : symbol}
          </div>
        )}
        <div style={{ marginBottom: 6, display: 'flex', flexWrap: 'wrap', gap: 8, fontSize: 12 }}>
          {SIGNAL_OPTIONS.map((opt) => (
            <Checkbox
              key={opt.type}
              checked={enabledTypes.includes(opt.type)}
              onChange={() => toggleType(opt.type)}
              style={{ color: opt.color, fontSize: 12 }}
            >
              {opt.label}
            </Checkbox>
          ))}
        </div>
        {backtestSignals.length > 0 && (
          <div style={{ marginBottom: 6, display: 'flex', flexWrap: 'wrap', gap: 8, fontSize: 12, alignItems: 'center' }}>
            <span style={{ color: '#999', fontSize: 11 }}>回测信号</span>
            {BT_SIGNAL_OPTIONS.map((opt) => (
              <Checkbox
                key={opt.type}
                checked={btEnabledTypes.includes(opt.type)}
                onChange={() => toggleBtType(opt.type)}
                style={{ color: opt.color, fontSize: 12 }}
              >
                {opt.label}
              </Checkbox>
            ))}
          </div>
        )}
        <div ref={chartRef} style={{ width: '100%', height }} />
      </div>
    </div>
  )
}
