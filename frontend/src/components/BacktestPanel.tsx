import { useState } from 'react'
import ReactECharts from 'echarts-for-react'
import {
  Card, Form, Input, InputNumber, DatePicker, Button, Statistic,
  Row, Col, Table, Alert, Spin,
} from 'antd'
import dayjs from 'dayjs'
import { api } from '../api/client'
import type { BacktestResult, BacktestTrade } from '../types'

interface Props {
  symbol: string
  onBacktestResult?: (trades: BacktestTrade[]) => void
}

export default function BacktestPanel({ symbol, onBacktestResult }: Props) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [error, setError] = useState('')

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
      <Form layout="inline" onFinish={handleRun} initialValues={{ capital: 100000 }}>
        <Form.Item name="range" label="时间范围" rules={[{ required: true }]}>
          <DatePicker.RangePicker
            picker="date"
            defaultValue={[dayjs().subtract(1, 'year'), dayjs()]}
          />
        </Form.Item>
        <Form.Item name="capital" label="初始资金">
          <InputNumber min={10000} max={10000000} style={{ width: 120 }} />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>
            运行回测
          </Button>
        </Form.Item>
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
