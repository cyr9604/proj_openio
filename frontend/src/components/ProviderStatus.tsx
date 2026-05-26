import { useEffect, useState } from 'react'
import { Card, Table, Tag, Descriptions } from 'antd'
import { api } from '../api/client'
import type { ProviderStatusResponse } from '../types'

export default function ProviderStatusPanel() {
  const [data, setData] = useState<ProviderStatusResponse | null>(null)

  useEffect(() => {
    api.getProviderStatus().then(setData).catch(() => {})
  }, [])

  if (!data) return null

  const columns = [
    { title: '行情源', dataIndex: 'name', key: 'name' },
    {
      title: '可用',
      dataIndex: 'available',
      key: 'available',
      render: (v: boolean) => (v ? <Tag color="green">是</Tag> : <Tag color="red">否</Tag>),
    },
    {
      title: '已配置',
      dataIndex: 'configured',
      key: 'configured',
      render: (v: boolean) => (v ? <Tag color="green">是</Tag> : <Tag color="orange">否</Tag>),
    },
    { title: '最近同步', dataIndex: 'last_sync', key: 'last_sync', render: (v: string | null) => v || '-' },
    { title: '错误', dataIndex: 'error', key: 'error', render: (v: string) => v || '-' },
  ]

  return (
    <Card title="行情源状态" size="small">
      <Descriptions size="small" style={{ marginBottom: 12 }}>
        <Descriptions.Item label="当前优先级">
          {data.current_priority.join(' > ')}
        </Descriptions.Item>
      </Descriptions>
      <Table
        dataSource={data.providers}
        columns={columns}
        rowKey="name"
        pagination={false}
        size="small"
      />
    </Card>
  )
}
