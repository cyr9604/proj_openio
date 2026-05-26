import { useEffect, useState } from 'react'
import { Spin, Tabs } from 'antd'
import KLineChart from '../components/KLineChart'
import AnalysisPanel from '../components/AnalysisPanel'
import BacktestPanel from '../components/BacktestPanel'
import { api } from '../api/client'
import type { AnalysisResult } from '../types'

interface Props {
  symbol: string
}

export default function AnalysisPage({ symbol }: Props) {
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!symbol) return
    setLoading(true)
    api.analyzeStock(symbol)
      .then(setResult)
      .catch(() => setResult(null))
      .finally(() => setLoading(false))
  }, [symbol])

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />

  return (
    <Tabs
      defaultActiveKey="analysis"
      items={[
        {
          key: 'analysis',
          label: '策略分析',
          children: (
            <>
              <div style={{ background: '#fff', padding: 12, borderRadius: 6, marginBottom: 16 }}>
                <KLineChart data={result?.chart_data || []} signals={result?.signals || []} symbol={result?.symbol} name={result?.name} />
              </div>
              <AnalysisPanel result={result} loading={false} />
            </>
          ),
        },
        {
          key: 'backtest',
          label: '回测',
          children: <BacktestPanel symbol={symbol} />,
        },
      ]}
    />
  )
}
