// 为什么有这个文件：保留示例的章节目录、正文和助手三栏编辑流程。
// 它解决什么问题：编辑权、旧草稿、正式版本与建议确认都以后台实际校验为准。
import { useEffect, useRef, useState } from 'react';
import { displaySlaValue, insertSlaMeasurement } from './sla-form';
import { Alert, App as AntApp, Button, Card, Checkbox, Drawer, Empty, Input, Modal, Radio, Select, Space, Spin, Tabs, Tag, Tooltip } from 'antd';
import { FileTextOutlined, HistoryOutlined, LockOutlined, SaveOutlined, SendOutlined, UnlockOutlined } from '@ant-design/icons';
import { ApiError, request } from './api';
import { formatTime, useProject, volumeName } from './context';
import type { Candidate, Chapter, Volume, Workspace, WritingInputPreview } from './types';
import { recoveryWrite } from './editor-recovery';
import RecoveryReview, { type RecoveryChoice } from './RecoveryReview';
import WritingPlanReview from './WritingPlanReview';
import WritingInputPreviewContent, { WritingSources } from './WritingInputPreview';
import { candidateProblem, insertFactToken } from './writing-input';
import { acquiredEditingFingerprint, editingContentWrite, loadedEditingFingerprint, recoveryEditingFingerprint, reviewedEditingFingerprint } from './editing-source';
import { chapterCan } from './project-team';

type Lease = { lease_token: string; expires_at: string; owner_id: string };
type Version = { revision: number; content: string; actor_id: string; created_at: string };

export default function EditorPage({ onDirtyChange }: { onDirtyChange: (dirty: boolean) => void }) {
  const { workspace, user, token, busy: projectBusy, mutate, reload, report, navigate } = useProject();
  const { modal } = AntApp.useApp();
  const [volume, setVolume] = useState<Volume>('technical');
  const [chapterId, setChapterId] = useState(workspace.chapters.find(item => item.volume === 'technical')?.id ?? workspace.chapters[0]?.id ?? '');
  const [chapter, setChapter] = useState<Chapter | null>(null);
  const [content, setContent] = useState('');
  const [editFingerprint, setEditFingerprint] = useState<string | null>(null);
  const [sourceReview, setSourceReview] = useState<{ preview: WritingInputPreview; target: 'editor' | 'recovery' } | null>(null);
  const [sourceReviewed, setSourceReviewed] = useState(false);
  const [lease, setLease] = useState<Lease | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [rightTab, setRightTab] = useState('assistant');
  const [instruction, setInstruction] = useState('写得更具体，按原文和已确认事实说明工作步骤，不能新增未经核实的承诺。');
  const [suggestion, setSuggestion] = useState<Candidate | null>(null);
  const [diff, setDiff] = useState<Candidate | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const [savedAt, setSavedAt] = useState('');
  const [slaKey, setSlaKey] = useState('');
  const [factId, setFactId] = useState('');
  const selection = useRef<{ start: number; end: number } | null>(null);
  const [notice, setNotice] = useState('');
  const [sourceAdvice, setSourceAdvice] = useState(false);
  const [versions, setVersions] = useState<Version[]>([]);
  const [versionsOpen, setVersionsOpen] = useState(false);
  const [planOpen, setPlanOpen] = useState(false);
  const [inputOpen, setInputOpen] = useState(false);
  const [recovery, setRecovery] = useState<RecoveryChoice | null>(null);
  const [recoveryReviewed, setRecoveryReviewed] = useState(false);
  const epoch = useRef(0);
  const currentLease = useRef<Lease | null>(null);
  const currentId = useRef(chapterId);
  const sequence = useRef(0);
  const dirty = chapter ? content !== (chapter.draft?.base_revision === chapter.revision ? chapter.draft.content : chapter.content) : false;
  const modified = chapter ? content !== chapter.content : false;
  const combinedBusy = busy || projectBusy || loading;
  const activeChapter = workspace.chapters.find(item => item.id === chapterId);
  const canEdit = chapterCan(activeChapter, 'edit');
  const canGenerate = chapterCan(activeChapter, 'generate');
  const planCurrent = activeChapter?.writing_input?.is_current === true;
  const held = canEdit && !!lease && Date.parse(lease.expires_at) > Date.now();
  const proposed = suggestion ?? workspace.chapters.find(item => item.id === chapterId)?.candidate ?? null;
  const candidate = proposed;
  const candidateIssue = candidate ? candidateProblem(candidate, workspace.input_fingerprint, chapter?.revision) : null;
  const sources = workspace.requirements.filter(item => item.chapter_id === chapterId || workspace.chapters.find(value => value.id === chapterId)?.requirement_ids?.includes(item.id));
  const sourceStale = !!chapter && editFingerprint !== workspace.input_fingerprint;

  useEffect(() => { onDirtyChange(dirty); }, [dirty]);
  useEffect(() => {
    if (!canEdit && currentLease.current) {
      currentLease.current = null; setLease(null);
      setNotice('本节分工或项目权限已经变化，写入口已关闭。当前文字仍保留，可先保留一份本地文字，再核对最新分工。');
    }
  }, [canEdit]);
  useEffect(() => {
    function leaving(event: BeforeUnloadEvent) { if (dirty) { event.preventDefault(); event.returnValue = ''; } }
    window.addEventListener('beforeunload', leaving); return () => window.removeEventListener('beforeunload', leaving);
  }, [dirty]);
  useEffect(() => {
    currentId.current = chapterId; const start = ++epoch.current;
    setChapter(null); setContent(''); setEditFingerprint(null); setSourceReview(null); setSourceReviewed(false); selection.current = null; setSlaKey(''); setFactId(''); setLease(null); currentLease.current = null; setSuggestion(null); setDiff(null); setInputOpen(false); setSourceAdvice(false); setRecovery(null); setSavedAt(''); setNotice(''); onDirtyChange(false);
    if (!chapterId) return;
    setLoading(true);
    request<Chapter>(`/api/chapters/${chapterId}`, token).then(data => {
      if (start !== epoch.current) return;
      setChapter(data); sequence.current = data.draft?.sequence ?? 0;
      setEditFingerprint(loadedEditingFingerprint(data, workspace.input_fingerprint));
      if (data.draft && data.draft.base_revision !== data.revision) { setContent(data.content); setNotice('存在基于旧版本的个人草稿。当前先展示新版本正文，旧草稿没有自动覆盖。'); }
      else { setContent(data.draft?.content ?? data.content); if (data.draft) setNotice('已恢复当前版本的个人草稿，提交本节后才进入正式正文和导出。'); }
    }).catch(error => { if (start === epoch.current) report(error); }).finally(() => { if (start === epoch.current) setLoading(false); });
    return () => {
      ++epoch.current;
      const previous = currentLease.current; currentLease.current = null;
      if (previous) void request(`/api/chapters/${chapterId}/lock/release`, token, 'POST', { lease_token: previous.lease_token }).catch(() => undefined);
    };
  }, [chapterId, token]);
  useEffect(() => {
    if (!lease) return;
    const start = epoch.current;
    const timer = window.setInterval(async () => {
      const activeLease = currentLease.current;
      if (!activeLease || start !== epoch.current) return;
      try { const renewed = await request<Lease>(`/api/chapters/${chapterId}/lock/renew`, token, 'POST', { lease_token: activeLease.lease_token }); if (start === epoch.current && activeLease.lease_token === currentLease.current?.lease_token) { currentLease.current = renewed; setLease(renewed); } }
      catch (error) { if (start === epoch.current && activeLease.lease_token === currentLease.current?.lease_token) { currentLease.current = null; setLease(null); setNotice('编辑权续期失败，文字已保留在当前页面。请重新取得编辑权后核对版本再保存。'); report(error); if (error instanceof ApiError && [403, 404].includes(error.status)) void reload().catch(report); } }
    }, 30_000);
    return () => window.clearInterval(timer);
  }, [lease?.lease_token, chapterId, token]);

  function localError(error: unknown) {
    report(error);
    if (error instanceof ApiError && ['INPUT_FINGERPRINT_REQUIRED', 'INPUT_FINGERPRINT_STALE'].includes(error.code)) {
      setNotice(error.code === 'INPUT_FINGERPRINT_REQUIRED' ? '这份文字尚未记录来源依据，文字仍保留。请核对最新来源，再保存或提交。' : '条款、事实、证据或写作方案已经变化，本次保存或提交未成功，文字和原依据仍保留。请核对最新来源后再写入。');
      void reload().catch(report); return;
    }
    if (error instanceof ApiError && error.code === 'FACT_SOURCE_CHANGE_REQUIRED') { setSourceAdvice(true); setNotice(error.message); return; }
    if (error instanceof ApiError && [403, 404].includes(error.status)) {
      currentLease.current = null; setLease(null);
      setNotice('本次操作没有权限，当前文字保留在页面。请核对最新项目成员和章节分工；个人草稿不会转送给其他人。');
      void reload().catch(report); return;
    }
    if (error instanceof ApiError && error.status === 423) { currentLease.current = null; setLease(null); setNotice('编辑权已失效，当前文字仍在页面。请重新取得编辑权，避免覆盖其他人。'); }
    if (error instanceof ApiError && error.status === 409) setNotice('后台正文或草稿已变化，本次写入没有成功。当前文字保留；请查看最新版本后核对，不能继续覆盖。');
  }
  async function run(action: () => Promise<void>) { setBusy(true); try { await action(); } catch (error) { localError(error); } finally { setBusy(false); } }
  async function acquire(reason: string | null = null) {
    if (!canEdit || combinedBusy) return;
    await run(async () => {
      const start = epoch.current;
      const result = await request<Lease>(`/api/chapters/${chapterId}/lock`, token, 'POST', { takeover_reason: reason });
      if (start !== epoch.current) return;
      currentLease.current = result; setLease(result);
      const latest = await request<Chapter>(`/api/chapters/${chapterId}`, token);
      if (start !== epoch.current) return;
      if (chapter && latest.revision !== chapter.revision && modified) { setNotice('取得编辑权时发现新版本。当前文字未被清除，请先查看最新版本，核对后再编辑。'); currentLease.current = null; setLease(null); await request(`/api/chapters/${chapterId}/lock/release`, token, 'POST', { lease_token: result.lease_token }); return; }
      setChapter(latest); sequence.current = latest.draft?.sequence ?? sequence.current;
      if (!modified) setContent(latest.draft?.base_revision === latest.revision ? latest.draft.content : latest.content);
      setEditFingerprint(acquiredEditingFingerprint(editFingerprint, latest, modified));
      setNotice('已取得编辑权。其他账号会被后台阻止写入。');
    });
  }
  function takeover() { let reason = ''; modal.confirm({ title: '说明接管编辑的理由', content: <Input.TextArea aria-label="接管理由" placeholder="接管会使原编辑人的凭据失效，原因将留在操作记录中" onChange={e => { reason = e.target.value; }} />, okText: '填写理由并接管', onOk: async () => { if (!reason.trim()) throw new Error('请填写接管理由'); await acquire(reason); } }); }
  async function release() { await run(async () => { if (!lease) return; await request(`/api/chapters/${chapterId}/lock/release`, token, 'POST', { lease_token: lease.lease_token }); currentLease.current = null; setLease(null); setChapter(await request<Chapter>(`/api/chapters/${chapterId}`, token)); }); }
  async function saveDraft() { await run(async () => {
    if (!chapter || !lease || !canEdit) return;
    const start = epoch.current;
    const value = await request<NonNullable<Chapter['draft']>>(`/api/chapters/${chapterId}/draft`, token, 'PUT', { lease_token: lease.lease_token, base_revision: chapter.revision, sequence: ++sequence.current, ...editingContentWrite(content, editFingerprint) });
    if (start !== epoch.current) return;
    setChapter({ ...chapter, draft: value }); setEditFingerprint(value.input_fingerprint ?? null);
    setSavedAt(new Date().toLocaleTimeString('zh-CN', { hour12: false })); setNotice('个人草稿及对应来源依据已保存；尚未进入正式正文和导出。');
  }); }
  async function commit() { await run(async () => {
    if (!chapter || !lease || !canEdit) return;
    const start = epoch.current;
    await request(`/api/chapters/${chapterId}/versions`, token, 'POST', { lease_token: lease.lease_token, base_revision: chapter.revision, ...editingContentWrite(content, editFingerprint), idempotency_key: crypto.randomUUID() });
    const updated = await request<Chapter>(`/api/chapters/${chapterId}`, token);
    const current = await request<Workspace>(`/api/v1/projects/${workspace.project.id}/workspace`, token);
    if (start !== epoch.current) return;
    setChapter(updated); setContent(updated.content); setEditFingerprint(current.input_fingerprint); setSuggestion(null); sequence.current = updated.draft?.sequence ?? sequence.current;
    setSavedAt(new Date().toLocaleTimeString('zh-CN', { hour12: false })); setNotice(`已提交正文 v${updated.revision}；之前的检查和导出会失效，需要重新运行。`); await reload();
  }); }
  async function suggest() { if (!canGenerate || !planCurrent || combinedBusy) return; await run(async () => { const start = epoch.current; const value = await request<Candidate>(`/api/chapters/${chapterId}/suggestions`, token, 'POST', { instruction }); if (start === epoch.current) setSuggestion(value); }); }
  async function generate() { if (!canGenerate || !planCurrent || combinedBusy) return; try { await mutate(`/api/v1/projects/${workspace.project.id}/generate`, 'POST', { chapter_ids: [chapterId] }); setSuggestion(null); setNotice('已生成候选，尚未改动正式正文。请在右侧比较并确认。'); } catch { /* 统一入口已经显示错误 */ } }
  async function viewVersions() { await run(async () => { const value = await request<{ versions: Version[] }>(`/api/chapters/${chapterId}/versions`, token); setVersions(value.versions.slice().reverse()); setVersionsOpen(true); }); }
  function selectChapter(id: string, nextVolume?: Volume) {
    const action = () => { if (nextVolume) setVolume(nextVolume); setChapterId(id); };
    if (!dirty) action(); else modal.confirm({ title: '当前章节还有未保存文字', content: '先保存草稿或提交本节，才能保证这些文字不丢失。', okText: '离开当前章节', cancelText: '继续编辑', onOk: action });
  }
  function showDiff(value: Candidate) { if (candidateProblem(value, workspace.input_fingerprint, chapter?.revision)) return; setReviewed(false); setDiff(value); }
  async function apply() {
    if (!chapter || !lease || !held || !diff || candidateProblem(diff, workspace.input_fingerprint, chapter.revision) || !reviewed) return;
    await run(async () => {
      const start = epoch.current;
      const latest = await request<Workspace>(`/api/v1/projects/${workspace.project.id}/workspace`, token);
      if (start !== epoch.current) return;
      if (!diff.input_fingerprint || diff.input_fingerprint !== latest.input_fingerprint) {
        setDiff(null); setSuggestion(null); await reload();
        throw new Error('条款、事实、证据或正文已变化，这份候选已过期。请重新生成后核对。');
      }
      setContent(diff.content); setEditFingerprint(diff.input_fingerprint); setDiff(null); setSuggestion(null); setNotice('候选及生成时的来源依据已写入当前编辑内容。请人工修订，再保存草稿或提交本节。');
    });
  }
  function reviewRecovery(choice: RecoveryChoice) { setRecoveryReviewed(false); setRecovery(choice); }
  async function saveRecovery() {
    if (!chapter || !lease || !held || !recovery || !recoveryReviewed) return;
    await run(async () => {
      const start = epoch.current;
      const latest = await request<Chapter>(`/api/chapters/${chapterId}`, token);
      if (start !== epoch.current) return;
      const current = await request<Workspace>(`/api/v1/projects/${workspace.project.id}/workspace`, token);
      if (start !== epoch.current) return;
      const write = recoveryWrite(chapter, latest, recovery.content);
      const fingerprint = recoveryEditingFingerprint(recovery, current.input_fingerprint);
      const draft = await request<NonNullable<Chapter['draft']>>(`/api/chapters/${chapterId}/draft`, token, 'PUT', { ...write, ...editingContentWrite(recovery.content, fingerprint), lease_token: lease.lease_token });
      if (start !== epoch.current) return;
      sequence.current = draft.sequence; setChapter({ ...latest, draft }); setContent(draft.content); setEditFingerprint(draft.input_fingerprint ?? null); setRecovery(null);
      setSavedAt(new Date().toLocaleTimeString('zh-CN', { hour12: false }));
      setNotice('恢复内容及其来源依据已保存为新的个人草稿，正式正文未变。请修订后提交本节。');
    });
  }
  async function reviewCurrentSources(target: 'editor' | 'recovery') {
    await run(async () => {
      const start = epoch.current;
      const preview = await request<WritingInputPreview>(`/api/v1/projects/${workspace.project.id}/chapters/${chapterId}/writing-input`, token);
      if (start !== epoch.current) return;
      setSourceReviewed(false); setSourceReview({ preview, target });
    });
  }
  async function confirmCurrentSources() {
    if (!sourceReview || !sourceReviewed || !chapter || !held || !canEdit) return;
    await run(async () => {
      const start = epoch.current;
      const current = await request<Workspace>(`/api/v1/projects/${workspace.project.id}/workspace`, token);
      if (start !== epoch.current) return;
      const fingerprint = reviewedEditingFingerprint(sourceReview.preview.input_snapshot.input_fingerprint, current, chapterId, chapter.revision);
      if (sourceReview.target === 'recovery') {
        if (!recovery) return;
        setRecovery({ ...recovery, reviewed_input_fingerprint: fingerprint }); setRecoveryReviewed(false);
      } else setEditFingerprint(fingerprint);
      setSourceReview(null); setSourceReviewed(false); setNotice('已人工核对当前来源并更新本次文字的写作依据；正文、草稿和原资料尚未改变，仍须保存或提交。');
      await reload();
    });
  }
  function insertVariable() {
    const row = workspace.sla?.rows.find(item => item.var_key === slaKey);
    if (!held || combinedBusy || !row || row.fact_status !== 'confirmed' || row.source_stale || workspace.sla?.template_stale) return;
    try {
      const range = selection.current ?? { start: content.length, end: content.length };
      const result = insertSlaMeasurement(content, range.start, range.end, row.variable_token, row.unit);
      setContent(result.content);
      selection.current = { start: result.cursor, end: result.cursor };
      setNotice('已插入完整服务变量，导出读取矩阵的当前已确认值；本次修改仍须保存或提交。');
    } catch (error) { report(error); }
  }
  function insertProjectFact() {
    const fact = workspace.facts.find(item => item.id === factId);
    if (!held || combinedBusy || !fact) return;
    try {
      const range = selection.current ?? { start: content.length, end: content.length };
      const result = insertFactToken(content, range.start, range.end, fact);
      setContent(result.content); selection.current = { start: result.cursor, end: result.cursor };
      setNotice('已插入项目事实变量，导出读取当前已确认取值；本次修改仍须保存或提交。');
    } catch (error) { report(error); }
  }
  function keepLocalText() {
    const link = document.createElement('a');
    const url = URL.createObjectURL(new Blob([content], { type: 'text/plain;charset=utf-8' }));
    link.href = url; link.download = `${chapter?.title ?? '本节'}-未提交文字.txt`; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function deleteOwnDraft() {
    if (!chapter?.draft || combinedBusy) return;
    modal.confirm({ title: '明确删除本人已保存草稿', content: '只删除这个账号在本节已保存的个人草稿，不删除其他人草稿、正式正文或历史。当前编辑框的文字仍保留；需要的话请先保留一份本地文字。', okText: '删除本人草稿', cancelText: '保留草稿', onOk: async () => { await run(async () => {
      const start = epoch.current;
      await request(`/api/chapters/${chapterId}/draft`, token, 'DELETE', { sequence: chapter.draft!.sequence });
      const latest = await request<Chapter>(`/api/chapters/${chapterId}`, token);
      if (start !== epoch.current) return;
      setChapter(latest); sequence.current = latest.draft?.sequence ?? 0;
      setNotice('本人已保存草稿已删除，当前编辑框文字、正式正文和历史仍保留。'); await reload();
    }); } });
  }

  return <>
    <div className="editor-layout">
      <aside className="chapter-directory">
        <Radio.Group size="small" optionType="button" buttonStyle="solid" value={volume}
          onChange={e => { const next = e.target.value as Volume; selectChapter(workspace.chapters.find(item => item.volume === next)?.id ?? '', next); }}
          options={[{ value: 'technical', label: '技术分册' }, { value: 'business', label: '商务分册' }]} />
        <Input size="small" prefix={<FileTextOutlined />} placeholder="搜索章节" aria-label="搜索章节" value={search} onChange={e => setSearch(e.target.value)} />
        <div className="directory-label">章节目录</div>
        {workspace.chapters.filter(item => item.volume === volume && item.title.includes(search)).map(item =>
          <button className={`chapter-entry ${chapterId === item.id ? 'active' : ''}`} onClick={() => selectChapter(item.id)} key={item.id}>
            <span className={`chapter-dot ${item.content.trim() ? 'green-dot' : ''}`} /><span><b>{item.title}</b>
              <small>编写人：{item.assignee_name || '未分配'} · {item.writing_input?.is_current ? '方案已确认' : '方案待确认'}</small><small>{item.content.trim() ? `已提交 v${item.revision}` : '待编制'}{item.candidate ? item.candidate.status === 'stale' ? ' · 候选需重新生成' : ' · 有候选待确认' : ''}</small></span>
          </button>)}
        <div className="directory-bottom"><Button block size="small" onClick={() => setPlanOpen(true)} disabled={combinedBusy || !workspace.parse_confirmed}>写作方案与大纲确认</Button>
          <p className="muted">已确认方案 {workspace.chapters.filter(item => item.writing_input?.is_current).length} / {workspace.chapters.length} 节；每节独立办理</p><Tag color="orange">结构化段落编辑仍在后续任务中</Tag></div>
      </aside>
      <section className="editor-center">
        <div className="sla-token-tools">
          <Select aria-label="选择已确认项目事实" placeholder="选择已确认的项目事实" value={factId || undefined} onChange={setFactId}
            options={workspace.facts.filter(fact => fact.source_type !== 'sla').map(fact => ({ value: fact.id, label: `${fact.key} · ${fact.value}`, disabled: fact.status !== 'confirmed' }))} />
          <Button size="small" disabled={!held || combinedBusy || !factId || workspace.facts.find(fact => fact.id === factId)?.status !== 'confirmed'} onClick={insertProjectFact}>插入事实变量</Button>
          <small className="muted">事实变量读取已确认值；文字改动仍须提交</small>
        </div>
        {workspace.sla && <div className="sla-token-tools">
          <Select aria-label="选择已确认服务承诺变量" placeholder="选择已确认的服务变量" value={slaKey || undefined} onChange={setSlaKey}
            options={workspace.sla.rows.map(row => ({ value: row.var_key, label: `${row.label} · ${displaySlaValue(row.project_value, row.project_unit)}`, disabled: row.fact_status !== 'confirmed' || row.source_stale || workspace.sla?.template_stale }))} />
          <Button size="small" disabled={!held || combinedBusy || !slaKey || workspace.sla.template_stale || workspace.sla.rows.find(row => row.var_key === slaKey)?.fact_status !== 'confirmed'} onClick={insertVariable}>插入服务变量</Button>
          <small className="muted">导出使用矩阵当前值；变量按模板单位显示</small>
        </div>}
        <div className="editor-toolbar"><Space size={6}>
          <Tooltip title="正文格式与选区工具将在结构化编辑器中实现"><Button size="small" disabled>格式</Button></Tooltip>
          <Button size="small" icon={<HistoryOutlined />} onClick={viewVersions} disabled={combinedBusy || !chapter}>版本</Button>
          <Tooltip title="生成整章候选，不会直接改动正文"><Button size="small" onClick={generate} disabled={combinedBusy || !planCurrent || !canGenerate || !chapter}>生成候选</Button></Tooltip>
        </Space><Space size={6}>
          <Tag color={held ? 'green' : canEdit && chapter?.lock ? 'orange' : 'default'} icon={held ? <LockOutlined /> : <UnlockOutlined />}>{!canEdit ? '当前无本节编辑权限' : held ? '本人锁定' : chapter?.lock ? '他人 / 其他会话编辑中' : '未取得编辑权'}</Tag>
          {savedAt && <span className="saved-at">{savedAt} 已保存</span>}<Button type="primary" size="small" onClick={commit} disabled={combinedBusy || !held || !chapter} loading={busy}>提交本节</Button>
        </Space></div>
        <Spin spinning={loading}><div className="editor-scroll">
          {sourceAdvice && <Alert className="editor-notice" type="warning" showIcon message="取值由数据源决定，助手不能代改" action={<Space><Button size="small" onClick={() => navigate('facts')}>去项目事实表</Button><Button size="small" onClick={() => navigate('matrix')}>去服务承诺矩阵</Button></Space>} closable onClose={() => setSourceAdvice(false)} />}
          {sourceStale && <Alert className="editor-notice" type="warning" showIcon message={editFingerprint ? '当前文字依据的来源已经变化' : '当前草稿没有记录来源依据'} description="文字和原依据仍保留，不能直接视为采用了最新资料。请核对当前条款、事实和证据，再决定是否使用这些文字。" action={<Button size="small" disabled={combinedBusy} onClick={() => reviewCurrentSources('editor')}>核对最新来源</Button>} />}
        {notice && <Alert className="editor-notice" showIcon type={notice.includes('变化') || notice.includes('失败') || notice.includes('失效') ? 'warning' : 'info'} message={notice} closable onClose={() => setNotice('')} />}
          {chapter ? <article className="document-paper">
            <div className="document-heading"><h2>{chapter.title}</h2><Tag>{volumeName(chapter.volume)}</Tag></div>
            <p className="document-subline">本节编写人 {activeChapter?.assignee_name || '未指定'} · 正文版本 v{chapter.revision} · {sources.length} 条关联要求 · {!canEdit ? '只读，请核对本节分工' : held ? '已取得编辑权' : '只读，请先取得编辑权'}</p>
            {sources.length > 0 && <div className="chapter-source-summary"><span className="source-label">招标原文</span><div>{sources.map(item => <p key={item.id}>{item.text} <Tag>P.{item.source.page}</Tag></p>)}</div></div>}
            <Input.TextArea className="chapter-editor" aria-label="章节正文" placeholder="根据招标原文、项目事实和可引用证据编制正文。不要把未经核实的承诺直接写入。"
              autoSize={{ minRows: 18, maxRows: 35 }} value={content}
              onSelect={e => { const target = e.currentTarget; selection.current = { start: target.selectionStart, end: target.selectionEnd }; }}
              onChange={e => { selection.current = { start: e.target.selectionStart, end: e.target.selectionEnd }; setContent(e.target.value); }} readOnly={!held || combinedBusy} />
            <div className="document-footer"><span className="muted">{content.length} 字 · {modified ? '当前内容未全部提交' : '与已提交正文一致'}</span><Space>
              <Button size="small" onClick={keepLocalText} disabled={!content}>保留当前文字到本地</Button><Button size="small" icon={<SaveOutlined />} onClick={saveDraft} disabled={combinedBusy || !held}>保存草稿</Button>
              {held ? <Button size="small" onClick={release} disabled={combinedBusy}>释放编辑权</Button> : <Button size="small" type="primary" icon={<LockOutlined />} onClick={() => acquire()} disabled={combinedBusy || !canEdit}>取得编辑权</Button>}
              {!held && chapter.lock && chapterCan(activeChapter, 'takeover') && <Button size="small" danger onClick={takeover} disabled={combinedBusy}>填写理由接管</Button>}
            </Space></div>
            {chapter.draft && <Button size="small" danger disabled={combinedBusy} onClick={deleteOwnDraft}>明确删除本人已保存草稿</Button>}
            {chapter.draft && chapter.draft.base_revision !== chapter.revision && <Card size="small" title={`旧草稿（基于 v${chapter.draft.base_revision}，未自动覆盖）`}
              extra={<Button size="small" disabled={combinedBusy || !held} onClick={() => reviewRecovery({ title: `旧草稿 v${chapter.draft!.base_revision}`, content: chapter.draft!.content, source_kind: 'draft', input_fingerprint: chapter.draft!.input_fingerprint ?? null })}>核对并恢复</Button>} className="old-draft"><pre>{chapter.draft.content}</pre></Card>}
          </article> : <Empty description="当前分册没有可编辑章节" />}
        </div></Spin>
      </section>
      <aside className="editor-right">
        <Tabs size="small" activeKey={rightTab} onChange={setRightTab} items={[{ key: 'assistant', label: '对话助手' }, { key: 'issues', label: '问题' }, { key: 'sources', label: '写作来源' }]} />
        <div className="assistant-scroll">
          {rightTab === 'assistant' && <>
            <div className="model-label"><Tag color="purple">演示建议</Tag><span>整章候选 · 人工确认后才写入</span></div>
            {workspace.project.sensitive && <Alert type="info" message="敏感项目 · 只使用本地服务" />}
            <Card size="small" className="instruction-card"><span className="muted">当前章节 · {chapter?.title}</span><p>{instruction}</p></Card>
            {candidate ? <Card size="small" className="suggestion-card" title={<Space wrap><Tag color="purple">整章候选</Tag><span>基于 v{candidate.base_revision}</span></Space>}>
              {candidateIssue && <Alert type="warning" showIcon message="候选已失效，暂不能写入" description={candidateIssue} className="page-notice" />}
              <p className="suggestion-content">{candidate.content}</p>
              <Alert type="info" showIcon message={candidate.is_real_model ? '模型建议仍须人工核对' : '当前为演示建议，不代表真实模型已接入'} />
              <p className="muted">先核对当次输入，再比较整章内容；写入后仍需提交本节。</p><p className="muted">已校验输入状态、变量和单位；完整事实语义、段落来源和选区预检仍待完成。</p>
              <Space wrap><Button size="small" onClick={() => setInputOpen(true)}>查看当次输入来源</Button>
                <Button type="primary" size="small" disabled={combinedBusy || !held || !chapter || !!candidateIssue} onClick={() => showDiff(candidate)}>查看差异并确认写入</Button></Space>
            </Card> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="先确认写作方案，生成整章候选或取得整章修改建议" />}
          </>}
          {rightTab === 'sources' && <WritingSources key={chapterId} chapterId={chapterId} candidate={candidate} />}
          {rightTab === 'issues' && <>
            {workspace.checks[workspace.checks.length - 1]?.issues.filter(item => item.chapter_id === chapterId).map(item => <Alert key={item.id} className="page-notice" type={item.severity === 'warning' ? 'warning' : 'error'} message={`${item.code} · ${item.message}`} />) ?? <Empty description="请提交正文后运行检查" />}
            <Alert type="info" message="问题依据当前检查批次；未提交内容尚未检查" />
          </>}
        </div>
        {rightTab === 'assistant' && <div className="assistant-input">
          <div className="prompt-chips">{['改写', '扩写', '缩写', '按指令修改', '换一种说法'].map(text => <button key={text} onClick={() => setInstruction(`${text}当前章节，依据已核对原文与事实，不新增未经证实的承诺。`)}>{text}</button>)}</div>
          <Input.TextArea aria-label="给助手的修改要求" placeholder="针对已提交正文输入整章修改要求" rows={3} maxLength={2000} value={instruction} onChange={e => setInstruction(e.target.value)} disabled={combinedBusy || !canEdit} />
          <div className="assistant-send"><span className="muted">整章建议 · 选区助手待实现</span><Button size="small" type="primary" icon={<SendOutlined />}
            disabled={combinedBusy || !canGenerate || !chapter || !planCurrent || !instruction.trim() || modified} onClick={suggest}>发送</Button></div>
          {modified && <span className="muted">先提交本节，再基于已提交正文请求建议</span>}
          {!planCurrent && <span className="muted">先由本节编写人或负责人确认本节方案，再请求整章建议</span>}
        </div>}
      </aside>
    </div>
    <Modal title="写入确认 · 整章建议差异" cancelText="放弃这次写入" width={960} open={!!diff} onCancel={() => setDiff(null)} onOk={apply} okText="确认写入当前草稿"
      okButtonProps={{ disabled: !held || combinedBusy || !reviewed || !chapter || !diff || !!candidateProblem(diff, workspace.input_fingerprint, chapter.revision) }}>
      <div className="diff-description"><Tag color="purple">{diff?.is_real_model ? '模型建议' : '演示建议'}</Tag>将替换当前整章编辑内容；保存草稿不会提交正文，提交本节后才用于检查和导出。</div>
      <div className="diff-columns"><div><h4>当前内容</h4><pre className="diff-before">{content || '（空正文）'}</pre></div><div><h4>建议写入</h4><pre className="diff-after">{diff?.content}</pre></div></div>
      <label className="review-checkbox"><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} /> 我已逐字核对原文、证据和承诺，并确认整章修改合理</label>
    </Modal>
    <Drawer title="当次写作输入 · 候选历史快照" open={inputOpen} onClose={() => setInputOpen(false)} width={760}>
      {candidateIssue && <Alert className="page-notice" showIcon type="warning" message="候选已失效；下方仍保留生成时的输入供核对" />}
      <WritingInputPreviewContent snapshot={candidate?.input_snapshot} historical />
    </Drawer>
    <Drawer title="正式版本记录" open={versionsOpen} onClose={() => setVersionsOpen(false)} width={680}>
      {versions.length ? versions.map(item => <Card size="small" className="version-card" title={`正文 v${item.revision}`} extra={formatTime(item.created_at)} key={item.revision}>
        <p className="muted">提交账号：{item.actor_id}</p><pre>{item.content}</pre><Button size="small" disabled={combinedBusy || !held || item.revision === chapter?.revision} onClick={() => reviewRecovery({ title: `历史正文 v${item.revision}`, content: item.content, source_kind: 'history', input_fingerprint: workspace.input_fingerprint })}>核对并恢复为草稿</Button>
      </Card>) : <Empty description="暂无已提交版本" />}<Alert type="info" message="历史版本保留不变。恢复先保存个人草稿，人工修订并提交后才产生新正文版本。" />
    </Drawer>
    <RecoveryReview choice={recovery} current={content} reviewed={recoveryReviewed} busy={busy} writable={held && !combinedBusy && canEdit} onReview={setRecoveryReviewed} onCancel={() => setRecovery(null)} onSave={saveRecovery} onReviewSources={() => reviewCurrentSources('recovery')} />
    <WritingPlanReview chapterId={chapterId} open={planOpen} onClose={() => setPlanOpen(false)} />
    <Drawer title="核对最新来源 · 更新这次文字的写作依据" open={!!sourceReview} onClose={() => setSourceReview(null)} width={760} zIndex={1200}
      footer={<Space wrap><Checkbox checked={sourceReviewed} onChange={event => setSourceReviewed(event.target.checked)}>我已核对当前来源，并确认待保存文字仍然适用</Checkbox><Button size="small" disabled={combinedBusy} onClick={() => sourceReview && reviewCurrentSources(sourceReview.target)}>重新读取来源</Button><Button type="primary" loading={busy} disabled={!sourceReviewed || combinedBusy || !held || !canEdit} onClick={confirmCurrentSources}>按已核对来源更新依据</Button></Space>}>
      <Alert className="page-notice" showIcon type="warning" message="这一步只更新本次文字的写作依据，不会修改原文、事实、服务承诺或正式正文" description="先取得编辑权再确认。确认期间如果来源或正文又有变化，仍会拒绝更新；确认后也须人工修订，再保存草稿或提交。" />
      {sourceReview && <WritingInputPreviewContent snapshot={sourceReview.preview.input_snapshot} historical={false} />}
    </Drawer>
  </>;
}
