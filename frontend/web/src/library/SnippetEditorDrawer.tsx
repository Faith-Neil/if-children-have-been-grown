// 为什么有这个文件：方案片段的新建、草稿保存与发布界面。
// 它解决什么问题：此前片段只能通过接口创建，页面只能看不能写；发布被拦截（未声明变量、写死承诺数字、
// 报告无来源组等）时，原因也不能在页面上看到。发布成功后后台自动同步到公司知识库。

import React, { useEffect, useRef, useState } from 'react';
import { Alert, Button, Drawer, Form, Input, List, Select, Space, Tag, Typography } from 'antd';
import { request } from '../shared/api.ts';
import type { SnippetPublication } from '../shared/types.ts';
import { SNIPPET_TYPE_MAP, extractSnippetVariables } from './snippet-library-core.ts';

const TYPE_OPTIONS = Object.entries(SNIPPET_TYPE_MAP).filter(([k]) => k !== 'all').map(([value, label]) => ({ value, label }));
const BASE = '/api/v1/snippet-publications';

export interface SnippetEditorDrawerProps {
  open: boolean;
  token: string | null;
  snippet: SnippetPublication | null; // null = 新建
  canWrite: boolean;
  onClose: () => void;
  onSaved: (item: SnippetPublication) => void;
}

export function SnippetEditorDrawer({ open, token, snippet, canWrite, onClose, onSaved }: SnippetEditorDrawerProps) {
  const [form] = Form.useForm();
  const [current, setCurrent] = useState<SnippetPublication | null>(snippet);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [reasons, setReasons] = useState<{ code: string; message: string }[]>([]);
  const [published, setPublished] = useState(false);

  // 只在打开或换成另一条片段时重置；保存/发布后父组件回传同一条片段，不能清掉拦截原因和提示。
  const loadedId = useRef<string | null | undefined>(undefined);
  useEffect(() => {
    if (!open) { loadedId.current = undefined; return; }
    const id = snippet?.id ?? null;
    if (loadedId.current === id) return;
    loadedId.current = id;
    setCurrent(snippet); setError(''); setReasons([]); setPublished(false);
    form.setFieldsValue(snippet
      ? { product: snippet.product, snippet_type: snippet.snippet_type, variables: snippet.variables ?? [],
          source_group: snippet.source_group ?? '', boilerplate_group: snippet.boilerplate_group ?? '', draft_body: snippet.draft_body ?? '' }
      : { product: '', snippet_type: 'solution', variables: [], source_group: '', boilerplate_group: '', draft_body: '' });
  }, [snippet?.id, open]);

  async function save(): Promise<SnippetPublication | null> {
    setError('');
    const values = await form.validateFields();
    setBusy(true);
    try {
      const body = { ...values, variables: values.variables ?? [] };
      const saved = current
        ? await request<SnippetPublication>(`${BASE}/${encodeURIComponent(current.id)}`, token, 'PUT', body, current.draft_revision ?? 1)
        : await request<SnippetPublication>(BASE, token, 'POST', body);
      setCurrent(saved);
      onSaved(saved);
      return saved;
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存失败');
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function publish() {
    const saved = await save();
    if (!saved) return;
    setBusy(true);
    try {
      const result = await request<{ item: SnippetPublication; blocked: boolean; reasons: { code: string; message: string }[] }>(
        `${BASE}/${encodeURIComponent(saved.id)}/publish`, token, 'POST', {}, saved.draft_revision ?? 1);
      setCurrent(result.item);
      onSaved(result.item);
      setReasons(result.reasons);
      setPublished(!result.blocked);
    } catch (e) {
      setError(e instanceof Error ? e.message : '发布失败');
    } finally {
      setBusy(false);
    }
  }

  const body: string = Form.useWatch('draft_body', form) ?? '';
  const declared: string[] = Form.useWatch('variables', form) ?? [];
  const used = extractSnippetVariables(body);
  const undeclared = used.filter(v => !declared.includes(v));

  return (
    <Drawer open={open} width={720} title={current ? `编辑方案片段（草稿 v${current.draft_revision ?? 1}）` : '新建方案片段'} onClose={onClose}
      extra={canWrite && <Space>
        <Button onClick={() => void save()} loading={busy}>保存草稿</Button>
        <Button type="primary" onClick={() => void publish()} loading={busy} data-testid="snippet-publish-button">发布</Button>
      </Space>}>
      {!canWrite && <Alert type="info" showIcon message="当前账号只能查看片段。" style={{ marginBottom: 12 }} />}
      {error && <Alert type="error" showIcon closable message={error} onClose={() => setError('')} style={{ marginBottom: 12 }} />}
      {published && <Alert type="success" showIcon message="已发布。系统正在把它同步到公司知识库，写作时即可检索。" style={{ marginBottom: 12 }} />}
      {reasons.length > 0 && (
        <Alert type="warning" showIcon style={{ marginBottom: 12 }} message="发布被拦截，请修改后再发布"
          description={<List size="small" dataSource={reasons} renderItem={r => <List.Item>{r.message}</List.Item>} />} data-testid="snippet-block-reasons" />
      )}
      <Form form={form} layout="vertical" disabled={!canWrite || busy}>
        <Space style={{ width: '100%' }} size="large" align="start">
          <Form.Item name="product" label="产品 / 方案名称" rules={[{ required: true, whitespace: true, message: '请填写产品或方案名称' }]} style={{ width: 320 }}>
            <Input placeholder="例如：数据中心运维服务" />
          </Form.Item>
          <Form.Item name="snippet_type" label="分类" rules={[{ required: true }]} style={{ width: 200 }}>
            <Select options={TYPE_OPTIONS} />
          </Form.Item>
        </Space>
        <Space style={{ width: '100%' }} size="large" align="start">
          <Form.Item name="boilerplate_group" label="套话组 / 小标题" style={{ width: 320 }}><Input placeholder="例如：日常巡检方案" /></Form.Item>
          <Form.Item name="source_group" label="来源组" tooltip="正文提到检测报告、测评报告等时必须填写来源，否则不能发布。" style={{ width: 320 }}>
            <Input placeholder="例如：2025 年等保测评报告" />
          </Form.Item>
        </Space>
        <Form.Item name="variables" label="声明的变量" tooltip="正文里的 {{变量名}} 必须在这里声明；承诺类数字请写成变量，不要写死。">
          <Select mode="tags" tokenSeparators={[',', '，', ' ']} placeholder="输入变量名后回车，例如 response_minutes" />
        </Form.Item>
        {undeclared.length > 0 && (
          <Alert type="warning" showIcon style={{ marginBottom: 12 }} message={<>正文使用了未声明的变量：{undeclared.map(v => <Tag key={v}>{v}</Tag>)}</>}
            action={canWrite && <Button size="small" onClick={() => form.setFieldValue('variables', [...declared, ...undeclared])}>全部声明</Button>} />
        )}
        <Form.Item name="draft_body" label="片段正文" rules={[{ required: true, whitespace: true, message: '请填写正文' }]}>
          <Input.TextArea rows={14} placeholder="可用 {{变量名}} 引用项目事实，例如：一级故障 {{response_minutes}} 分钟内响应。" />
        </Form.Item>
        <Typography.Text type="secondary">
          保存只更新草稿，不影响已发布内容；发布前系统会检查变量声明、写死的承诺数字、报告来源与跨公司引用。
        </Typography.Text>
      </Form>
    </Drawer>
  );
}

export default SnippetEditorDrawer;
