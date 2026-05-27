import { useEffect, useState } from 'react'
import { Card, Form, Select, Input, Switch, Button, message, Alert } from 'antd'
import { api } from '../api/client'

export default function SettingsPanel() {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.getSettings().then((data) => form.setFieldsValue(data)).catch(() => {})
  }, [form])

  const handleSave = async (values: any) => {
    setLoading(true)
    try {
      await api.saveSettings(values)
      message.success('保存成功')
    } catch {
      message.error('保存失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card title="行情源配置">
      <Alert
        type="info"
        message="Baostock 和 Efinance 免费可用无需配置；同花顺 HTTP 模式需要 refresh_token；SDK 模式需本机安装 iFinD 环境。"
        style={{ marginBottom: 16 }}
        showIcon
      />
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSave}
        initialValues={{
          priority: ['baostock', 'efinance', 'ths_http', 'ths_sdk', 'akshare'],
          ths_http_token: '',
          ths_http_refresh_token: '',
          ths_sdk_enabled: false,
          default_adjust: 'forward',
        }}
        style={{ maxWidth: 600 }}
      >
        <Form.Item name="priority" label="行情源优先级">
          <Select mode="multiple">
            <Select.Option value="baostock">Baostock</Select.Option>
            <Select.Option value="efinance">Efinance (东方财富)</Select.Option>
            <Select.Option value="ths_http">同花顺 HTTP</Select.Option>
            <Select.Option value="ths_sdk">同花顺 iFinD SDK</Select.Option>
            <Select.Option value="akshare">AKShare</Select.Option>
            <Select.Option value="sina">新浪</Select.Option>
          </Select>
        </Form.Item>
        <Form.Item name="ths_http_refresh_token" label="同花顺 HTTP Refresh Token">
          <Input.Password placeholder="输入 refresh_token" />
        </Form.Item>
        <Form.Item name="ths_http_token" label="同花顺 HTTP Access Token">
          <Input.Password placeholder="输入 access_token（可选）" />
        </Form.Item>
        <Form.Item name="ths_sdk_enabled" label="启用同花顺 iFinD SDK" valuePropName="checked">
          <Switch />
        </Form.Item>
        <Form.Item name="default_adjust" label="默认复权方式">
          <Select>
            <Select.Option value="forward">前复权</Select.Option>
            <Select.Option value="backward">后复权</Select.Option>
            <Select.Option value="none">不复权</Select.Option>
          </Select>
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>
            保存配置
          </Button>
        </Form.Item>
      </Form>
    </Card>
  )
}
