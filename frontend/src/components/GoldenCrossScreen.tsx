import { useState, useRef, useEffect } from 'react'
import { Card, Tag, Button, Typography, Empty, Progress, Space, InputNumber } from 'antd'
import { ReloadOutlined, ThunderboltOutlined, PauseCircleOutlined, PlayCircleOutlined } from '@ant-design/icons'
import { api } from '../api/client'
import type { GoldenCrossItem } from '../types'

const LS_KEY = 'gcScanId'
const RESULTS_KEY = 'gcScanResults'

export default function GoldenCrossScreen() {
  const [cachedData, setCachedData] = useState<GoldenCrossItem[]>([])
  const [cachedLoading, setCachedLoading] = useState(false)
  const [fullResults, setFullResults] = useState<GoldenCrossItem[]>(() => {
    try { return JSON.parse(localStorage.getItem(RESULTS_KEY) || '[]') } catch { return [] }
  })
  const [scanId, setScanId] = useState<string | null>(null)
  const [scanStatus, setScanStatus] = useState<string>('')
  const [scanTotal, setScanTotal] = useState(0)
  const [scanProcessed, setScanProcessed] = useState(0)
  const [seekValue, setSeekValue] = useState<number | null>(null)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
  }

  const startPolling = (sid: string) => {
    stopPolling()
    pollingRef.current = setInterval(async () => {
      try {
        const res = await api.getFullScanStatus(sid)
        setScanStatus(res.status)
        setScanTotal(res.total)
        setScanProcessed(res.processed)
        setFullResults(res.results)
        localStorage.setItem(RESULTS_KEY, JSON.stringify(res.results))
        if (res.status === 'completed' || res.status === 'cancelled') {
          localStorage.removeItem(LS_KEY)
          stopPolling()
        }
      } catch {
        localStorage.removeItem(LS_KEY)
        stopPolling()
      }
    }, 1000)
  }

  useEffect(() => {
    const saved = localStorage.getItem(LS_KEY)
    if (saved) {
      api.checkFullScanExists(saved).then((res) => {
        if (res.exists) {
          setScanId(saved)
          setScanStatus(res.status || 'running')
          startPolling(saved)
        } else {
          localStorage.removeItem(LS_KEY)
        }
      }).catch(() => localStorage.removeItem(LS_KEY))
    }
    return () => stopPolling()
  }, [])

  const handleCachedScan = async () => {
    setCachedLoading(true)
    try {
      const result = await api.getGoldenCrossStocks()
      setCachedData(result)
    } catch {
      setCachedData([])
    } finally {
      setCachedLoading(false)
    }
  }

  const handleFullScan = async () => {
    setFullResults([])
    localStorage.removeItem(RESULTS_KEY)
    try {
      const { scan_id } = await api.startFullScan()
      localStorage.setItem(LS_KEY, scan_id)
      setScanId(scan_id)
      setScanStatus('running')
      startPolling(scan_id)
    } catch {
      setScanStatus('')
    }
  }

  const handlePause = async () => {
    if (scanId) {
      await api.pauseFullScan(scanId)
      setScanStatus('paused')
    }
  }

  const handleResume = async () => {
    if (scanId) {
      await api.resumeFullScan(scanId)
      setScanStatus('running')
    }
  }

  const handleSeek = async () => {
    if (scanId && seekValue !== null && seekValue >= 0) {
      await api.seekFullScan(scanId, seekValue)
      setScanProcessed(seekValue)
    }
  }

  const clearFullScan = () => {
    localStorage.removeItem(LS_KEY)
    localStorage.removeItem(RESULTS_KEY)
    stopPolling()
    setScanId(null)
    setScanStatus('')
    setScanTotal(0)
    setScanProcessed(0)
    setFullResults([])
  }

  const isFullScanning = scanStatus === 'running' || scanStatus === 'paused'
  const isRunning = scanStatus === 'running'
  const displayResults = fullResults.length > 0 ? fullResults : cachedData

  return (
    <Card
      size="small"
      title={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>金叉筛选</span>
          <Space size={4}>
            <Button size="small" icon={<ReloadOutlined />} loading={cachedLoading} onClick={handleCachedScan}>
              缓存扫描
            </Button>
            {isFullScanning ? (
              <>
                {isRunning ? (
                  <Button size="small" icon={<PauseCircleOutlined />} onClick={handlePause}>暂停</Button>
                ) : (
                  <Button size="small" icon={<PlayCircleOutlined />} onClick={handleResume}>继续</Button>
                )}
              </>
            ) : (
              <Button size="small" icon={<ThunderboltOutlined />} onClick={handleFullScan}>全量扫描</Button>
            )}
          </Space>
        </div>
      }
      styles={{ body: { padding: displayResults.length === 0 && !isFullScanning ? 12 : '4px 12px', maxHeight: 500, overflowY: 'auto' } }}
    >
      {isFullScanning && (
        <div style={{ padding: '8px 0' }}>
          <Progress
            percent={scanTotal > 0 ? Math.round((scanProcessed / scanTotal) * 100) : 0}
            size="small"
            format={() => `${scanProcessed} / ${scanTotal}`}
          />
          <div style={{ marginTop: 6, display: 'flex', gap: 4, alignItems: 'center' }}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>跳转到:</Typography.Text>
            <InputNumber
              size="small"
              min={0}
              max={scanTotal}
              value={seekValue !== null ? seekValue : scanProcessed}
              onChange={(v) => setSeekValue(v)}
              style={{ width: 90 }}
            />
            <Button size="small" onClick={handleSeek} disabled={seekValue === null}>跳转</Button>
            <Button size="small" danger onClick={clearFullScan}>清除</Button>
          </div>
        </div>
      )}
      {displayResults.length === 0 && !isFullScanning ? (
        <Empty description="点击缓存扫描或全量扫描" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        displayResults.map((item) => (
          <div key={item.symbol} style={{ marginBottom: 8, padding: '6px 0', borderBottom: '1px solid #f0f0f0' }}>
            <div style={{ marginBottom: 2 }}>
              <Tag color="blue">{item.symbol}</Tag>
              <Typography.Text strong>{item.name}</Typography.Text>
              <Tag color={item.signal_type === 'combined_gc_macd' ? 'magenta' : 'red'} style={{ marginLeft: 6 }}>
                {item.signal_type === 'combined_gc_macd' ? '共振' : '金叉'}
              </Tag>
            </div>
            <div style={{ fontSize: 12, color: '#666' }}>
              {item.date} 价格: {item.price.toFixed(2)}
            </div>
            <div style={{ fontSize: 12, color: '#999', marginTop: 2 }}>{item.description}</div>
          </div>
        ))
      )}
    </Card>
  )
}