import { useEffect, useState } from 'react'
import { Card, Tag, Typography, Button, Empty } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { api } from '../api/client'
import type { WatchlistSignalInfo } from '../types'

const typeColors: Record<string, string> = {
  golden_cross: 'red',
  pullback: 'blue',
  convergence: 'gold',
  macd_plus: 'purple',
  combined_gc_macd: 'magenta',
  stop_loss_ma5: 'orange',
  stop_loss_ma20: 'red',
  death_cross: 'green',
  take_profit_normal: 'pink',
}

const typeNames: Record<string, string> = {
  golden_cross: '金叉',
  pullback: '回踩',
  convergence: '粘合',
  macd_plus: 'MACD+',
  combined_gc_macd: '共振',
  stop_loss_ma5: '止损5日',
  stop_loss_ma20: '止损20日',
  death_cross: '死叉',
  take_profit_normal: '止盈',
}

export default function WatchlistSignalPanel() {
  const [data, setData] = useState<WatchlistSignalInfo[]>([])
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const result = await api.getWatchlistSignals()
      setData(result)
    } catch {
      setData([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <Card
      size="small"
      title={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>自选股近3天信号</span>
          <Button size="small" icon={<ReloadOutlined />} loading={loading} onClick={load}>刷新</Button>
        </div>
      }
      styles={{ body: { padding: data.length === 0 ? 12 : '4px 12px', maxHeight: 400, overflowY: 'auto' } }}
    >
      {data.length === 0 ? (
        <Empty description="暂无信号" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        data.map((item) => (
          <div key={item.symbol} style={{ marginBottom: 8, padding: '6px 0', borderBottom: '1px solid #f0f0f0' }}>
            <div style={{ marginBottom: 4 }}>
              <Tag color="blue">{item.symbol}</Tag>
              <Typography.Text strong>{item.name}</Typography.Text>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {item.signals.map((s, i) => (
                <Tag key={i} color={typeColors[s.type] || 'default'} title={s.description}>
                  {s.date.slice(5)} {typeNames[s.type] || s.type}
                </Tag>
              ))}
            </div>
          </div>
        ))
      )}
    </Card>
  )
}