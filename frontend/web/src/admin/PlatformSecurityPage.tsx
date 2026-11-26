// 平台管理员维护全局账号安全策略（ISSUE-056）。
import React, { useEffect, useState } from 'react';
import { App, Alert, Button, Card, Form, InputNumber, Space } from 'antd';
import { ReloadOutlined, SaveOutlined } from '@ant-design/icons';
import { request, userFacingMessage } from '../shared/api.ts';

interface SecuritySettings { password_min_length: number; password_min_char_classes: number; max_login_attempts: number; session_timeout_minutes: number }
const defaults: SecuritySettings = { password_min_length: 8, password_min_char_classes: 3, max_login_attempts: 5, session_timeout_minutes: 120 };

export function PlatformSecurityPage({ token }: { token?: string | null }) {
  const { message } = App.useApp();
  const [settings, setSettings] = useState(defaults);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const load = () => {
    setLoading(true);
    request<SecuritySettings>('/api/v1/platform/security-settings', token ?? null, 'GET')
      .then(data => { setSettings(data); setError(''); })
      .catch(err => setError(userFacingMessage(err)))
      .finally(() => setLoading(false));
  };
  useEffect(load, [token]);
  const set = (key: keyof SecuritySettings, value: number) => setSettings(prev => ({ ...prev, [key]: value }));
  const save = async () => {
    setSaving(true);
    try {
      const saved = await request<SecuritySettings>('/api/v1/platform/security-settings', token ?? null, 'PATCH', settings);
      setSettings(saved); message.success('平台安全策略已保存');
    } catch (err) { message.error(userFacingMessage(err)); } finally { setSaving(false); }
  };
  return <Card title="平台安全策略" loading={loading} extra={<Space><Button icon={<ReloadOutlined />} onClick={load}>刷新</Button><Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={save}>保存</Button></Space>}>
    {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} />}
    <Form layout="vertical" style={{ maxWidth: 560 }}>
      <Form.Item label="密码最少位数"><InputNumber min={8} max={32} value={settings.password_min_length} onChange={v => set('password_min_length', v ?? 8)} /></Form.Item>
      <Form.Item label="密码至少包含字符类别"><InputNumber min={3} max={4} value={settings.password_min_char_classes} onChange={v => set('password_min_char_classes', v ?? 3)} /></Form.Item>
      <Form.Item label="连续登录失败锁定次数"><InputNumber min={1} max={5} value={settings.max_login_attempts} onChange={v => set('max_login_attempts', v ?? 5)} /></Form.Item>
      <Form.Item label="会话有效期（分钟）"><InputNumber min={30} max={480} value={settings.session_timeout_minutes} onChange={v => set('session_timeout_minutes', v ?? 120)} /></Form.Item>
    </Form>
  </Card>;
}
