import { useState, useEffect } from 'react'
import { Row, Col, Tabs, Spin } from 'antd'
import StockSearch from '../components/StockSearch'
import WatchList from '../components/WatchList'
import WatchlistSignalPanel from '../components/WatchlistSignalPanel'
import GoldenCrossScreen from '../components/GoldenCrossScreen'
import ProviderStatusPanel from '../components/ProviderStatus'
import KLineChart from '../components/KLineChart'
import AnalysisPanel from '../components/AnalysisPanel'
import BacktestPanel from '../components/BacktestPanel'
import type { StockSearchItem, AnalysisResult, SignalPoint, BacktestTrade } from '../types'
import { api } from '../api/client'

interface Props {
  onAnalyze: (symbol: string) => void
  onAddWatchlist: (symbol: string, name: string) => void
  refreshKey: number
  setRefreshKey: (k: number) => void
}

export default function HomePage({ onAnalyze, onAddWatchlist, refreshKey, setRefreshKey }: Props) {
  const [selectedSymbol, setSelectedSymbol] = useState('')
  const [selectedName, setSelectedName] = useState('')
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [backtestSignals, setBacktestSignals] = useState<SignalPoint[]>([])

  // 自选股点击分析
  const handleAnalyze = (symbol: string, name: string) => {
    setSelectedSymbol(symbol)
    setSelectedName(name)
  }

  // 搜索点击添加自选
  const handleSelectAdd = async (item: StockSearchItem) => {
    await onAddWatchlist(item.symbol, item.name)
    setRefreshKey(refreshKey + 1)
  }

  // 搜索点击分析（添加到自选并分析）
  const handleSelectAnalyze = async (item: StockSearchItem) => {
    try {
      await onAddWatchlist(item.symbol, item.name)
    } catch {}
    setSelectedSymbol(item.symbol)
    setSelectedName(item.name)
    setRefreshKey(refreshKey + 1)
  }

  // 加载分析数据
  useEffect(() => {
    if (!selectedSymbol) return
    setLoading(true)
    api.analyzeStock(selectedSymbol)
      .then(setAnalysisResult)
      .catch(() => setAnalysisResult(null))
      .finally(() => setLoading(false))
  }, [selectedSymbol])

  const handleBack = () => {
    setSelectedSymbol('')
    setSelectedName('')
    setAnalysisResult(null)
  }

  const handleBacktestResult = (trades: BacktestTrade[]) => {
    const signals: SignalPoint[] = trades
      .filter((t) => t.action === '买入' || t.action === '卖出' || t.action === '加仓' || t.action === '平仓')
      .map((t) => ({
        date: t.date,
        type: (t.action === '买入' || t.action === '加仓') ? 'backtest_buy' : 'backtest_sell',
        price: t.price,
        description: t.reason,
      }))
    setBacktestSignals(signals)
  }

  return (
    <Row gutter={16}>
      <Col span={8}>
        <StockSearch onSelect={handleSelectAnalyze} />
        <div style={{ marginTop: 16 }}>
          <WatchList onSelect={handleAnalyze} refreshKey={refreshKey} />
        </div>
        <div style={{ marginTop: 16 }}>
          <WatchlistSignalPanel />
        </div>
        <div style={{ marginTop: 16 }}>
          <GoldenCrossScreen />
        </div>
        <div style={{ marginTop: 16 }}>
          <ProviderStatusPanel />
        </div>
      </Col>
      <Col span={16}>
        {loading ? (
          <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />
        ) : selectedSymbol ? (
          <Tabs
            defaultActiveKey="analysis"
            items={[
              {
                key: 'analysis',
                label: '策略分析',
                children: (
                  <>
                    <div style={{ background: '#fff', padding: 12, borderRadius: 6, marginBottom: 16 }}>
                      <KLineChart 
                        data={analysisResult?.chart_data || []} 
                        signals={analysisResult?.signals || []} 
                        backtestSignals={backtestSignals}
                        symbol={analysisResult?.symbol}
                        name={analysisResult?.name}
                      />
                    </div>
                    <AnalysisPanel result={analysisResult} loading={false} />
                  </>
                ),
              },
              {
                key: 'backtest',
                label: '回测',
                children: (
                  <>
                    <div style={{ background: '#fff', padding: 12, borderRadius: 6, marginBottom: 16 }}>
                      <KLineChart 
                        data={analysisResult?.chart_data || []} 
                        signals={analysisResult?.signals || []} 
                        backtestSignals={backtestSignals}
                        symbol={selectedSymbol}
                        name={selectedName}
                      />
                    </div>
                    <BacktestPanel symbol={selectedSymbol} onBacktestResult={handleBacktestResult} />
                  </>
                ),
              },
            ]}
          />
        ) : (
          <div style={{ padding: '60px 20px', textAlign: 'center', color: '#999' }}>
            <h2>A股 520 均线买卖分析系统</h2>
            <p>搜索或选择左侧自选股中的股票，查看详细分析</p>
            <p style={{ fontSize: 12 }}>
              本系统基于 5/20 日均线策略，提供趋势判断、买卖信号、回测验证和风险提示。<br />
              系统输出为策略辅助分析，不构成投资建议。
            </p>
          </div>
        )}
      </Col>
    </Row>
  )
}