// 为什么有这个文件：抽取冲突待选定卡片列表（ConflictCards）。
// 它解决什么问题：各方取值、原文、文件与页码并列显示；可选定一方或标“不构成冲突”，均须写理由；
// “已按补遗处理”的不阻断确认，可核对或撤销；未定位的补遗条目须指定被替代的原条款（PRD v1.8 §5.1.2、§5.2.3）。

import React, { useEffect, useState } from 'react';
import { Button, Card, Col, Empty, Input, Radio, Row, Select, Space, Tag } from 'antd';
import { useProject } from '../app/context.tsx';
import { projectCan } from './project-team.ts';
import { SourceLink } from './SourceLink.tsx';
import { request } from '../shared/api.ts';
import { buildDecision, conflictTone, decisionPath } from './parse-postprocess-core.ts';
import type { ConflictDecisionBody, ConflictList, ConflictValue, Source } from '../shared/types.ts';

export interface ConflictCardsProps {
  onLocate: (source: Source) => void;
}

function valueSource(value: ConflictValue): Source | null {
  return value.file_id ? { file_id: value.file_id, page: value.page ?? 1, quote: value.quote } : null;
}

export function ConflictCards({ onLocate }: ConflictCardsProps) {
  const { workspace, token, busy, mutate } = useProject();
  const [list, setList] = useState<ConflictList | null>(null);
  const [choices, setChoices] = useState<Record<string, string>>({});
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [error, setError] = useState<Record<string, string>>({});
  const lead = projectCan(workspace, 'prepare_sources');

  useEffect(() => {
    let cancelled = false;
    request<ConflictList>(`/api/v1/projects/${workspace.project.id}/parse/conflicts`, token)
      .then(value => { if (!cancelled) setList(value); }).catch(() => { if (!cancelled) setList(null); });
    return () => { cancelled = true; };
  }, [workspace.project.id, workspace.revision, token]);

  async function decide(id: string, action: ConflictDecisionBody['action'], factId?: string, requirementId?: string) {
    const { body, error: problem } = buildDecision(action, reasons[id] ?? '', { factId, requirementId });
    setError({ ...error, [id]: problem ?? '' });
    if (!body) return;
    try { await mutate(decisionPath(workspace.project.id, id), 'POST', body); } catch { /* mutate 已显示后台原因，保留输入 */ }
  }

  if (!list || !list.conflicts.length) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前没有发现取值冲突；仍需人工对照原文" />;
  }
  const current = list.conflicts.filter(item => item.current);
  const history = list.conflicts.filter(item => !item.current);
  const card = (item: ConflictList['conflicts'][number]) => {
    const choice = choices[item.id] ?? item.selected_fact_id ?? item.chosen_requirement_id ?? '';
    const open = item.current && item.status === 'pending';
    return (
      <Card className="conflict-card" key={item.id} data-testid="conflict-card" data-status={item.status} title={`${item.key} · ${item.conflict_type_label}`}
        extra={<Tag color={conflictTone(item)}>{item.status_label}</Tag>}>
        <Radio.Group value={choice} style={{ width: '100%' }} disabled={busy || !lead || !open}
          onChange={e => setChoices({ ...choices, [item.id]: e.target.value })}>
          <Row gutter={12} data-testid="conflict-values">
            {item.values.map(value => {
              const id = value.fact_id ?? value.requirement_id ?? value.value;
              const source = valueSource(value);
              return (
                <Col span={Math.max(24 / Math.max(item.values.length, 1), 8)} key={id}>
                  <div className={`conflict-option ${value.effective_status === 'superseded' ? 'muted' : ''}`}>
                    {item.conflict_type === 'addendum_unlocated' ? <b>{value.value}</b> : <Radio value={id}><b>{value.value}</b></Radio>}
                    <p>{value.filename}{value.page ? ` 第 ${value.page} 页` : ''}{value.effective_status === 'superseded' ? '（已被替代）' : ''}</p>
                    {source && <p><SourceLink source={source} onClick={onLocate} /></p>}
                    <blockquote>{value.quote || '服务承诺引用，无独立招标原文'}</blockquote>
                  </div>
                </Col>
              );
            })}
          </Row>
        </Radio.Group>
        {item.conflict_type === 'addendum_unlocated' && open && (
          <Select style={{ width: '100%', marginBottom: 8 }} placeholder="指定被替代的原条款" value={choices[item.id]} disabled={!lead}
            onChange={value => setChoices({ ...choices, [item.id]: value })} data-testid="conflict-target"
            options={item.candidates.map(value => ({ value: value.requirement_id ?? '', label: value.value }))} />
        )}
        {item.status !== 'pending' && item.reason && <p className="muted">处理理由：{item.reason}{item.decided_by_name ? `（${item.decided_by_name}）` : ''}</p>}
        {item.status === 'by_addendum' && <p className="muted" data-testid="by-addendum-note">已按补遗处理，不阻断确认解析结果；请核对，不同意可撤销。</p>}
        {item.current && lead && (open || item.status === 'by_addendum') && (
          <>
            <Input.TextArea rows={2} aria-label="处理理由" data-testid="conflict-reason" maxLength={2000}
              placeholder="处理理由（必填），例如以正式招标文件为准" value={reasons[item.id] ?? ''}
              onChange={e => setReasons({ ...reasons, [item.id]: e.target.value })} />
            {error[item.id] && <p className="orange" role="alert">{error[item.id]}</p>}
            <Space style={{ marginTop: 12 }} wrap>
              {open && item.conflict_type !== 'addendum_unlocated' && (
                <Button type="primary" disabled={busy || !choice} data-testid="conflict-choose"
                  onClick={() => void decide(item.id, 'choose', item.conflict_type === 'field_value' ? choice : undefined,
                    item.conflict_type === 'field_value' ? undefined : choice)}>选定正确取值</Button>
              )}
              {open && item.conflict_type === 'addendum_unlocated' && (
                <Button type="primary" disabled={busy || !choices[item.id]} data-testid="conflict-assign"
                  onClick={() => void decide(item.id, 'assign_target', undefined, choices[item.id])}>指定原条款</Button>
              )}
              {open && <Button disabled={busy} data-testid="conflict-not-conflict" onClick={() => void decide(item.id, 'not_conflict')}>不构成冲突</Button>}
              {item.status === 'by_addendum' && <Button disabled={busy} data-testid="conflict-confirm" onClick={() => void decide(item.id, 'confirm')}>核对无误</Button>}
              {item.status === 'by_addendum' && <Button danger disabled={busy} data-testid="conflict-revert" onClick={() => void decide(item.id, 'revert')}>撤销补遗替代</Button>}
            </Space>
          </>
        )}
      </Card>
    );
  };
  return (
    <>
      <p className="muted" data-testid="conflict-summary">
        待处理 {list.summary.pending} · 已按补遗处理 {list.summary.by_addendum} · 已选定 {list.summary.resolved} · 不构成冲突 {list.summary.not_conflict}
      </p>
      {current.map(card)}
      {history.length > 0 && <details><summary>历史记录 {history.length} 条</summary>{history.map(card)}</details>}
    </>
  );
}
