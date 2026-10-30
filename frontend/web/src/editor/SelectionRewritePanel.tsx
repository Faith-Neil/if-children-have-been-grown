// 为什么有这个文件：编辑台右侧“对话助手”中的选区改写（PRD v1.8 §5.11.2、§5.11.5、§5.11.6、§5.11.11；APP-M2-T176～T180、T185、T187）。
// 它解决什么问题：选中一段文字后，请助手给出 3～5 种写法；每条样例显示写法、引用来源（或“无知识库来源”）、预检提示与字数，
// 可“替换选中内容”或“插在选中内容后”；写入前弹出差异视图，确认后由后端核对编辑锁与选区再写入新版本，并显示改动段落的复查结果。
// 面板顶部显示当前模型（含是否本地）和知识库开关（默认值与能否关闭取公司设置）；样例按完成先后流式出现；
// 每次提问与写入记入本人会话，可在会话里接着提要求，也能回看之前的会话。
// 模型逐字输出时各写法先显示原文预览（预检通过后换成样例）；可随时“停止”（断开连接，服务端停止生成、不保存）；
// 主模型失败改用备用模型时显示“已使用备用模型 X”（APP-M2-T177）。

import React, { useEffect, useRef, useState } from 'react';
import { Alert, Button, Card, Collapse, Empty, Input, Modal, Select, Space, Spin, Switch, Tag, Tooltip } from 'antd';
import { EditOutlined } from '@ant-design/icons';
import { ApiError, request, streamEvents } from '../shared/api.ts';
import type { Chapter } from '../shared/types.ts';
import { AssistantAskBox } from './AssistantAskBox.tsx';
import {
  ACTION_LABEL, EMPTY_STREAM, REWRITE_MODES, assistantPaths, defaultKnowledgeBase, diffText, fallbackNotice, isAbort, knowledgeBaseNote,
  locateSelection, modelLabel, pendingCount, previewWrite, reduceStream, relocation, rewritePath, selectionProblem,
  type ApplyResult, type AssistantPolicy, type RewriteAction, type RewriteBatch, type RewriteMode, type RewriteSample,
  type SessionDetail, type SessionSummary, type StreamState,
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
const NEW_SESSION = '__new__';

export function SelectionRewritePanel({ projectId, chapter, content, selection, leaseToken, canGenerate, busy, token, onApplied, onClear, report }: SelectionRewritePanelProps) {
  const [mode, setMode] = useState<RewriteMode>('rewrite');
  const [instruction, setInstruction] = useState('');
  const [count, setCount] = useState(3);
  const [policy, setPolicy] = useState<AssistantPolicy | null>(null);
  const [knowledgeBase, setKnowledgeBase] = useState(false);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [sessionId, setSessionId] = useState<string>(NEW_SESSION);
  const [history, setHistory] = useState<SessionDetail | null>(null);
  const [batch, setBatch] = useState<RewriteBatch | null>(null);
  const [live, setLive] = useState<StreamState | null>(null);
  const [working, setWorking] = useState(false);
  const [pending, setPending] = useState<Pending | null>(null);
  const [result, setResult] = useState<ApplyResult | null>(null);
  const [invalid, setInvalid] = useState('');
  const [historyTick, setHistoryTick] = useState(0);
  const [stopped, setStopped] = useState(false);
  const abort = useRef<AbortController | null>(null);
  useEffect(() => () => abort.current?.abort(), []);
  const paths = chapter ? assistantPaths(projectId, chapter.id) : null;

  async function loadSessions(keep?: string) {
    if (!paths) return;
    const value = await request<{ sessions: SessionSummary[] }>(paths.sessions, token);
    setSessions(value.sessions);
    if (keep) setSessionId(keep);
    setHistoryTick(tick => tick + 1);
  }

  useEffect(() => {
    setBatch(null); setResult(null); setInvalid(''); setLive(null); setSessionId(NEW_SESSION); setHistory(null);
    if (!paths) return;
    let cancelled = false;
    request<AssistantPolicy>(paths.policy, token).then(value => {
      if (cancelled) return;
      setPolicy(value); setKnowledgeBase(defaultKnowledgeBase(value)); setCount(value.count);
    }).catch(() => { if (!cancelled) setPolicy(null); });
    loadSessions().catch(() => undefined);
    return () => { cancelled = true; };
  }, [chapter?.id, token]);

  // 换了选区才清空上一组样例；写入后选区被清除时保留结果与复查提示
  useEffect(() => { if (selection) { setBatch(null); setResult(null); setInvalid(''); setLive(null); } }, [selection?.text, selection?.start]);

  useEffect(() => {
    if (!paths || sessionId === NEW_SESSION) { setHistory(null); return; }
    request<SessionDetail>(paths.session(sessionId), token).then(setHistory).catch(report);
  }, [sessionId, historyTick]);

  if (!chapter || !paths) return null;
  const committed = chapter.content ?? '';
  const problem = selection ? selectionProblem(committed, content, selection.text, selection.start, selection.end) : null;
  const located = selection ? locateSelection(committed, selection.text, selection.start, selection.end) : null;

  async function generate() {
    if (!located || !chapter || !paths) return;
    setWorking(true); setResult(null); setInvalid(''); setBatch(null); setLive(EMPTY_STREAM); setStopped(false);
    let final: RewriteBatch | null = null;
    const controller = new AbortController();
    abort.current = controller;
    try {
      await streamEvents(paths.stream, token, {
        base_revision: chapter.revision, start: located.start, end: located.end, selected_text: located.text,
        mode, instruction: mode === 'instruction' ? instruction.trim() : '', count, knowledge_base_enabled: knowledgeBase,
        ...(sessionId !== NEW_SESSION ? { session_id: sessionId } : {}),
      }, event => {
        if (event.event === 'done') { final = event.batch as RewriteBatch; return; }
        if (event.event === 'error') throw new ApiError(Number(event.status) || 502, String(event.code), String(event.message));
        setLive(current => reduceStream(current ?? EMPTY_STREAM, event));
      }, controller.signal);
      const done = final as RewriteBatch | null;
      if (done) { setBatch(done); await loadSessions(done.session_id ?? undefined); }
    } catch (error) {
      if (isAbort(error)) setStopped(true); else report(error);
    } finally { abort.current = null; setWorking(false); setLive(null); }
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
      await loadSessions(value.batch.session_id ?? undefined).catch(() => undefined);
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
  const shown = live ? live.samples : batch?.samples ?? [];
  const dropped = live ? live.dropped : batch?.dropped ?? [];
  return (
    <Card size="small" className="rewrite-card" data-testid="selection-rewrite-panel" title={<Space><EditOutlined />选区改写</Space>}
      extra={selection ? <Button size="small" type="link" onClick={onClear}>清除选区</Button> : null}>
      <div className="rewrite-toolbar">
        <Tag color={policy?.is_real_model ? 'purple' : 'default'} data-testid="assistant-model-label">{modelLabel(policy) || '读取模型…'}</Tag>
        <Space size={4}>
          <span>知识库</span>
          <Switch size="small" aria-label="知识库" data-testid="assistant-kb-switch" checked={knowledgeBase}
            disabled={!policy || !policy.allow_kb_off || disabled} onChange={setKnowledgeBase} />
        </Space>
      </div>
      <p className="muted" data-testid="assistant-kb-note">{knowledgeBaseNote(policy, knowledgeBase)}</p>
      {policy && !policy.enabled && <Alert type="info" showIcon message="本公司已关闭对话助手" />}
      <Space size={4} style={{ marginBottom: 8 }} wrap>
        <Select size="small" aria-label="会话" style={{ minWidth: 200 }} value={sessionId} onChange={setSessionId}
          options={[{ value: NEW_SESSION, label: '新会话' }, ...sessions.map(item => ({
            value: item.id, label: `${item.title}${item.title.length >= 24 ? '…' : ''}${item.owner_name ? ` · ${item.owner_name}` : ''}`,
          }))]} />
        {history && <span className="muted">{history.message_count} 条记录{history.read_only ? ' · 只读' : ''}</span>}
      </Space>
      {history && history.messages.length > 0 && <SessionHistory detail={history} />}
      {!selection ? (
        <>
          <p className="muted">在正文中选中一段文字，点浮动按钮“问对话助手”，可得到 3～5 种写法；不选中时可以直接提问。</p>
          <AssistantAskBox projectId={projectId} chapterId={chapter.id} token={token} knowledgeBase={knowledgeBase}
            sessionId={sessionId === NEW_SESSION ? null : sessionId} disabled={disabled || !policy?.enabled}
            onAnswered={id => { void loadSessions(id ?? undefined); }} />
        </>
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
              placeholder={sessionId === NEW_SESSION ? '例如：语气更正式，突出每月巡检报告由负责人复核' : '接着上一轮说，例如：再短一点'} />
          )}
          <Space style={{ marginTop: 8 }}>
            <Select size="small" aria-label="样例条数" value={count} onChange={setCount} options={[3, 4, 5].map(value => ({ value, label: `${value} 条样例` }))} />
            <Button size="small" type="primary" data-testid="rewrite-generate-btn" loading={working && !pending}
              disabled={disabled || !!problem || !canGenerate || !policy?.enabled || (mode === 'instruction' && !instruction.trim())} onClick={generate}>
              生成样例
            </Button>
          </Space>
          {!canGenerate && <p className="muted">你不是本节编写人，不能请助手改写本节。</p>}
        </>
      )}
      {live && (
        <p className="muted" role="status" style={{ marginTop: 12 }}>
          <Spin size="small" /> {live.retrieval?.status === 'found' ? `${live.retrieval.message} ` : ''}
          已完成 {live.samples.length + live.dropped.length} / {live.styles.length || count} 种写法…
          <Button size="small" type="link" danger data-testid="rewrite-stop-btn" onClick={() => abort.current?.abort()}>停止</Button>
        </p>
      )}
      {stopped && <Alert type="info" showIcon data-testid="rewrite-stopped" style={{ marginTop: 8 }} message="已停止生成，正文没有修改，本次样例不保存。" />}
      {(live?.fallbacks.length || batch?.fallback_used?.length) ? (
        <Alert type="warning" showIcon data-testid="rewrite-fallback" style={{ marginTop: 8 }}
          message={fallbackNotice(live ? live.fallbacks : batch?.fallback_used)} />
      ) : null}
      {live && Object.entries(live.drafts).map(([style, text]) => (
        <Card key={`draft-${style}`} size="small" className="suggestion-card" data-testid="rewrite-draft"
          title={<Space><Tag>{style}</Tag><span className="muted">生成中，预检后才能使用</span></Space>}>
          <p className="suggestion-content muted">{text}</p>
        </Card>
      ))}
      {invalid && <Alert type="warning" showIcon message={invalid} style={{ marginTop: 8 }} />}
      {result && <RecheckResult result={result} />}
      {batch?.status === 'no_results' && <Alert type="info" showIcon data-testid="rewrite-no-results" style={{ marginTop: 8 }} message={batch.retrieval.message} />}
      {(batch || live) && batch?.status !== 'no_results' && (
        <div style={{ marginTop: 12 }} data-testid="rewrite-batch">
          {batch && <p className="muted">{batch.mode_label} · {batch.samples.length} 条样例 · {batch.source_note} · 模型 {batch.model || batch.provider}{batch.is_local_model ? '（本地）' : ''}</p>}
          {dropped.length > 0 && (
            <Alert type="info" showIcon message={`${dropped.length} 条未展示`} description={dropped.map(d => `${d.style}：${d.reason}`).join('；')} style={{ marginBottom: 8 }} />
          )}
          {batch && shown.length === 0 && <Empty description="没有可用样例" />}
          {shown.map(sample => (
            <Card key={sample.id} size="small" className="suggestion-card" data-testid="rewrite-sample"
              title={<Space><Tag color="purple">{sample.style_label}</Tag><span className="muted">{sample.chars} 字</span>
                {sample.is_fallback && <Tooltip title={sample.fallback_reason}><Tag color="orange">备用模型 {sample.model}</Tag></Tooltip>}
                {sample.status === 'adopted' && <Tag color="green">已采纳</Tag>}{sample.status === 'invalidated' && <Tag>已失效</Tag>}</Space>}>
              <p className="suggestion-content" data-testid="rewrite-sample-text">{sample.text}</p>
              {sample.warnings.map(text => <Alert key={text} type="warning" showIcon message={text} style={{ marginBottom: 6 }} />)}
              {sample.sources.length ? (
                <ul className="rewrite-sources" data-testid="rewrite-sources">
                  {sample.sources.map(src => <li key={src.cite_tag}><Tag>{src.cite_tag}</Tag>{src.name}（v{src.revision}）</li>)}
                </ul>
              ) : <p className="muted">无知识库来源</p>}
              <Space wrap>
                {(['replace', 'insert_after'] as RewriteAction[]).map(action => (
                  <Tooltip key={action} title={leaseToken ? '' : '先取得本节编辑权'}>
                    <Button size="small" type={action === 'replace' ? 'primary' : 'default'} data-testid={action === 'replace' ? 'rewrite-replace-btn' : 'rewrite-insert-btn'}
                      disabled={disabled || !batch || !leaseToken || sample.status !== 'proposed' || batch.status !== 'proposed'}
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

function SessionHistory({ detail }: { detail: SessionDetail }) {
  return (
    <Collapse size="small" style={{ marginBottom: 8 }} data-testid="assistant-session-history" items={[{
      key: 'history', label: '会话记录',
      children: (
        <ol className="session-messages">
          {detail.messages.map(message => (
            <li key={message.id} className={message.role}>
              {message.kind === 'selection_request' && <>问：{message.mode_label}{message.instruction ? `（${message.instruction}）` : ''} · 「{(message.selected_text ?? '').slice(0, 40)}」{message.knowledge_base_enabled ? ' · 知识库开' : ' · 知识库关'}</>}
              {message.kind === 'samples' && <>答：{message.batch?.status === 'no_results' ? message.retrieval?.message : `${message.sample_count ?? 0} 条样例`}{message.batch?.samples.find(s => s.status === 'adopted') ? ' · 已采纳 1 条' : ''}</>}
              {message.kind === 'applied' && <>写入：{message.edit_mode_label}，生成 v{message.result_revision}</>}
              {message.kind === 'question' && <>问：{(message.question ?? '').slice(0, 60)}{message.knowledge_base_enabled ? ' · 知识库开' : ' · 知识库关'}</>}
              {message.kind === 'answer' && <>答：{message.route === 'direct_query' ? '答案卡' : message.route === 'no_results' ? '知识库无结果' : (message.answer ?? '').slice(0, 80)}</>}
            </li>
          ))}
        </ol>
      ),
    }]} />
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
  const sources = pending.sample.sources;
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
        <li>知识库：{batch.knowledge_base_enabled ? (sources.length ? `引用 ${sources.map(s => `${s.name}（v${s.revision}）`).join('、')}` : '已打开') : '已关闭，样例为“无知识库来源”'}</li>
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
