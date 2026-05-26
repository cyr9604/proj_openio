import { useEffect, useState } from 'react'
import { List, Button, Tag, Popconfirm, Typography } from 'antd'
import { DeleteOutlined, LineChartOutlined } from '@ant-design/icons'
import { api } from '../api/client'
import type { WatchlistItem } from '../types'

interface Props {
  onSelect: (symbol: string, name: string) => void
  refreshKey: number
}

export default function WatchList({ onSelect, refreshKey }: Props) {
  const [items, setItems] = useState<WatchlistItem[]>([])

  const load = async () => {
    try {
      const data = await api.getWatchlist()
      setItems(data)
    } catch {
      setItems([])
    }
  }

  useEffect(() => {
    load()
  }, [refreshKey])

  const handleRemove = async (symbol: string) => {
    await api.removeWatchlist(symbol)
    load()
  }

  return (
    <List
      size="small"
      header={<Typography.Text strong>自选股</Typography.Text>}
      dataSource={items}
      locale={{ emptyText: '暂无自选股，请搜索添加' }}
      renderItem={(item) => (
        <List.Item
          actions={[
            <Button
              type="link"
              icon={<LineChartOutlined />}
              onClick={() => onSelect(item.symbol, item.name)}
            >
              分析
            </Button>,
            <Popconfirm title="确定删除？" onConfirm={() => handleRemove(item.symbol)}>
              <Button type="link" danger icon={<DeleteOutlined />} />
            </Popconfirm>,
          ]}
        >
          <Tag color="blue">{item.symbol}</Tag>
          {item.name}
        </List.Item>
      )}
    />
  )
}
