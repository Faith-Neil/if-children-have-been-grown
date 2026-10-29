// 为什么有这个文件：编辑台右侧“对话助手”中的选区改写（PRD v1.8 §5.11.2、§5.11.5、§5.11.6；APP-M2-T178/T180/T185/T187）。
// 它解决什么问题：选中一段文字后，请助手给出 3～5 种写法；每条样例显示写法、预检提示与字数，可“替换选中内容”或“插在选中内容后”；
// 写入前弹出差异视图（删除标红、增加标绿、【待补】个数），确认后由后端核对编辑锁与选区再写入新版本，并显示改动段落的复查结果。

import React, { useEffect, useState } from 'react';
import { Alert, Button, Card, Empty, Input, Modal, Select, Space, Spin, Tag, Tooltip } from 'antd';
import { EditOutlined } from '@ant-design/icons';
import { ApiError, request } from '../shared/api.ts';
import type { Chapter } from '../shared/types.ts';
import {
  ACTION_LABEL, REWRITE_MODES, diffText, pendingCount, previewWrite, relocation, rewritePath, selectionProblem, locateSelection,
  type ApplyResult, type RewriteAction, type RewriteBatch, type RewriteMode, type RewriteSample,
} from './selection-rewrite-core.ts';

export type RewriteSelection = { text: string; start?: number; end?: number };

export interface SelectionRewritePanelProps {
  projectId: string;
  chapter: Chapter | null;
  content: string;
  selection: RewriteSelection | null;
  leaseToken: string | null;
  canGenerate: boolean;
  busy: boolean;
  token: string;
  onApplied: (result: ApplyResult) => Promise<void>;
  onClear: () => void;
  report: (error: unknown) => void;
}

type Pending = { sample: RewriteSample; action: RewriteAction; confirmStart?: number; moved?: boolean };

export function SelectionRewritePanel({ projectId, chapter, content, selection, leaseToken, canGenerate, busy, token, onApplied, onClear, report }: SelectionRewritePanelProps) {
  const [mode, setMode] = useState<RewriteMode>('rewrite');
  const [instruction, setInstruction] = useState('');
  const [count, setCount] = useState(3);
  const [batch, setBatch] = useState<RewriteBatch | null>(null);
  const [working, setWorking] = useState(false);
  const [pending, setPending] = useState<Pending | null>(null);
  const [result, setResult] = useState<ApplyResult | null>(null);
  const [invalid, setInvalid] = useState('');

  // 换了选区才清空上一组样例；写入后选区被清除时保留结果与复查提示
  useEffect(() => { if (selection) { setBatch(null); setResult(null); setInvalid(''); } }, [selection?.text, selection?.start]);
  useEffect(() => { setBatch(null); setResult(null); setInvalid(''); }, [chapter?.id]);

  if (!chapter) return null;
  const committed = chapter.content ?? '';
  const problem = selection ? selectionProblem(committed, content, selection.text, selection.start, selection.end) : null;
  const located = selection ? locateSelection(committed, selection.text, selection.start, selection.end) : null;

  async function generate() {
    if (!located || !chapter) return;
    setWorking(true); setResult(null); setInvalid('');
    try {
      const value = await request<RewriteBatch>(rewritePath(projectId, chapter.id), token, 'POST', {
        base_revision: chapter.revision, start: located.start, end: located.end, selected_text: located.text,
        mode, instruction: mode === 'instruction' ? instruction.trim() : '', count,
      });
      setBatch(value);
    } catch (error) { report(error); } finally { setWorking(false); }
  }

  async function confirm() {
    if (!pending || !batch || !chapter || !leaseToken) return;
    setWorking(true);
    try {
      const value = await request<ApplyResult>(rewritePath(projectId, chapter.id, batch.id), token, 'POST', {
        lease_token: leaseToken, sample_id: pending.sample.id, action: pending.action,
        ...(pending.confirmStart !== undefined ? { confirm_start: pending.confirmStart } : {}),
      });
      setPending(null); setBatch(value.batch); setResult(value);
      await onApplied(value);
    } catch (error) {
      const moved = relocation(error);
      if (moved?.relocated) { setPending({ ...pending, confirmStart: moved.start, moved: true }); return; }
      if (moved && !moved.relocated) {
        setPending(null); setBatch(current => current && { ...current, status: 'invalidated', samples: current.samples.map(s => ({ ...s, status: 'invalidated' })) });
        setInvalid(error instanceof ApiError ? error.message : '原文已被改动，样例已失效，请重新选择后再问。');
        return;
      }
      report(error);
    } finally { setWorking(false); }
  }

  const disabled = busy || working;
  return (
    <Card size="small" className="rewrite-card" data-testid="selection-rewrite-panel" title={<Space><EditOutlined />选区改写</Space>}
      extra={selection ? <Button size="small" type="link" onClick={onClear}>清除选区</Button> : null}>
      {!selection ? (
        <p className="muted">在正文中选中一段文字，点浮动按钮“问对话助手”，可得到 3～5 种写法。</p>
      ) : (
        <>
          <blockquote data-testid="rewrite-selection">{selection.text.length > 200 ? `${selection.text.slice(0, 200)}…` : selection.text}</blockquote>
          <span className="muted">已选 {selection.text.length} 字</span>
          {problem && <Alert type="warning" showIcon message={problem} style={{ marginTop: 8 }} />}
          <div className="prompt-chips" style={{ marginTop: 8 }}>
            {REWRITE_MODES.map(item => (
              <button key={item.value} className={mode === item.value ? 'active' : ''} aria-pressed={mode === item.value} onClick={() => setMode(item.value)}>{item.label}</button>
            ))}
          </div>
          {mode === 'instruction' && (
            <Input.TextArea aria-label="选区修改要求" rows={2} maxLength={500} value={instruction} onChange={e => setInstruction(e.target.value)}
              placeholder="例如：语气更正式，突出每月巡检报告由负责人复核" />
          )}
          <Space style={{ marginTop: 8 }}>
            <Select size="small" aria-label="样例条数" value={count} onChange={setCount} options={[3, 4, 5].map(value => ({ value, label: `${value} 条样例` }))} />
            <Button size="small" type="primary" data-testid="rewrite-generate-btn" loading={working && !pending}
              disabled={disabled || !!problem || !canGenerate || (mode === 'instruction' && !instruction.trim())} onClick={generate}>
              生成样例
            </Button>
          </Space>
          {!canGenerate && <p className="muted">你不是本节编写人，不能请助手改写本节。</p>}
        </>
      )}
      {working && !pending && !batch && <p className="muted" role="status" style={{ marginTop: 12 }}><Spin size="small" /> 模型正在按不同写法改写…</p>}
      {invalid && <Alert type="warning" showIcon message={invalid} style={{ marginTop: 8 }} />}
      {result && <RecheckResult result={result} />}
      {batch && (
        <div style={{ marginTop: 12 }} data-testid="rewrite-batch">
          <p className="muted">{batch.mode_label} · {batch.samples.length} 条样例 · {batch.source_note} · 模型 {batch.model || batch.provider}{batch.is_local_model ? '（本地）' : ''}</p>
          {batch.dropped.length > 0 && (
            <Alert type="info" showIcon message={`${batch.dropped.length} 条未展示`} description={batch.dropped.map(d => `${d.style}：${d.reason}`).join('；')} style={{ marginBottom: 8 }} />
          )}
          {batch.samples.length === 0 && <Empty description="没有可用样例" />}
          {batch.samples.map(sample => (
            <Card key={sample.id} size="small" className="suggestion-card" data-testid="rewrite-sample"
              title={<Space><Tag color="purple">{sample.style_label}</Tag><span className="muted">{sample.chars} 字</span>
                {sample.status === 'adopted' && <Tag color="green">已采纳</Tag>}{sample.status === 'invalidated' && <Tag>已失效</Tag>}</Space>}>
              <p className="suggestion-content" data-testid="rewrite-sample-text">{sample.text}</p>
              {sample.warnings.map(text => <Alert key={text} type="warning" showIcon message={text} style={{ marginBottom: 6 }} />)}
              <p className="muted">无知识库来源</p>
              <Space wrap>
                {(['replace', 'insert_after'] as RewriteAction[]).map(action => (
                  <Tooltip key={action} title={leaseToken ? '' : '先取得本节编辑权'}>
                    <Button size="small" type={action === 'replace' ? 'primary' : 'default'} data-testid={action === 'replace' ? 'rewrite-replace-btn' : 'rewrite-insert-btn'}
                      disabled={disabled || !leaseToken || sample.status !== 'proposed' || batch.status !== 'proposed'}
                      onClick={() => setPending({ sample, action })}>
                      {ACTION_LABEL[action]}
                    </Button>
                  </Tooltip>
                ))}
              </Space>
            </Card>
          ))}
        </div>
      )}
      <WriteConfirm batch={batch} pending={pending} committed={committed} working={working} onCancel={() => setPending(null)} onConfirm={confirm} />
    </Card>
  );
}

function WriteConfirm({ batch, pending, committed, working, onCancel, onConfirm }: {
  batch: RewriteBatch | null; pending: Pending | null; committed: string; working: boolean; onCancel: () => void; onConfirm: () => void;
}) {
  if (!batch || !pending) return null;
  const start = pending.confirmStart ?? batch.start;
  const end = start + batch.selected_text.length;
  const after = previewWrite(committed, start, end, pending.sample.text, pending.action);
  const from = committed.lastIndexOf('\n', start - 1) + 1;
  const stopAt = committed.indexOf('\n', end);
  const stop = stopAt < 0 ? committed.length : stopAt;
  const before = committed.slice(from, stop);
  const changed = after.slice(from, stop + (after.length - committed.length));
  const parts = diffText(before, changed);
  const added = pendingCount(pending.sample.text);
  return (
    <Modal open title={`确认写入 · ${ACTION_LABEL[pending.action]}`} onCancel={onCancel} onOk={onConfirm} okText="确认写入" cancelText="不写入"
      confirmLoading={working} width={720} okButtonProps={{ 'data-testid': 'rewrite-confirm-btn' } as never}>
      {pending.moved && <Alert type="warning" showIcon style={{ marginBottom: 12 }} message="原文位置已变化，已在本章重新找到；请再次核对下面的差异后确认写入。" />}
      <div className="rewrite-diff" data-testid="rewrite-diff">
        {parts.map((part, index) => part.kind === 'same' ? <span key={index}>{part.text}</span>
          : part.kind === 'added' ? <ins key={index}>{part.text}</ins> : <del key={index}>{part.text}</del>)}
      </div>
      <ul className="rewrite-facts">
        <li>修改方式：{pending.action === 'replace' ? '对话助手替换' : '对话助手增加'}（{batch.mode_label} · {pending.sample.style_label}）</li>
        <li>知识库：未检索，样例为“无知识库来源”</li>
        <li>将新增【待补】：{added} 处{added ? '，导出前须补齐' : ''}</li>
        {pending.sample.warnings.map(text => <li key={text}>需人工确认：{text}</li>)}
        <li>写入后生成新的章节版本，并只对改动段落做规则复查；之前的检查和导出会失效。</li>
      </ul>
    </Modal>
  );
}

function RecheckResult({ result }: { result: ApplyResult }) {
  const issues = result.operation.recheck.issues;
  return (
    <Alert style={{ marginTop: 8 }} type={issues.length ? 'warning' : 'success'} showIcon data-testid="rewrite-recheck"
      message={`已写入 v${result.revision}（${result.operation.edit_mode_label}）· 改动段落复查${issues.length ? `发现 ${issues.length} 项` : '未发现问题'}`}
      description={issues.length ? issues.map(item => `${item.rule_id}：${item.message}`).join('；') : undefined} />
  );
}
