import { useState } from 'react'
import { Card, Descriptions, Tag, Table, Alert, Progress, Select } from 'antd'
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  MinusOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons'
import type { AnalysisResult } from '../types'

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
  golden_cross: '金叉买点',
  pullback: '回踩买点',
  convergence: '均线粘合',
  macd_plus: 'MACD+买点',
  combined_gc_macd: '金叉+MACD+共振',
  stop_loss_ma5: '止损(跌破5日线)',
  stop_loss_ma20: '止损(放量破20日线)',
  death_cross: '死叉',
  take_profit_normal: '常规止盈',
}

interface Props {
  result: AnalysisResult | null
  loading: boolean
}

export default function AnalysisPanel({ result, loading }: Props) {
  const [filterType, setFilterType] = useState<string | undefined>(undefined)

  if (!result && !loading) {
    return <Card><Alert type="info" message="请先搜索或选择一只股票进行分析" showIcon /></Card>
  }
  if (!result) return null

  const trendIcon = {
    up: <ArrowUpOutlined style={{ color: '#f5222d' }} />,
    down: <ArrowDownOutlined style={{ color: '#52c41a' }} />,
    flat: <MinusOutlined style={{ color: '#faad14' }} />,
  }

  const riskLevel = {
    low: <Tag color="green">低</Tag>,
    medium: <Tag color="orange">中</Tag>,
    high: <Tag color="red">高</Tag>,
  }

  const signalColumns = [
    { title: '日期', dataIndex: 'date', key: 'date', width: 110 },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 130,
      render: (t: string) => (
        <Tag color={typeColors[t] || 'default'}>{typeNames[t] || t}</Tag>
      ),
    },
    { title: '说明', dataIndex: 'description', key: 'description' },
    { title: '价格', dataIndex: 'price', key: 'price', width: 90 },
  ]

  return (
    <Card title={`${result.name || result.symbol} 分析结果`} loading={loading}>
      <Descriptions column={2} bordered size="small">
        <Descriptions.Item label="代码">{result.symbol}</Descriptions.Item>
        <Descriptions.Item label="名称">{result.name || '-'}</Descriptions.Item>
        <Descriptions.Item label="最后交易日">{result.last_date}</Descriptions.Item>
        <Descriptions.Item label="收盘价">{result.last_close.toFixed(2)}</Descriptions.Item>
        <Descriptions.Item label="趋势" span={2}>
          {trendIcon[result.trend.direction as keyof typeof trendIcon] || null}{' '}
          {result.trend.description}
        </Descriptions.Item>
        <Descriptions.Item label="风险等级">{riskLevel[result.risk.risk_level as keyof typeof riskLevel] || <Tag>未知</Tag>}</Descriptions.Item>
        <Descriptions.Item label="风险提示">{result.risk.stop_loss_desc || '无'}</Descriptions.Item>
      </Descriptions>

      <Card
        size="small"
        title="仓位建议"
        style={{ marginTop: 16 }}
      >
        <Progress
          percent={result.position.recommended_pct}
          format={(pct) => `建议 ${pct}%`}
          strokeColor={result.position.recommended_pct > 0 ? '#1890ff' : '#d9d9d9'}
        />
        <div style={{ marginTop: 8, color: '#666' }}>{result.position.advice_text}</div>
        <div style={{ color: '#999', fontSize: 12 }}>最高仓位: {result.position.max_pct}%</div>
      </Card>

      <Card size="small" title="信号列表" style={{ marginTop: 16 }}>
        {result.signals.length === 0 ? (
          <Alert type="info" message="当前无信号" showIcon />
        ) : (
          <>
            <div style={{ marginBottom: 12 }}>
              <Select
                allowClear
                placeholder="按类型筛选"
                style={{ width: 160 }}
                value={filterType}
                onChange={(val) => setFilterType(val)}
                options={[
                  ...new Set(result.signals.map((s) => s.type)),
                ].map((t) => ({ value: t, label: typeNames[t] || t }))}
              />
            </div>
            <Table
              dataSource={[...result.signals]
                .filter((s) => !filterType || s.type === filterType)
                .sort((a, b) => b.date.localeCompare(a.date))}
              columns={signalColumns}
              rowKey={(record: any) => `${record.date}-${record.type}`}
              pagination={{ pageSize: 20, showSizeChanger: true, pageSizeOptions: ['10', '20', '50', '100'] }}
              size="small"
            />
          </>
        )}
      </Card>
    </Card>
  )
}
