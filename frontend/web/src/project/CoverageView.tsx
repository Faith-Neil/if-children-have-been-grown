// 为什么有这个文件：技术分册覆盖视图（五列），对齐 Requirement→ResponseTask 架构。
// 它解决什么问题：去掉归属分册/证据等两册噪音列；点行跳编辑台对应节。

import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Button, Card, Collapse, Input, Popover, Table, Tag, Tooltip } from 'antd';
import { useProject } from '../app/context.tsx';
import { newIdempotencyKey, streamEvents } from '../shared/api.ts';
import type { CoverageRag, CoverageRow } from '../shared/types.ts';
import { technicalVolumeSessionPath, technicalVolumeStreamPath } from '../editor/section-stream.ts';
import { coverageInstruction, storePrefill } from '../editor/technical-assistant.ts';
import { activeVolumeSession } from '../status/generation-session.ts';
import {
  coverageLabel, coverageState, coverageStats, failureReasonLabel, mergeTaskPatch, parseTaskPatched, patchRows, ragLabel,
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

function RagCell({ rag }: { rag?: CoverageRag | null }) {
  const color = rag?.status === 'hit' ? 'green' : rag?.status === 'failed' ? 'red' : 'default';
  const detail = rag ? (
    <div style={{ maxWidth: 360 }}>
      <div className="muted">检索词：{rag.query || '—'}</div>
      {(rag.top ?? []).map((item, index) => (
        <div key={index}>{item.dataset_kind === 'material' ? '资料库' : item.dataset_kind === 'history' ? '历史标书' : '本标'} · {item.name || '未命名'}</div>
      ))}
      {rag.searched_at && <div className="muted">{rag.searched_at}</div>}
    </div>
  ) : null;
  const tag = <Tag color={color}>{ragLabel(rag)}</Tag>;
  return detail ? <Popover content={detail} title="知识库检索">{tag}</Popover> : tag;
}

export function CoverageView() {
  const { workspace, navigate, token, mutate, reload, report, busy } = useProject();
  const [running, setRunning] = useState('');
  const chapterId = workspace.technical_outline?.chapter_id;
  const canWrite = workspace.chapters.find(item => item.id === chapterId)?.permissions?.generate === true;
  const rejections = workspace.tender_digest?.rejection ?? [];

  async function retry(row: CoverageRow) {
    if (!row.outline_title) return;
    setRunning(row.task_id);
    try {
      await streamEvents(technicalVolumeStreamPath(workspace.project.id), token, { section: row.task_id || row.outline_title }, () => undefined,
        undefined, { 'If-Match': String(workspace.revision), 'Idempotency-Key': newIdempotencyKey() });
      await reload();
    } catch (error) {
      report(error);
    } finally {
      setRunning('');
    }
  }

  async function confirm(row: CoverageRow) {
    try {
      await mutate(`/api/v1/projects/${workspace.project.id}/technical-tasks/${encodeURIComponent(row.task_id)}/confirm`, 'POST', {});
    } catch (error) {
      report(error);
    }
  }

  async function dismissWarnings(row: CoverageRow) {
    try {
      await mutate(
        `/api/v1/projects/${workspace.project.id}/technical-tasks/${encodeURIComponent(row.task_id)}/verify-warnings/dismiss`,
        'POST', { warnings: row.verify_warnings ?? [] },
      );
    } catch (error) {
      report(error);
    }
  }

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
  const stats = coverageStats(rows);

  return (
    <div data-testid="coverage-view">
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 8 }}>
        <Card size="small"><span className="muted">已响应 </span><strong data-testid="coverage-stat-responded">{stats.responded}</strong></Card>
        <Card size="small"><span className="muted">生成中 </span><strong data-testid="coverage-stat-generating">{stats.generating}</strong></Card>
        <Card size="small"><span className="muted">失败 </span><strong data-testid="coverage-stat-failed">{stats.failed}</strong></Card>
        <Card size="small"><span className="muted">待人工确认 </span><strong data-testid="coverage-stat-confirm">{stats.confirm}</strong></Card>
      </div>
      {honesty.degraded && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 8 }}
          data-testid="parse-honesty-warning"
          message="解析结果不完整"
          description={honesty.text}
          action={<Button size="small" onClick={() => navigate('parse')}>回到解析核对</Button>}
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
          action={<Button size="small" onClick={() => navigate('editor')}>去目录挂载</Button>}
        />
      )}
      {rejections.length > 0 && (
        <Collapse
          size="small"
          style={{ marginBottom: 8 }}
          data-testid="coverage-rejections"
          items={[{
            key: 'rejection',
            label: `废标清单（${rejections.length}，正文硬约束）`,
            children: rejections.map(item => (
              <div key={item.id}>
                <Tag color="red">{item.id}</Tag>{item.text}
                {item.category && <Tag>{item.category}</Tag>}
                {item.page != null && <span className="muted"> p.{item.page}</span>}
              </div>
            )),
          }]}
        />
      )}
      <Card size="small" styles={{ body: { padding: 0 } }}>
        <div style={{ padding: 8 }}>
          <Input
            allowClear
            placeholder="搜索要求 / 章节"
            value={search}
            onChange={event => setSearch(event.target.value)}
            style={{ width: 'min(320px, 100%)' }}
            data-testid="coverage-search"
          />
        </div>
        <Table
          rowKey={row => `${row.task_id}-${row.requirement_id}`}
          size="small"
          pagination={{ pageSize: 12, size: 'small' }}
          scroll={{ x: 1080 }}
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
              width: 320,
              ellipsis: true,
              render: (value: string, row) => (
                <>
                  <Tooltip title={value} placement="topLeft"><div className="coverage-cell-text">{value}</div></Tooltip>
                  {row.kind === 'scoring' && row.score_item && (
                    <Tag color="blue">{row.score_item}{row.score != null ? ` ${row.score}分` : ''}</Tag>
                  )}
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
                <Button type="link" size="small" onClick={event => {
                  event.stopPropagation();
                  if (row.outline_title) storePrefill(workspace.project.id, { section: row.task_id || row.outline_title, instruction: coverageInstruction(row) });
                  navigate('editor');
                }}>
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
                  {row.response_status === 'confirmed' && <Tag color="green">已人工确认</Tag>}
                  {row.failure_reason && <div className="muted coverage-failure-reason">{failureReasonLabel(row.failure_reason)}</div>}
                  {canWrite && coverageState(row) === 'failed' && (
                    <Button size="small" type="link" loading={running === row.task_id} disabled={busy || !!running}
                      data-testid={`coverage-retry-${row.requirement_id}`}
                      onClick={event => { event.stopPropagation(); void retry(row); }}>重试本节</Button>
                  )}
                </span>
              ),
            },
            {
              title: '知识库检索',
              width: 150,
              render: (_, row) => <span data-testid={`coverage-rag-${row.requirement_id}`}><RagCell rag={row.rag} /></span>,
            },
            {
              title: '人工确认',
              width: 170,
              render: (_, row) => (row.confirm_reasons ?? []).length ? (
                <span data-testid={`coverage-confirm-${row.requirement_id}`}>
                  {(row.confirm_reasons ?? []).map(reason => <Tag key={reason} color="gold">{reason}</Tag>)}
                  {canWrite && (row.verify_warnings ?? []).length > 0 && (
                    <Popover
                      title="核验警示明细"
                      content={(
                        <div style={{ maxWidth: 420 }}>
                          {(row.verify_warnings ?? []).map(w => <div key={w} style={{ marginBottom: 6 }}>{w}</div>)
                          }
                          <Button size="small" type="primary" disabled={busy}
                            data-testid={`coverage-dismiss-${row.requirement_id}`}
                            onClick={event => { event.stopPropagation(); void dismissWarnings(row); }}>已核无误，消除警示</Button>
                        </div>
                      )}
                    >
                      <Button size="small" type="link" disabled={busy}
                        data-testid={`coverage-warnings-${row.requirement_id}`}
                        onClick={event => event.stopPropagation()}>消警</Button>
                    </Popover>
                  )}
                  {canWrite && coverageState(row) === 'responded' && (
                    <Button size="small" type="link" disabled={busy}
                      onClick={event => { event.stopPropagation(); void confirm(row); }}>确认</Button>
                  )}
                </span>
              ) : null,
            },
          ]}
        />
      </Card>
    </div>
  );
}
