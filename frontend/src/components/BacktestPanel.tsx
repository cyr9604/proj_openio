import { useState, useEffect } from 'react'
import ReactECharts from 'echarts-for-react'
import {
  Card, Form, InputNumber, DatePicker, Button, Statistic,
  Row, Col, Table, Alert, Spin, Select, Tag, Collapse,
} from 'antd'
import dayjs from 'dayjs'
import { api } from '../api/client'
import type { BacktestResult, BacktestTrade, StrategyDetail } from '../types'

interface Props {
  symbol: string
  onBacktestResult?: (trades: BacktestTrade[]) => void
}

const ruleColors: Record<string, string> = {
  '金叉买入': 'red',
  '回踩买入': 'blue',
  '粘合发散买入': 'gold',
  '共振买入': 'purple',
  '常规止盈': 'green',
  '死叉卖出': 'orange',
  '跌破5日线止损': 'volcano',
  '放量破20日线止损': 'red',
}

export default function BacktestPanel({ symbol, onBacktestResult }: Props) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [error, setError] = useState('')
  const [strategyName, setStrategyName] = useState('ma520')
  const [strategyDetail, setStrategyDetail] = useState<StrategyDetail | null>(null)
  const [strategyList, setStrategyList] = useState<Record<string, { name: string; description: string }>>({})

  useEffect(() => {
    api.getStrategies().then(setStrategyList).catch(() => {})
  }, [])

  useEffect(() => {
    if (strategyName) {
      api.getStrategyInfo(strategyName).then(setStrategyDetail).catch(() => setStrategyDetail(null))
    }
  }, [strategyName])

  const handleRun = async (values: any) => {
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const data = await api.runBacktest({
        symbol,
        start_date: values.range[0].format('YYYY-MM-DD'),
        end_date: values.range[1].format('YYYY-MM-DD'),
        initial_capital: values.capital || 100000,
        fee_rate: values.fee_rate / 10000,
        min_fee: values.min_fee,
        strategy: strategyName,
      })
      setResult(data)
      onBacktestResult?.(data.trades)
    } catch (e: any) {
      setError(e.message || '回测失败')
    } finally {
      setLoading(false)
    }
  }

  const tradeColumns = [
    { title: '日期', dataIndex: 'date', key: 'date', width: 110 },
    { title: '操作', dataIndex: 'action', key: 'action', width: 70 },
    { title: '价格', dataIndex: 'price', key: 'price', width: 80 },
    { title: '数量', dataIndex: 'shares', key: 'shares', width: 80 },
    { title: '金额', dataIndex: 'amount', key: 'amount', width: 90 },
    { title: '原因', dataIndex: 'reason', key: 'reason' },
  ]

  return (
    <Card title={`${symbol} 回测`} size="small">
      <div style={{ marginBottom: 16 }}>
        <div style={{ marginBottom: 8, fontWeight: 500, fontSize: 13 }}>回测策略</div>
        <Select
          value={strategyName}
          onChange={setStrategyName}
          style={{ width: 280 }}
          options={Object.entries(strategyList).map(([k, v]) => ({
            value: k,
            label: v.name,
          }))}
          placeholder="请选择回测策略"
        />
      </div>

      {strategyDetail && (
        <Collapse ghost size="small" style={{ marginBottom: 16, background: '#fafafa', borderRadius: 6 }}>
          <Collapse.Panel
            key="strategy"
            header={
              <span style={{ fontWeight: 500 }}>
                {strategyDetail.name}
                <span style={{ color: '#999', fontWeight: 400, fontSize: 12, marginLeft: 8 }}>策略规则详情</span>
              </span>
            }
          >
            <div style={{ color: '#666', fontSize: 13, marginBottom: 12 }}>{strategyDetail.description}</div>
            {strategyDetail.buy_rules.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 6, color: '#cf1322' }}>买入策略</div>
                {strategyDetail.buy_rules
                  .sort((a, b) => a.priority - b.priority)
                  .map((r, i) => (
                    <div key={i} style={{ marginBottom: 6, fontSize: 12, lineHeight: 1.8 }}>
                      <Tag color={ruleColors[r.type] || 'default'} style={{ marginRight: 6 }}>{r.type}</Tag>
                      <span style={{ color: '#666' }}>{r.condition}</span>
                      <span style={{ color: '#1890ff', marginLeft: 6 }}>→ {r.action}</span>
                    </div>
                  ))}
              </div>
            )}
            {strategyDetail.sell_rules.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 6, color: '#389e0d' }}>卖出策略</div>
                {strategyDetail.sell_rules
                  .sort((a, b) => a.priority - b.priority)
                  .map((r, i) => (
                    <div key={i} style={{ marginBottom: 6, fontSize: 12, lineHeight: 1.8 }}>
                      <Tag color={ruleColors[r.type] || 'default'} style={{ marginRight: 6 }}>{r.type}</Tag>
                      <span style={{ color: '#666' }}>{r.condition}</span>
                      <span style={{ color: '#1890ff', marginLeft: 6 }}>→ {r.action}</span>
                    </div>
                  ))}
              </div>
            )}
            {strategyDetail.add_rules.length > 0 && (
              <div>
                <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 6, color: '#d46b08' }}>加仓策略</div>
                {strategyDetail.add_rules.map((r, i) => (
                  <div key={i} style={{ marginBottom: 6, fontSize: 12, lineHeight: 1.8 }}>
                    <Tag color="geekblue" style={{ marginRight: 6 }}>加仓</Tag>
                    <span style={{ color: '#666' }}>{r.condition}</span>
                    <span style={{ color: '#1890ff', marginLeft: 6 }}>→ {r.action}</span>
                  </div>
                ))}
              </div>
            )}
          </Collapse.Panel>
        </Collapse>
      )}

      <Form layout="inline" onFinish={handleRun} initialValues={{ capital: 100000, fee_rate: 2.5, min_fee: 5, range: [dayjs().subtract(1, 'year'), dayjs()] }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', flexWrap: 'wrap', marginBottom: 12 }}>
          <Form.Item name="range" label="时间范围" rules={[{ required: true }]}>
            <DatePicker.RangePicker picker="date" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>
              运行回测
            </Button>
          </Form.Item>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', flexWrap: 'wrap' }}>
          <Form.Item name="capital" label="初始资金">
            <InputNumber min={10000} max={10000000} style={{ width: 120 }} />
          </Form.Item>
          <Form.Item name="fee_rate" label="费率">
            <InputNumber min={0} max={100} step={0.1} style={{ width: 120 }} addonAfter="‱" />
          </Form.Item>
          <Form.Item name="min_fee" label="保底费用">
            <InputNumber min={0} max={100} step={1} style={{ width: 110 }} addonAfter="元" />
          </Form.Item>
        </div>
      </Form>

      {error && <Alert type="error" message={error} style={{ marginTop: 12 }} showIcon />}

      <Spin spinning={loading}>
        {result && (
          <>
            <Row gutter={16} style={{ marginTop: 16 }}>
              <Col span={6}><Statistic title="最终资产" value={result.final_capital.toFixed(2)} prefix="¥" /></Col>
              <Col span={6}>
                <Statistic
                  title="总收益率"
                  value={result.total_return}
                  suffix="%"
                  valueStyle={{ color: result.total_return >= 0 ? '#3f8600' : '#cf1322' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="年化收益"
                  value={result.annual_return.toFixed(2)}
                  suffix="%"
                  valueStyle={{ color: result.annual_return >= 0 ? '#3f8600' : '#cf1322' }}
                />
              </Col>
              <Col span={6}><Statistic title="最大回撤" value={result.max_drawdown.toFixed(2)} suffix="%" /></Col>
              <Col span={6}><Statistic title="胜率" value={result.win_rate.toFixed(1)} suffix="%" /></Col>
              <Col span={6}><Statistic title="交易次数" value={result.total_trades} /></Col>
              <Col span={6}><Statistic title="总费用" value={result.total_fees.toFixed(2)} prefix="¥" /></Col>
            </Row>

            {result.equity_curve.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <ReactECharts
                  option={{
                    tooltip: {
                      trigger: 'axis',
                      formatter: (params: any[]) => {
                        if (!params?.length) return ''
                        const date = params[0].axisValue
                        let html = `<div style="font-weight:600;margin-bottom:4px">${date}</div>`
                        params.forEach((p: any) => {
                          const val = typeof p.value === 'number' ? p.value.toFixed(2) : p.value
                          html += `<div style="display:flex;justify-content:space-between;gap:16px">`
                          html += `<span>${p.marker} ${p.seriesName}</span>`
                          html += `<span>${p.seriesName === '持仓' ? val + '股' : '¥' + val}</span>`
                          html += `</div>`
                        })
                        return html
                      },
                    },
                    legend: { data: ['资产曲线', '持仓'], top: -2, left: 60, icon: 'line', textStyle: { fontSize: 11 } },
                    xAxis: { type: 'category', data: result.equity_curve.map(e => e.date), show: false },
                    yAxis: [
                      { type: 'value', scale: true, axisLabel: { formatter: '¥{value}' } },
                      { type: 'value', scale: true, axisLabel: { formatter: '{value}股' }, splitLine: { show: false } },
                    ],
                    grid: { left: 60, right: 60, top: 20, bottom: 20 },
                    series: [
                      {
                        name: '资产曲线',
                        type: 'line',
                        yAxisIndex: 0,
                        data: result.equity_curve.map(e => e.equity),
                        smooth: true,
                        lineStyle: { color: '#1890ff', width: 2 },
                        areaStyle: { color: 'rgba(24,144,255,0.1)' },
                        showSymbol: false,
                      },
                      {
                        name: '持仓',
                        type: 'bar',
                        yAxisIndex: 1,
                        data: result.equity_curve.map(e => e.position || 0),
                        itemStyle: { color: 'rgba(82,196,26,0.35)', borderRadius: [2, 2, 0, 0] },
                        barWidth: '60%',
                      },
                    ],
                  }}
                  style={{ height: 280 }}
                />
              </div>
            )}

            {result.trades.length > 0 && (
              <Table
                dataSource={result.trades}
                columns={tradeColumns}
                rowKey={(r) => r.date + r.action}
                size="small"
                pagination={false}
                style={{ marginTop: 16 }}
              />
            )}
          </>
        )}
      </Spin>
    </Card>
  )
}
