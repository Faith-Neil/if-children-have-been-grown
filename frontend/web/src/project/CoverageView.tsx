// 为什么有这个文件：技术分册覆盖视图（五列），对齐 Requirement→ResponseTask 架构。
// 它解决什么问题：去掉归属分册/证据等两册噪音列；点行跳编辑台对应节。

import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Button, Card, Input, Table, Tag } from 'antd';
import { useProject } from '../app/context.tsx';
import { streamEvents } from '../shared/api.ts';
import type { CoverageRow, TechnicalRagAuditRow } from '../shared/types.ts';
import { technicalVolumeSessionPath } from '../editor/section-stream.ts';
import { activeVolumeSession } from '../status/generation-session.ts';
import { auditSearchLine, auditTopKinds, tenderIndexLine, writerModelLine } from './coverage-audit.ts';
import {
  coverageLabel, coverageState, coverageStats, mergeTaskPatch, parseTaskPatched, patchRows,
  type CoveragePatches,
} from './coverage-live.ts';
import { parseHonesty } from './parse-honesty.ts';

const RISK_LABEL: Record<string, string> = {
  critical: '废标风险',
  high: '高',
  medium: '中',
  low: '低',
};

const ENDED = new Set(['volume.done', 'volume.cancelled', 'volume.failed']);

function stateColor(row: CoverageRow): string {
  const state = coverageState(row);
  if (state === 'failed') return 'error';
  if (state === 'generating') return 'processing';
  if (state === 'pending') return 'default';
  if (row.response_type === 'deviate') return 'orange';
  if (row.response_type === 'exceed') return 'blue';
  return 'success';
}

/** 订阅进行中的技术卷生成会话，按 task.patched 累积行补丁；会话结束后由工作区刷新接手。 */
function useSessionPatches(): CoveragePatches {
  const { workspace, token, reload } = useProject();
  const sessionId = activeVolumeSession(workspace.jobs, workspace.project.id)?.id ?? '';
  const [live, setLive] = useState<{ sessionId: string; patches: CoveragePatches }>({ sessionId: '', patches: {} });
  useEffect(() => {
    if (!sessionId || !token) return;
    const controller = new AbortController();
    let patches: CoveragePatches = {};
    setLive({ sessionId, patches });
    void streamEvents(technicalVolumeSessionPath(sessionId), token, undefined, raw => {
      const patch = parseTaskPatched(raw);
      if (patch) {
        const next = mergeTaskPatch(patches, patch);
        if (next !== patches) {
          patches = next;
          setLive({ sessionId, patches });
        }
        return;
      }
      const name = (raw as { event?: unknown }).event;
      if (typeof name !== 'string' || !ENDED.has(name)) return;
      if (name !== 'volume.done') setLive({ sessionId, patches: {} });
      void reload().catch(() => undefined);
    }, controller.signal).catch(() => undefined);
    return () => controller.abort();
  }, [sessionId, token]);
  return live.sessionId === sessionId ? live.patches : {};
}

export function CoverageView() {
  const { workspace, navigate } = useProject();
  const [search, setSearch] = useState('');
  const patches = useSessionPatches();
  const allRows = useMemo(
    () => patchRows((workspace.coverage_rows ?? []) as CoverageRow[], patches),
    [workspace.coverage_rows, patches],
  );
  const rows = useMemo(() => {
    const q = search.trim();
    if (!q) return allRows;
    return allRows.filter(row =>
      row.text.includes(q)
      || (row.outline_title || '').includes(q)
      || (row.outline_number || '').includes(q),
    );
  }, [allRows, search]);

  const validation = workspace.plan_validation;
  const honesty = parseHonesty(workspace);
  const audits = (workspace.technical_rag_audit ?? []) as TechnicalRagAuditRow[];
  const indexLine = tenderIndexLine(workspace.tender_index);
  const modelLine = writerModelLine(workspace.writer_model);
  const stats = coverageStats(rows);

  return (
    <div data-testid="coverage-view">
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 8 }}>
        <Card size="small"><span className="muted">要求 </span><strong>{stats.total}</strong></Card>
        <Card size="small"><span className="muted">废标相关 </span><strong>{stats.rejection}</strong></Card>
        <Card size="small"><span className="muted">已响应 </span><strong data-testid="coverage-stat-responded">{stats.responded}</strong></Card>
        <Card size="small"><span className="muted">生成中 </span><strong data-testid="coverage-stat-generating">{stats.generating}</strong></Card>
        <Card size="small"><span className="muted">失败 </span><strong data-testid="coverage-stat-failed">{stats.failed}</strong></Card>
      </div>
      <Alert
        type="info"
        showIcon
        className="page-notice"
        data-testid="coverage-view-notice"
        style={{ marginBottom: 8 }}
        message="覆盖视图（可选）"
        description="招标要求 → 响应任务 → 目标章节。不挡「开始生成」与导出。"
        action={<Button size="small" type="link" onClick={() => navigate('editor')}>回编辑台</Button>}
      />
      {honesty.degraded && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 8 }}
          data-testid="parse-honesty-warning"
          message="解析结果不完整"
          description={honesty.text}
        />
      )}
      {validation && validation.passed === false && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 8 }}
          data-testid="plan-validation-warning"
          message="生成计划校验未全部通过"
          description={(validation.issues || []).join('；')}
        />
      )}
      {(indexLine || modelLine) && (
        <div data-testid="coverage-retrieval-meta" className="muted" style={{ marginBottom: 8 }}>
          {[indexLine, modelLine].filter(Boolean).join(' ｜ ')}
        </div>
      )}
      {audits.length > 0 && (
        <Card size="small" styles={{ body: { padding: 0 } }} style={{ marginBottom: 8 }} data-testid="coverage-rag-audit">
          <Table
            rowKey={(row, index) => `${row.section || 's'}-${row.query || 'q'}-${index}`}
            size="small"
            pagination={false}
            dataSource={audits}
            columns={[
              {
                title: '节',
                dataIndex: 'section',
                width: 160,
                render: (value: string) => value || '—',
              },
              {
                title: '查询',
                dataIndex: 'query',
                render: (value: string) => value || '—',
              },
              {
                title: '命中',
                width: 220,
                render: (_, row) => auditSearchLine(row),
              },
              {
                title: '库别',
                width: 120,
                render: (_, row) => auditTopKinds(row) || '—',
              },
            ]}
          />
        </Card>
      )}
      <Card size="small" styles={{ body: { padding: 0 } }}>
        <div style={{ padding: 8 }}>
          <Input
            allowClear
            placeholder="搜索要求 / 章节"
            value={search}
            onChange={event => setSearch(event.target.value)}
            style={{ width: 280 }}
            data-testid="coverage-search"
          />
        </div>
        <Table
          rowKey={row => `${row.task_id}-${row.requirement_id}`}
          size="small"
          pagination={{ pageSize: 12, size: 'small' }}
          dataSource={rows}
          onRow={row => ({
            style: { cursor: 'pointer' },
            onClick: () => navigate('editor'),
            'data-testid': `coverage-row-${row.requirement_id}`,
          })}
          columns={[
            {
              title: '招标要求',
              dataIndex: 'text',
              width: 360,
              render: (value: string, row) => (
                <>
                  <div>{value}</div>
                  {row.is_rejection_criterion && <Tag color="red">废标相关</Tag>}
                </>
              ),
            },
            {
              title: '风险',
              dataIndex: 'risk_level',
              width: 100,
              render: (value: string) => (
                <Tag color={value === 'critical' ? 'red' : value === 'high' ? 'orange' : 'default'}>
                  {RISK_LABEL[value] || value}
                </Tag>
              ),
            },
            {
              title: '原文出处',
              width: 140,
              render: (_, row) => (
                <span className="muted">
                  {row.source_filename || '招标文件'}
                  {row.source_page != null ? ` · p.${row.source_page}` : ''}
                </span>
              ),
            },
            {
              title: '目标章节',
              width: 180,
              render: (_, row) => (
                <Button type="link" size="small" onClick={event => { event.stopPropagation(); navigate('editor'); }}>
                  {[row.outline_number, row.outline_title].filter(Boolean).join(' ') || '未挂目录'}
                </Button>
              ),
            },
            {
              title: '响应状态',
              width: 150,
              render: (_, row) => (
                <span data-testid={`coverage-state-${row.requirement_id}`}>
                  <Tag color={stateColor(row)}>{coverageLabel(row)}</Tag>
                  {row.response_status === 'needs_confirm' && <Tag color="gold">待确认</Tag>}
                </span>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
}
