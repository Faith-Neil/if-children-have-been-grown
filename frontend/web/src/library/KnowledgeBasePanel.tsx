// 为什么有这个文件：在资料库页显示公司知识库（RAGFlow）同步概况，并提供立即同步与刷新解析状态。
// 它解决什么问题：资料确认后是否真的进入知识库、哪些失败及原因，此前界面上完全看不到。

import React, { useEffect, useState } from 'react';
import { Alert, Button, Card, Progress, Space, Table, Tag, Typography } from 'antd';
import { CloudSyncOutlined, ReloadOutlined } from '@ant-design/icons';
import { request } from '../shared/api.ts';
import {
  attentionItems,
  kbStatusMeta,
  summarizeKnowledgeBase,
  type KnowledgeBaseItem,
  type KnowledgeBaseStatus,
  type KnowledgeBaseSyncResult,
} from './knowledge-base-core.ts';

export interface KnowledgeBasePanelProps {
  token: string | null;
  canSync: boolean;
  /** 资料库版本变化时重新读取（资料保存后后台会自动同步）。 */
  libraryRevision?: number;
  report?: (error: unknown) => void;
  /** 状态读取后回调，资料表格据此显示每条资料是否已入库。 */
  onStatus?: (status: KnowledgeBaseStatus) => void;
}

export function KnowledgeBasePanel({ token, canSync, libraryRevision = 0, report, onStatus }: KnowledgeBasePanelProps) {
  const [status, setStatus] = useState<KnowledgeBaseStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');

  async function load(refresh = false) {
    if (!token) return;
    try {
      const next = await request<KnowledgeBaseStatus>(`/api/v1/knowledge-base/status${refresh ? '?refresh=true' : ''}`, token);
      setStatus(next);
      onStatus?.(next);
    } catch (error) {
      report?.(error);
    }
  }

  async function syncNow() {
    if (!token || !canSync) return;
    setBusy(true);
    try {
      const result = await request<KnowledgeBaseSyncResult>('/api/v1/knowledge-base/sync', token, 'POST', {});
      setNotice(result.enabled
        ? `本次上传 ${result.uploaded} 条、删除旧文档 ${result.deleted} 篇、失败 ${result.failed} 条。${result.message}`
        : result.message);
      await load();
    } catch (error) {
      report?.(error);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => { void load(); }, [token, libraryRevision]);
  // 有资料在解析中时每 10 秒刷新一次，直到全部完成或失败。
  const parsing = (status?.counts?.parsing ?? 0) > 0;
  useEffect(() => {
    if (!parsing) return undefined;
    const timer = setInterval(() => { void load(true); }, 10000);
    return () => clearInterval(timer);
  }, [parsing, token]);

  if (!status) return null;
  const summary = summarizeKnowledgeBase(status);
  const pending = attentionItems(status);

  return (
    <Card size="small" title="公司知识库（RAGFlow）" data-testid="knowledge-base-panel" style={{ marginBottom: 16 }}
      extra={(
        <Space>
          <Button size="small" icon={<ReloadOutlined />} onClick={() => void load(true)} disabled={!status.enabled || busy}
            data-testid="kb-refresh">刷新解析状态</Button>
          <Button size="small" type="primary" icon={<CloudSyncOutlined />} onClick={() => void syncNow()}
            loading={busy} disabled={!status.enabled || !canSync} data-testid="kb-sync">立即同步</Button>
        </Space>
      )}>
      {!status.enabled ? (
        <Alert type="warning" showIcon message="尚未配置知识库"
          description="未配置或未启用 RAGFlow（含 API Key）。资料仍可正常管理与挂接，但写作时不会检索公司知识库。请公司管理员在“知识库配置”中填写。" />
      ) : (
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space size="large" wrap>
            <Progress type="circle" size={56} percent={summary.coverage} data-testid="kb-coverage" />
            <Typography.Text>应入库 {summary.total} 条：已入库 {summary.synced}，解析中 {summary.parsing}，待同步 {summary.pending}，失败 {summary.failed}</Typography.Text>
            <Typography.Text type="secondary">只有已确认、未过期的资料与已发布片段会进入知识库；检索命中只是候选，挂接到响应矩阵后才是 [证]。</Typography.Text>
          </Space>
          {status.last_error && <Alert type="error" showIcon message={status.last_error} />}
          {notice && <Alert type="info" showIcon closable message={notice} onClose={() => setNotice('')} />}
          {pending.length > 0 && (
            <Table<KnowledgeBaseItem>
              size="small" rowKey="key" pagination={{ pageSize: 5 }} dataSource={pending} data-testid="kb-attention"
              columns={[
                { title: '名称', dataIndex: 'name', ellipsis: true },
                { title: '来源', dataIndex: 'source_type', width: 90, render: value => (value === 'snippet' ? '方案片段' : '资料') },
                { title: '版本', dataIndex: 'revision', width: 70 },
                { title: '状态', dataIndex: 'status', width: 120,
                  render: value => { const meta = kbStatusMeta(value); return <Tag color={meta.color}>{meta.label}</Tag>; } },
                { title: '说明', dataIndex: 'message', ellipsis: true },
              ]}
            />
          )}
        </Space>
      )}
    </Card>
  );
}

export default KnowledgeBasePanel;
