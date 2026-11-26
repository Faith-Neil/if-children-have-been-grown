// 为什么有这个文件：公司管理员维护本公司真实生效的写作辅助与解析阈值（ISSUE-056）。
// 它解决什么问题：删除空壳扩展字段、查重参数与平台安全策略；锁心跳等底层技术参数保留后端默认值，不再暴露给业务管理员误调。

import React, { useEffect, useState } from 'react';
import { App, Alert, Button, Card, Form, InputNumber, Space, Switch, Typography } from 'antd';
import { ReloadOutlined, SaveOutlined } from '@ant-design/icons';
import type { ApplicationSession } from '../shared/types.ts';
import { fetchCompanySettings, updateCompanySettings, type ApiCompanySettings } from './company-settings-api.ts';
import { userFacingMessage } from '../shared/api.ts';
import { WordTemplateCard } from './WordTemplateCard.tsx';

const { Text } = Typography;

export interface CompanySettingsPageProps {
  session?: ApplicationSession | null;
  currentUser?: { company_id?: string; role?: string; primary_role?: string } | null;
  currentRole?: string;
  token?: string | null;
}

type FormState = Pick<ApiCompanySettings,
  'assistant_enabled' | 'assistant_kb_default' | 'assistant_allow_kb_off' |
  'assistant_suggestion_count' | 'assistant_paste_match_ratio' | 'parse_confidence_threshold'>;

const defaults: FormState = {
  assistant_enabled: true,
  assistant_kb_default: true,
  assistant_allow_kb_off: true,
  assistant_suggestion_count: 3,
  assistant_paste_match_ratio: 0.8,
  parse_confidence_threshold: 0.8,
};

export function CompanySettingsPage({ session, currentUser, token }: CompanySettingsPageProps) {
  const { message } = App.useApp();
  const companyId = currentUser?.company_id || session?.user?.company_id || '';
  const [settings, setSettings] = useState<FormState>(defaults);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const load = () => {
    if (!companyId) return;
    setLoading(true);
    fetchCompanySettings(companyId, token ?? null)
      .then(api => {
        setSettings({
          assistant_enabled: api.assistant_enabled,
          assistant_kb_default: api.assistant_kb_default,
          assistant_allow_kb_off: api.assistant_allow_kb_off,
          assistant_suggestion_count: api.assistant_suggestion_count,
          assistant_paste_match_ratio: api.assistant_paste_match_ratio ?? 0.8,
          parse_confidence_threshold: api.parse_confidence_threshold ?? 0.8,
        });
        setError('');
      })
      .catch(err => setError(userFacingMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(load, [companyId, token]);

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => setSettings(prev => ({ ...prev, [key]: value }));
  const save = async () => {
    setSaving(true);
    try {
      await updateCompanySettings(companyId, settings, token ?? null);
      message.success('公司设置已保存');
    } catch (err) {
      message.error(userFacingMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card
      title="公司设置"
      loading={loading}
      extra={<Space><Button icon={<ReloadOutlined />} onClick={load}>刷新</Button><Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={save}>保存</Button></Space>}
    >
      {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} />}
      <Alert type="info" showIcon message="这些设置只影响本公司的写作助手与解析提示。账号安全策略由平台管理员统一维护。" style={{ marginBottom: 20 }} />
      <Form layout="vertical" style={{ maxWidth: 760 }}>
        <Form.Item label="启用划词改写助手">
          <Switch checked={settings.assistant_enabled} onChange={v => set('assistant_enabled', v)} data-testid="switch-assistant-enabled" />
        </Form.Item>
        <Form.Item label="新对话默认参考知识库">
          <Switch checked={settings.assistant_kb_default} onChange={v => set('assistant_kb_default', v)} data-testid="switch-assistant-kb-default" />
        </Form.Item>
        <Form.Item label="允许编写人临时关闭知识库参考">
          <Switch checked={settings.assistant_allow_kb_off} onChange={v => set('assistant_allow_kb_off', v)} data-testid="switch-assistant-allow-kb-off" />
        </Form.Item>
        <Form.Item label="每次给出修改建议条数">
          <InputNumber min={3} max={5} value={settings.assistant_suggestion_count} onChange={v => set('assistant_suggestion_count', v ?? 3)} data-testid="input-assistant-count" />
        </Form.Item>
        <Form.Item label="粘贴内容识别阈值" extra="粘贴内容与助手建议重合达到该比例时，系统将其识别为助手撰写。">
          <InputNumber min={0.5} max={1} step={0.05} value={settings.assistant_paste_match_ratio} onChange={v => set('assistant_paste_match_ratio', v ?? 0.8)} data-testid="input-paste-ratio" />
        </Form.Item>
        <Form.Item label="解析低置信度提醒阈值" extra="低于该比例的解析结果会高亮提醒人工核对。">
          <InputNumber min={0.5} max={0.99} step={0.05} value={settings.parse_confidence_threshold} onChange={v => set('parse_confidence_threshold', v ?? 0.8)} data-testid="input-parse-confidence" />
        </Form.Item>
      </Form>
      <WordTemplateCard companyId={companyId} token={token ?? null} canEdit />
      <Text type="secondary">编辑锁与自动保存参数由系统按安全默认值统一管理。</Text>
    </Card>
  );
}
