// 为什么有这个文件：项目设置里的“导出设置”——内部稿命名模板与递交版命名规则（PRD v1.8 §5.1.4 第 9 项；APP-M2-T086）。
// 它解决什么问题：项目负责人按招标文件要求填写递交版文件名规则（不能含编写人），页面即时预览文件名，保存后导出按此命名。

import { useEffect, useState } from 'react';
import { Alert, App as AntApp, Button, Form, Input, Space, Tag } from 'antd';
import { request, userFacingMessage } from '../shared/api';
import { exportSettingsPath, namingProblems, previewName, type ExportSettings } from './export-naming-core';

type Props = { projectId: string; projectName: string; tenderNumber?: string; token: string | null; canEdit: boolean; revision: number; onSaved: () => unknown };

export function ExportNamingCard({ projectId, projectName, tenderNumber, token, canEdit, revision, onSaved }: Props) {
  const { message } = AntApp.useApp();
  const [current, setCurrent] = useState<ExportSettings | null>(null);
  const [internal, setInternal] = useState('');
  const [submit, setSubmit] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    request<ExportSettings>(exportSettingsPath(projectId), token)
      .then(value => { setCurrent(value); setInternal(value.internal_template); setSubmit(value.submit_rule); })
      .catch(error => message.error(userFacingMessage(error)));
  }, [projectId, token]);  // eslint-disable-line react-hooks/exhaustive-deps

  if (!current) return null;
  const sample = { 编写人: '张三', 版本: 'V1.0', 日期: '20260115', 项目名称: projectName, 分册名称: '技术分册', 招标编号: tenderNumber || 'ZB-2026-001' };
  const internalIssues = namingProblems(internal, 'internal', current.variables);
  const submitIssues = namingProblems(submit, 'submission', current.variables);

  async function save() {
    setSaving(true);
    try {
      const value = await request<ExportSettings>(exportSettingsPath(projectId), token, 'PUT', { internal_template: internal, submit_rule: submit }, revision);
      setCurrent(value);
      message.success('导出命名已保存，之后的导出按新规则命名。');
      await onSaved();
    } catch (error) { message.error(userFacingMessage(error)); } finally { setSaving(false); }
  }

  return (
    <Form layout="vertical" data-testid="export-naming-card">
      <Form.Item label="内部稿命名模板" validateStatus={internalIssues.length ? 'error' : ''} help={internalIssues.join('；') || `示例：${previewName(internal, sample)}`}>
        <Input value={internal} disabled={!canEdit} onChange={event => setInternal(event.target.value)} data-testid="export-naming-internal" />
      </Form.Item>
      <Form.Item label="递交版命名规则" validateStatus={submitIssues.length ? 'error' : ''}
        help={submitIssues.join('；') || `示例：${previewName(submit, sample)}（按招标文件对电子文件命名的要求填写）`}>
        <Input value={submit} disabled={!canEdit} onChange={event => setSubmit(event.target.value)} data-testid="export-naming-submit" />
      </Form.Item>
      <Space wrap style={{ marginBottom: 12 }}>
        {current.variables.map(variable => <Tag key={variable.name} title={variable.description}>{`{${variable.name}}`}</Tag>)}
      </Space>
      {submit.includes('{编写人}') && <Alert type="error" showIcon style={{ marginBottom: 12 }} message="递交版文件名出现编写人，可能被用来判断不同投标人的文件由同一人编制。" />}
      {canEdit && (
        <Button type="primary" loading={saving} disabled={!!internalIssues.length || !!submitIssues.length} onClick={() => void save()}
          data-testid="export-naming-save">保存导出命名</Button>
      )}
    </Form>
  );
}
