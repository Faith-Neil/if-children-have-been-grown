// 平台管理员维护全局账号安全策略（ISSUE-056）。
// 保存只提交相对服务端快照真正改动的字段（ISSUE-059）：后端 PATCH 为合并语义，
// 未编辑字段不上行，不用前端默认值或旧快照覆盖服务端已保存的其他策略项。
import React, { useEffect, useState } from 'react';
import { App, Alert, Button, Card, Form, InputNumber, Space } from 'antd';
import { ReloadOutlined, SaveOutlined } from '@ant-design/icons';
import { request, userFacingMessage } from '../shared/api.ts';
import { SECURITY_SETTINGS_KEYS, canSaveSecuritySettings, changedSecurityFields, type SecuritySettingsValues } from './platform-security-core.ts';

const defaults: SecuritySettingsValues = { password_min_length: 8, password_min_char_classes: 3, max_login_attempts: 5, session_timeout_minutes: 120 };

export function PlatformSecurityPage({ token }: { token?: string | null }) {
  const { message } = App.useApp();
  // baseline 是最近一次成功读回/保存的服务端快照；未成功加载前为 null，此时禁止保存。
  const [baseline, setBaseline] = useState<SecuritySettingsValues | null>(null);
  const [draft, setDraft] = useState<SecuritySettingsValues>(defaults);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const load = () => {
    setLoading(true);
    request<SecuritySettingsValues>('/api/v1/platform/security-settings', token ?? null, 'GET')
      .then(data => {
        setBaseline(data);
        // 刷新不静默丢弃未保存编辑：用户改动过的字段保留用户值，其余采用服务端新值。
        setDraft(prev => {
          if (!baseline) return data;
          const merged = { ...data };
          for (const key of SECURITY_SETTINGS_KEYS) {
            if (prev[key] !== baseline[key]) merged[key] = prev[key];
          }
          return merged;
        });
        setError('');
      })
      .catch(err => setError(userFacingMessage(err)))
      .finally(() => setLoading(false));
  };
  useEffect(load, [token]);
  const set = (key: keyof SecuritySettingsValues, value: number) => setDraft(prev => ({ ...prev, [key]: value }));
  const saveable = canSaveSecuritySettings({ baseline, draft, loading, saving });
  const save = async () => {
    if (!baseline || !saveable) return;
    setSaving(true);
    try {
      // 合并语义 PATCH：只上行实际改动字段；服务端未建模字段与其他策略项保持原值。
      const saved = await request<SecuritySettingsValues>('/api/v1/platform/security-settings', token ?? null, 'PATCH', changedSecurityFields(baseline, draft));
      setBaseline(saved); setDraft(saved); message.success('平台安全策略已保存');
    } catch (err) { message.error(userFacingMessage(err)); } finally { setSaving(false); }
  };
  const inputsDisabled = !baseline || loading;
  return <Card title="平台安全策略" loading={loading && !baseline} extra={<Space><Button icon={<ReloadOutlined />} onClick={load}>刷新</Button><Button type="primary" icon={<SaveOutlined />} loading={saving} disabled={!saveable} onClick={save} data-testid="security-settings-save">保存</Button></Space>}>
    {error && <Alert type="error" showIcon message={baseline ? error : `${error}；未读回服务端快照前不能保存。`} style={{ marginBottom: 16 }} data-testid="security-settings-error" />}
    <Form layout="vertical" style={{ maxWidth: 560 }}>
      <Form.Item label="密码最少位数"><InputNumber min={8} max={32} value={draft.password_min_length} disabled={inputsDisabled} onChange={v => set('password_min_length', v ?? 8)} /></Form.Item>
      <Form.Item label="密码至少包含字符类别"><InputNumber min={3} max={4} value={draft.password_min_char_classes} disabled={inputsDisabled} onChange={v => set('password_min_char_classes', v ?? 3)} /></Form.Item>
      <Form.Item label="连续登录失败锁定次数"><InputNumber min={1} max={5} value={draft.max_login_attempts} disabled={inputsDisabled} onChange={v => set('max_login_attempts', v ?? 5)} /></Form.Item>
      <Form.Item label="会话有效期（分钟）"><InputNumber min={30} max={480} value={draft.session_timeout_minutes} disabled={inputsDisabled} onChange={v => set('session_timeout_minutes', v ?? 120)} /></Form.Item>
    </Form>
  </Card>;
}
