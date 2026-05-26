import { useState } from 'react'
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom'
import { ConfigProvider, Layout, Menu, Typography, message } from 'antd'
import { HomeOutlined, SettingOutlined } from '@ant-design/icons'
import zhCN from 'antd/locale/zh_CN'

import HomePage from './pages/HomePage'
import SettingsPage from './pages/SettingsPage'
import { api } from './api/client'

const { Header, Content } = Layout

function AppLayout() {
  const navigate = useNavigate()
  const [refreshKey, setRefreshKey] = useState(0)

  const handleAddWatchlist = async (symbol: string, name: string) => {
    const res: any = await api.addWatchlist(symbol, name)
    if (res?.status === 'ok') {
      message.success(`已添加 ${name || symbol}`)
    } else if (res?.status === 'exists') {
      message.info(`${name || symbol} 已在自选股中`)
    } else {
      message.error(`添加自选失败`)
      throw new Error('添加自选失败')
    }
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '0 24px',
          background: '#001529',
        }}
      >
        <Typography.Title level={4} style={{ color: '#fff', margin: 0, marginRight: 40 }}>
          A股520均线分析系统
        </Typography.Title>
        <Menu
          theme="dark"
          mode="horizontal"
          defaultSelectedKeys={['home']}
          items={[
            { key: 'home', icon: <HomeOutlined />, label: '首页', onClick: () => navigate('/') },
            { key: 'settings', icon: <SettingOutlined />, label: '配置', onClick: () => navigate('/settings') },
          ]}
          style={{ flex: 1, minWidth: 0 }}
        />
      </Header>
      <Content style={{ padding: 24, background: '#f0f2f5' }}>
        <Routes>
          <Route
            path="/"
            element={
              <HomePage
                onAnalyze={() => {}}
                onAddWatchlist={handleAddWatchlist}
                refreshKey={refreshKey}
                setRefreshKey={setRefreshKey}
              />
            }
          />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </Content>
    </Layout>
  )
}

export default function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <AppLayout />
      </BrowserRouter>
    </ConfigProvider>
  )
}