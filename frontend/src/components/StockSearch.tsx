import { useState, useEffect, useRef } from 'react'
import { Input, List, Card } from 'antd'
import { api } from '../api/client'
import type { StockSearchItem } from '../types'

interface Props {
  onSelect: (item: StockSearchItem) => Promise<void> | void
}

export default function StockSearch({ onSelect }: Props) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<StockSearchItem[]>([])
  const [loading, setLoading] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout>>()

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current)
    if (!query.trim()) {
      setResults([])
      return
    }
    timer.current = setTimeout(async () => {
      try {
        const data = await api.searchStocks(query)
        setResults(data)
      } catch {
        setResults([])
      }
    }, 300)
    return () => {
      if (timer.current) clearTimeout(timer.current)
    }
  }, [query])

  const handleSelect = async (item: StockSearchItem) => {
    setLoading(true)
    try {
      await onSelect(item)
      setQuery('')
      setResults([])
    } catch {
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ position: 'relative' }}>
      <Input.Search
        placeholder="输入股票代码或名称搜索"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        enterButton
        size="large"
        loading={loading}
      />
      {results.length > 0 && (
        <Card
          size="small"
          style={{
            position: 'absolute',
            top: 46,
            left: 0,
            right: 0,
            zIndex: 100,
            maxHeight: 320,
            overflow: 'auto',
          }}
        >
          <List
            size="small"
            dataSource={results}
            renderItem={(item) => (
              <List.Item
                onClick={() => handleSelect(item)}
                style={{ cursor: 'pointer' }}
              >
                <strong>{item.symbol}</strong> - {item.name}
              </List.Item>
            )}
          />
        </Card>
      )}
    </div>
  )
}