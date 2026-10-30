// 为什么有这个文件：保留示例的章节目录、正文和助手三栏编辑流程。
// 它解决什么问题：编辑权、旧草稿、正式版本与建议确认都以后台实际校验为准。
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Alert, App as AntApp, Button, Card, Drawer, Empty, Input, Modal, Progress, Space, Spin, Tag, Tooltip } from 'antd';
import {
  HistoryOutlined,
  LockOutlined,
  SaveOutlined,
  UnlockOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  BarsOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons';
import { ApiError, request } from '../shared/api.ts';
import { useProject, volumeName } from '../app/context.tsx';
import type { Candidate, Chapter, Volume, Workspace, WritingInputPreview } from '../shared/types.ts';
import { candidateProblem } from './writing-input.ts';
import { acquiredEditingFingerprint, editingContentWrite, loadedEditingFingerprint } from './editing-source.ts';
import { chapterCan } from '../project/project-team.ts';
import { AiTag, Cite, SourceBar } from '../library/BusinessTags.tsx';
import { ReadonlyBanner } from '../status/StatusViews';
import { useDataPermission } from '../shell/useDataPermission';
import { useVolumesStatus, isVolumeFinalized } from '../project/volume-api.ts';
import { OutlineTreeView } from '../project/OutlineTreeView';
import { ChapterTypeBadge } from '../project/ChapterTypeBadge';
import { mapChaptersToOutlineNodes, type ChapterOutlineNode } from '../project/outline-tree';
import { useBreakpoint } from '../shell/responsive';
import {
  calculateWordCount,
  isRevisionConflict,
  resolveConflictChoice,
  type ConflictContext,
  type WordCountInfo,
} from './editor-conflict';
import { CiteCapsule, RichParagraphWithCites } from './CiteCapsule';
import { SelectionBubble } from './SelectionBubble';
import { EditorAssistantPanel } from './EditorAssistantPanel.tsx';
import { SelectionRewritePanel, type RewriteSelection } from './SelectionRewritePanel.tsx';
import { pasteNotice, type PastedParagraph } from './paste-notice.ts';
import type { ApplyResult } from './selection-rewrite-core.ts';
import { EditorDiffDrawer, type ChapterVersionItem } from './EditorDiffDrawer.tsx';
import { extractCitationIds, type CiteKind, type CitationMeta } from './cite-capsule';
import { useEditorLock, type Lease } from './useEditorLock.ts';
import { SystemChapterPanel } from '../project/SystemChapterPanel.tsx';
import { systemChapterKind } from '../project/system-chapter-core.ts';
import { useSelectionBubble } from './useSelectionBubble.ts';
import { EditorSlaTools } from './EditorSlaTools.tsx';
import { EditorAuxiliaryDrawers } from './EditorAuxiliaryDrawers.tsx';
import { useEditorOperations } from './useEditorOperations.ts';
import { IDLE_SAVE_MS, editorTimings, savedLabel, shouldAutosave, type EditorTimings } from './autosave-core.ts';

export default function EditorPage({ onDirtyChange, initialChapterId }: { onDirtyChange: (dirty: boolean) => void; initialChapterId?: string }) {
  const { workspace, user, token, busy: projectBusy, mutate, reload, report, navigate } = useProject();
  const { modal } = AntApp.useApp();
  const breakpoint = useBreakpoint();
  const [directoryCollapsed, setDirectoryCollapsed] = useState(false);
  const [assistantCollapsed, setAssistantCollapsed] = useState(false);
  const [outlineDrawerOpen, setOutlineDrawerOpen] = useState(false);
  const [volume, setVolume] = useState<Volume>('technical');
  const [chapterId, setChapterId] = useState(() => {
    if (initialChapterId && workspace.chapters.some(item => item.id === initialChapterId)) return initialChapterId;
    return workspace.chapters.find(item => item.volume === 'technical')?.id ?? workspace.chapters[0]?.id ?? '';
  });
  useEffect(() => {
    if (initialChapterId && workspace.chapters.some(item => item.id === initialChapterId)) setChapterId(initialChapterId);
  }, [initialChapterId, workspace.chapters]);

  const [chapter, setChapter] = useState<Chapter | null>(null);
  const { volumes: volumesStatus } = useVolumesStatus(workspace.project.id, token, workspace.revision);
  const isCurrentVolumeFinalized = isVolumeFinalized(volumesStatus, chapter?.volume);
  const [content, setContent] = useState('');
  const [editFingerprint, setEditFingerprint] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [rightTab, setRightTab] = useState('assistant');
  const [savedAt, setSavedAt] = useState('');
  const [notice, setNotice] = useState('');
  const [sourceAdvice, setSourceAdvice] = useState(false);
  const [versions, setVersions] = useState<ChapterVersionItem[]>([]);
  const [versionsOpen, setVersionsOpen] = useState(false);
  const [conflict, setConflict] = useState<ConflictContext | null>(null);
  const [, setHighlightedSourceId] = useState<string | null>(null);
  const [rewriteSelection, setRewriteSelection] = useState<RewriteSelection | null>(null);
  const [timings, setTimings] = useState<EditorTimings>(() => editorTimings(null));
  const [autosavePaused, setAutosavePaused] = useState(false);
  const autosaving = useRef(false);

  const epoch = useRef(0);
  const sequence = useRef(0);

  const activeChapter = workspace.chapters.find(item => item.id === chapterId);
  const dataPermission = useDataPermission({ volume, chapterId, chapter: activeChapter, workspace, role: user?.role, userId: user?.id });
  const systemKind = systemChapterKind(activeChapter?.title);
  const canEdit = chapterCan(activeChapter, 'edit') && dataPermission.canEdit && !systemKind;
  const isReadOnlyView = !canEdit || dataPermission.readOnly;
  const canGenerate = chapterCan(activeChapter, 'generate') && dataPermission.canEdit;
  const combinedBusy = busy || projectBusy || loading;
  const planCurrent = activeChapter?.writing_input?.is_current === true;

  // 1. 租约与心跳续期 Hook
  const lock = useEditorLock({ chapterId, token, canEdit, epoch, report, reload, setNotice, heartbeatMs: timings.heartbeatMs });
  useEffect(() => {
    // 自动保存、心跳、锁超时取公司设置（PRD §5.11.9、§6.9）；读不到时用平台默认值
    if (!user?.company_id || !token) return;
    request<Record<string, number>>(`/api/v1/companies/${encodeURIComponent(user.company_id)}/settings`, token)
      .then(value => setTimings(editorTimings(value))).catch(() => undefined);
  }, [user?.company_id, token]);
  const { lease, setLease, currentLease, held } = lock;

  // 2. 划词与交互气泡 Hook
  const bubble = useSelectionBubble({
    content,
    onPolish: () => {
      // 气泡传来的文字已去掉首尾空白；改写要用原始选区，才能对上正文中的字符位置
      setRightTab('assistant'); setAssistantCollapsed(false);
      const range = selection.current;
      const raw = range ? content.slice(range.start, range.end) : '';
      const picked = raw.trim() ? raw : (window.getSelection()?.toString() ?? '');
      setRewriteSelection(range && raw.trim() ? { text: raw, start: range.start, end: range.end } : { text: picked });
      setNotice('已在右侧“选区改写”载入选中的文字，选择修改方式后生成样例。');
    },
    onComplianceQa: text => {
      setRightTab('assistant'); setAssistantCollapsed(false);
      ops.setInstruction(`针对选区「${text.slice(0, 100)}${text.length > 100 ? '...' : ''}」进行合规性核对：核对是否与招标要求或服务承诺相冲突，是否存在不可核实承诺。`);
      setNotice('已将选区文本载入AI助手（合规问答模式）');
    },
  });
  const { selectionBubble, editorWrapperRef, selection, handleTextareaSelect, handleContainerMouseUp, handleBubblePolish, handleBubbleComplianceQa, handleBubbleClear } = bubble;

  async function run(action: () => Promise<void>) { setBusy(true); try { await action(); } catch (error) { localError(error); } finally { setBusy(false); } }

  // 3. 业务动作与操作流 Hook
  const ops = useEditorOperations({
    chapter, setChapter, content, setContent, editFingerprint, setEditFingerprint,
    chapterId, token, workspace, lease, held, canEdit, canGenerate, planCurrent, combinedBusy,
    epoch, sequence, selection, setSavedAt, setNotice, run, reload, mutate, report, modal,
  });

  const dirty = chapter ? content !== (chapter.draft?.base_revision === chapter.revision ? chapter.draft.content : chapter.content) : false;
  const modified = chapter ? content !== chapter.content : false;
  const targetLength = activeChapter?.writing_input?.target_length ?? chapter?.writing_input?.target_length ?? null;
  const wordCountInfo = useMemo(() => calculateWordCount(content, targetLength), [content, targetLength]);
  const outlineNodes = useMemo(() => mapChaptersToOutlineNodes(workspace.chapters, workspace.requirements), [workspace.chapters, workspace.requirements]);
  const candidate = ops.suggestion ?? activeChapter?.candidate ?? null;
  const candidateIssue = candidate ? candidateProblem(candidate, workspace.input_fingerprint, chapter?.revision) : null;
  const sources = workspace.requirements.filter(item => item.chapter_id === chapterId || activeChapter?.requirement_ids?.includes(item.id));
  const sourceStale = !!chapter && editFingerprint !== workspace.input_fingerprint;
  const detectedCitations = useMemo(() => extractCitationIds(content), [content]);

  const knownCitations = useMemo(() => {
    const map: Record<string, Partial<CitationMeta>> = {};
    workspace.requirements.forEach(req => {
      req.evidence_ids.forEach(evId => { map[evId] = { id: evId, kind: 'evidence', title: `关联证据 (${evId})`, code: evId, status: 'confirmed', quote: req.text }; });
      map[req.id] = { id: req.id, kind: 'evidence', title: req.text.slice(0, 30), code: req.id, status: req.status, quote: req.text, page: req.source?.page };
    });
    return map;
  }, [workspace.requirements]);

  function handleCiteClick(id: string, kind: CiteKind) {
    setRightTab('sources'); setHighlightedSourceId(id);
    setNotice(`已在右侧定位依据：${kind === 'evidence' ? '资料证据' : '方案片段'} [${kind === 'evidence' ? '证' : '片'}:${id}]`);
  }

  useEffect(() => { onDirtyChange(dirty); }, [dirty, onDirtyChange]);

  useEffect(() => {
    const start = ++epoch.current;
    setChapter(null); setContent(''); setEditFingerprint(null); selection.current = null; setRewriteSelection(null);
    lock.clearLease(); ops.resetChapterStates(); setSavedAt(''); setNotice(''); onDirtyChange(false); setAutosavePaused(false);
    if (!chapterId) return;
    setLoading(true);
    request<Chapter>(`/api/chapters/${chapterId}`, token).then(data => {
      if (start !== epoch.current) return;
      setChapter(data); sequence.current = data.draft?.sequence ?? 0;
      setEditFingerprint(loadedEditingFingerprint(data, workspace.input_fingerprint));
      if (data.draft && data.draft.base_revision !== data.revision) {
        setContent(data.content); setNotice('存在基于旧版本的个人草稿。当前先展示新版本正文，旧草稿没有自动覆盖。');
      } else {
        setContent(data.draft?.content ?? data.content); if (data.draft) setNotice('已恢复当前版本的个人草稿，提交本节后才进入正式正文和导出。');
      }
    }).catch(error => { if (start === epoch.current) report(error); }).finally(() => { if (start === epoch.current) setLoading(false); });
    return () => { ++epoch.current; void lock.releaseLock(chapterId).catch(() => undefined); };
  }, [chapterId, token]);

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
    if (typeof isRevisionConflict === 'function' && isRevisionConflict(error)) {
      if (typeof handleRevisionConflict === 'function') void handleRevisionConflict(error, 'draft');
    }
  }

  async function handleRevisionConflict(error: unknown, target: 'draft' | 'commit' = 'draft') {
    if (!isRevisionConflict(error)) return false;
    try {
      const latest = await request<Chapter>(`/api/chapters/${chapterId}`, token);
      setConflict({ localContent: content, remoteContent: latest.content, remoteRevision: latest.revision, baseRevision: chapter?.revision ?? 0, target });
      return true;
    } catch (e) {
      report(e); setNotice('后台正文或草稿已变化，本次写入未成功。请核对最新版本。'); return false;
    }
  }

  async function applyConflictResolution(action: 'overwrite' | 'discard') {
    if (!conflict || !chapter) return;
    const resolved = resolveConflictChoice(action, conflict);
    if (action === 'overwrite') {
      if (!lease || !held) { setNotice('保留本地覆盖前请先取得编辑权。'); return; }
      await run(async () => {
        const latest = await request<Chapter>(`/api/chapters/${chapterId}`, token);
        const updated = { ...latest, revision: conflict.remoteRevision };
        setChapter(updated);
        const value = await request<NonNullable<Chapter['draft']>>(`/api/chapters/${chapterId}/draft`, token, 'PUT', {
          lease_token: lease.lease_token, base_revision: conflict.remoteRevision, sequence: ++sequence.current, ...editingContentWrite(conflict.localContent, editFingerprint),
        });
        setChapter({ ...updated, draft: value }); setEditFingerprint(value.input_fingerprint ?? null);
        setSavedAt(new Date().toLocaleTimeString('zh-CN', { hour12: false }));
        setNotice(`内容冲突已合并：${resolved.message}`); setConflict(null);
      });
    } else {
      setContent(conflict.remoteContent); setChapter({ ...chapter, content: conflict.remoteContent, revision: conflict.remoteRevision });
      setNotice(`内容冲突已合并：${resolved.message}`); setConflict(null); void reload().catch(report);
    }
  }

  async function acquire(reason: string | null = null) {
    if (!canEdit || combinedBusy) return;
    await run(async () => {
      const start = epoch.current;
      const result = await lock.acquireLock(reason);
      if (start !== epoch.current) return;
      const latest = await request<Chapter>(`/api/chapters/${chapterId}`, token);
      if (start !== epoch.current) return;
      if (chapter && latest.revision !== chapter.revision && modified) {
        setNotice('取得编辑权时发现新版本。当前文字未被清除，请先查看最新版本，核对后再编辑。');
        await lock.releaseLock(); return;
      }
      setChapter(latest); sequence.current = latest.draft?.sequence ?? sequence.current;
      if (!modified) setContent(latest.draft?.base_revision === latest.revision ? latest.draft.content : latest.content);
      setEditFingerprint(acquiredEditingFingerprint(editFingerprint, latest, modified));
      setNotice('已取得编辑权。其他账号会被后台阻止写入。');
    });
  }

  function takeover() {
    let reason = '';
    modal.confirm({
      title: '说明接管编辑的理由',
      content: <Input.TextArea aria-label="接管理由" placeholder="接管会使原编辑人的凭据失效，原因将留在操作记录中" onChange={e => { reason = e.target.value; }} />,
      okText: '填写理由并接管',
      onOk: async () => { if (!reason.trim()) throw new Error('请填写接管理由'); await acquire(reason); },
    });
  }

  async function release() {
    if (dirty) await autoSaveRef.current();
    await run(async () => {
      if (!lease) return;
      const before = chapter?.revision ?? 0;
      await lock.releaseLock();
      const latest = await request<Chapter>(`/api/chapters/${chapterId}`, token);
      setChapter(latest);
      if (latest.revision > before) { setContent(latest.content); setNotice(`已释放编辑权；已保存的草稿已自动提交为 v${latest.revision}。`); await reload(); }
    });
  }

  async function saveDraft() {
    if (!chapter || !lease || !canEdit) return;
    await run(async () => {
      const start = epoch.current;
      try {
        const value = await request<NonNullable<Chapter['draft']>>(`/api/chapters/${chapterId}/draft`, token, 'PUT', {
          lease_token: lease.lease_token, base_revision: chapter.revision, sequence: ++sequence.current, ...editingContentWrite(content, editFingerprint),
        });
        if (start !== epoch.current) return;
        setChapter({ ...chapter, draft: value }); setEditFingerprint(value.input_fingerprint ?? null);
        setSavedAt(new Date().toLocaleTimeString('zh-CN', { hour12: false })); setAutosavePaused(false);
        setNotice('个人草稿及对应来源依据已保存；尚未进入正式正文和导出。');
      } catch (error) {
        if (isRevisionConflict(error) && (await handleRevisionConflict(error, 'draft'))) return;
        throw error;
      }
    });
  }

  // 自动保存（APP-M2-T172）：停止输入 2 秒后、以及每隔公司设置的间隔，把手改保存为本人草稿；不提交为版本、不进入导出。
  // 失败时暂停自动保存并保留页面文字（来源变化、版本冲突按原规则提示），手动保存或提交成功后恢复。
  async function autoSaveDraft(): Promise<boolean> {
    if (!chapter || !lease || !canEdit) return false;
    if (!shouldAutosave({ held, dirty, saving: autosaving.current, paused: autosavePaused, busy: combinedBusy })) return !dirty;
    autosaving.current = true;
    const start = epoch.current;
    try {
      const value = await request<NonNullable<Chapter['draft']>>(`/api/chapters/${chapterId}/draft`, token, 'PUT', {
        lease_token: lease.lease_token, base_revision: chapter.revision, sequence: ++sequence.current, ...editingContentWrite(content, editFingerprint),
      });
      if (start !== epoch.current) return false;
      setChapter(prev => (prev ? { ...prev, draft: value } : prev)); setEditFingerprint(value.input_fingerprint ?? null);
      setSavedAt(savedLabel(new Date(), true));
      return true;
    } catch (error) {
      setAutosavePaused(true);
      if (isRevisionConflict(error) && (await handleRevisionConflict(error, 'draft'))) return false;
      localError(error);
      setNotice(current => current || '自动保存暂停：本次没有保存成功，文字仍在页面。请处理提示后手动保存草稿，成功后会恢复自动保存。');
      return false;
    } finally {
      autosaving.current = false;
    }
  }
  const autoSaveRef = useRef(autoSaveDraft);
  autoSaveRef.current = autoSaveDraft;
  useEffect(() => {
    if (!dirty || !held || autosavePaused) return;
    const timer = window.setTimeout(() => { void autoSaveRef.current(); }, IDLE_SAVE_MS);
    return () => window.clearTimeout(timer);
  }, [content, held, autosavePaused]);
  useEffect(() => {
    if (!held || autosavePaused) return;
    const timer = window.setInterval(() => { void autoSaveRef.current(); }, timings.autosaveMs);
    return () => window.clearInterval(timer);
  }, [held, autosavePaused, timings.autosaveMs]);

  async function commit() {
    if (!chapter || !lease || !canEdit) return;
    await run(async () => {
      const start = epoch.current;
      try {
        const committed = await request<{ paste_detected?: PastedParagraph[] | null }>(`/api/chapters/${chapterId}/versions`, token, 'POST', {
          lease_token: lease.lease_token, base_revision: chapter.revision, ...editingContentWrite(content, editFingerprint), idempotency_key: crypto.randomUUID(),
        });
        const updated = await request<Chapter>(`/api/chapters/${chapterId}`, token);
        const current = await request<Workspace>(`/api/v1/projects/${workspace.project.id}/workspace`, token);
        if (start !== epoch.current) return;
        setChapter(updated); setContent(updated.content); setEditFingerprint(current.input_fingerprint); ops.setSuggestion(null);
        sequence.current = updated.draft?.sequence ?? sequence.current; setSavedAt(new Date().toLocaleTimeString('zh-CN', { hour12: false }));
        setNotice(`已提交正文 v${updated.revision}；之前的检查和导出会失效，需要重新运行。${pasteNotice(committed.paste_detected)}`); setAutosavePaused(false);
        await reload();
      } catch (error) {
        if (isRevisionConflict(error) && (await handleRevisionConflict(error, 'commit'))) return;
        throw error;
      }
    });
  }

  async function viewVersions() {
    await run(async () => {
      const value = await request<{ versions: ChapterVersionItem[] }>(`/api/chapters/${chapterId}/versions`, token);
      setVersions(value.versions.slice().reverse()); setVersionsOpen(true);
    });
  }

  async function applyRewrite(result: ApplyResult) {
    const start = epoch.current;
    const updated = await request<Chapter>(`/api/chapters/${chapterId}`, token);
    const current = await request<Workspace>(`/api/v1/projects/${workspace.project.id}/workspace`, token);
    if (start !== epoch.current) return;
    setChapter(updated); setContent(updated.content); setEditFingerprint(current.input_fingerprint);
    sequence.current = updated.draft?.sequence ?? sequence.current; selection.current = null; setRewriteSelection(null);
    const issues = result.operation.recheck.issues.length;
    setNotice(`已按${result.operation.edit_mode_label}写入正文 v${result.revision}；改动段落复查${issues ? `发现 ${issues} 项问题，见右侧` : '未发现问题'}。之前的检查和导出会失效。`);
    await reload();
  }

  function selectChapter(id: string, nextVolume?: Volume) {
    const action = () => { if (nextVolume) setVolume(nextVolume); setChapterId(id); };
    const confirmLeave = () => modal.confirm({ title: '当前章节还有未保存文字', content: '自动保存没有成功。先保存草稿或提交本节，才能保证这些文字不丢失。', okText: '离开当前章节', cancelText: '继续编辑', onOk: action });
    if (!dirty) action();
    else if (held && !autosavePaused) void autoSaveRef.current().then(ok => { if (ok) action(); else confirmLeave(); });  // 切换前自动保存草稿（PRD §5.11.2）
    else confirmLeave();
  }

  return <>
    <div
      className={`editor-layout ${breakpoint.tier} ${directoryCollapsed ? 'directory-collapsed' : ''} ${assistantCollapsed ? 'assistant-collapsed' : ''}`}
      data-testid="editor-page-layout"
      data-breakpoint-tier={breakpoint.tier}
      data-editor-columns={breakpoint.editorColumns}
    >
      {/* 1. 左侧章节大纲树面板 */}
      {!directoryCollapsed && !breakpoint.isSubCompact ? (
        <aside className="chapter-directory chapter-directory-panel" data-testid="editor-directory-panel">
          <div className="directory-panel-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 4px', borderBottom: '1px solid #e8ebf0', marginBottom: 8 }}>
            <Space size={6}><UnorderedListOutlined style={{ color: '#1e4db7' }} /><span style={{ fontWeight: 600, fontSize: 13, color: '#1d2129' }}>章节大纲树</span></Space>
            <Tooltip title="收起大纲面板以扩大编辑区"><Button size="small" type="text" icon={<MenuFoldOutlined />} onClick={() => setDirectoryCollapsed(true)} data-testid="collapse-outline-btn" /></Tooltip>
          </div>
          <div className="directory-tree-scroll" style={{ flex: 1, overflow: 'auto' }}>
            <OutlineTreeView
              nodes={outlineNodes}
              activeVolume={volume}
              onVolumeChange={v => { const nextVol = v as Volume; selectChapter(workspace.chapters.find(c => c.volume === nextVol)?.id || '', nextVol); }}
              selectedChapterId={chapterId}
              onSelectChapter={node => selectChapter(node.id, node.volume as Volume)}
              onNavigateToEditor={id => selectChapter(id)}
            />
          </div>
          <div className="directory-bottom" style={{ marginTop: 'auto', paddingTop: 12 }}>
            <Button block size="small" onClick={() => ops.setPlanOpen(true)} disabled={combinedBusy || !workspace.parse_confirmed} data-testid="editor-open-plan-btn">写作方案与大纲确认</Button>
            <p className="muted" style={{ fontSize: 11, margin: '6px 0 0' }}>已确认方案 {workspace.chapters.filter(item => item.writing_input?.is_current).length} / {workspace.chapters.length} 节；每节独立办理</p>
          </div>
        </aside>
      ) : (
        <aside className="chapter-directory-collapsed-strip" data-testid="editor-directory-collapsed-strip">
          <Tooltip title="展开大纲树" placement="right"><Button size="small" type="text" icon={<MenuUnfoldOutlined />} onClick={() => { if (breakpoint.isSubCompact) setOutlineDrawerOpen(true); else setDirectoryCollapsed(false); }} data-testid="expand-outline-btn" /></Tooltip>
          <Tooltip title="以抽屉查看大纲树" placement="right"><Button size="small" type="text" icon={<BarsOutlined />} onClick={() => setOutlineDrawerOpen(true)} data-testid="open-outline-drawer-btn" /></Tooltip>
          <span style={{ writingMode: 'vertical-rl', fontSize: 12, color: '#4e5969', letterSpacing: 2, marginTop: 8 }}>大纲目录</span>
        </aside>
      )}

      {/* 2. 中间正文编辑区 */}
      <section className="editor-center" data-testid="editor-center-section">
        <EditorSlaTools workspace={workspace} factId={ops.factId} setFactId={ops.setFactId} slaKey={ops.slaKey} setSlaKey={ops.setSlaKey} held={held} combinedBusy={combinedBusy} onInsertFact={ops.insertProjectFact} onInsertVariable={ops.insertVariable} />

        <div className="editor-toolbar">
          <Space size={6}>
            {(directoryCollapsed || breakpoint.isSubCompact) && (
              <Tooltip title="展开大纲树"><Button size="small" icon={<BarsOutlined />} onClick={() => setOutlineDrawerOpen(true)} data-testid="toolbar-outline-drawer-btn">大纲</Button></Tooltip>
            )}
            <Tooltip title="正文格式与选区工具将在结构化编辑器中实现"><Button size="small" disabled>格式</Button></Tooltip>
            <Button size="small" icon={<HistoryOutlined />} onClick={viewVersions} disabled={combinedBusy || !chapter}>版本</Button>
            <Tooltip title="生成整章候选，不会直接改动正文"><Button size="small" onClick={ops.generate} disabled={combinedBusy || !planCurrent || !canGenerate || !chapter}>生成候选</Button></Tooltip>
          </Space>
          <Space size={6}>
            <Tag color={held ? 'green' : canEdit && chapter?.lock ? 'orange' : 'default'} icon={held ? <LockOutlined /> : <UnlockOutlined />}>{!canEdit ? '当前无本节编辑权限' : held ? '本人锁定' : chapter?.lock ? '他人 / 其他会话编辑中' : '未取得编辑权'}</Tag>
            {savedAt && <span className="saved-at" data-testid="editor-saved-at">{savedAt} 已保存</span>}
            {autosavePaused && held && <Tag color="orange" data-testid="autosave-paused-tag">自动保存已暂停</Tag>}
            {dirty && <Tag color="warning" data-testid="dirty-status-tag" icon={<SaveOutlined />}>未保存修改</Tag>}
            <Button size="small" icon={<SaveOutlined />} onClick={saveDraft} disabled={combinedBusy || !held || !dirty} type={dirty ? "dashed" : "default"} data-testid="toolbar-save-draft-btn">保存草稿{dirty ? ' *' : ''}</Button>
            <Button type="primary" size="small" onClick={commit} disabled={combinedBusy || !held || !chapter} loading={busy}>提交本节</Button>
            <Tooltip title={assistantCollapsed ? "展开对话助手" : "收起对话助手以扩展编辑区"}>
              <Button size="small" type="text" icon={assistantCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />} onClick={() => setAssistantCollapsed(!assistantCollapsed)} data-testid="toggle-assistant-btn">
                {assistantCollapsed ? '展开助手' : '收起助手'}
              </Button>
            </Tooltip>
          </Space>
        </div>

        <Spin spinning={loading}><div className="editor-scroll">
          {sourceAdvice && <Alert className="editor-notice" type="warning" showIcon message="取值由数据源决定，助手不能代改" action={<Space><Button size="small" onClick={() => navigate('facts')}>去项目事实表</Button><Button size="small" onClick={() => navigate('matrix')}>去服务承诺矩阵</Button></Space>} closable onClose={() => setSourceAdvice(false)} />}
          {sourceStale && <Alert className="editor-notice" type="warning" showIcon message={editFingerprint ? '当前文字依据的来源已经变化' : '当前草稿没有记录来源依据'} description="文字和原依据仍保留，不能直接视为采用了最新资料。请核对当前条款、事实和证据，再决定是否使用这些文字。" action={<Button size="small" disabled={combinedBusy} onClick={() => ops.reviewCurrentSources('editor')}>核对最新来源</Button>} />}
          {notice && <Alert className="editor-notice" showIcon type={notice.includes('变化') || notice.includes('失败') || notice.includes('失效') ? 'warning' : 'info'} message={notice} closable onClose={() => setNotice('')} />}

          {chapter ? <article className="document-paper" ref={editorWrapperRef} style={{ position: 'relative' }}>
            <SelectionBubble visible={selectionBubble.visible} position={selectionBubble.position} selectedText={selectionBubble.text} onPolish={handleBubblePolish} onComplianceQa={handleBubbleComplianceQa} onClear={handleBubbleClear} />
            {systemKind && activeChapter && <SystemChapterPanel chapterId={activeChapter.id} canGenerate={chapterCan(activeChapter, 'edit') && dataPermission.canEdit} />}
            {isReadOnlyView && !systemKind && <ReadonlyBanner banner reason={dataPermission.readOnlyReason || '当前章节处于只读浏览状态'} scope={dataPermission.scopeName || activeChapter?.title || volumeName(chapter.volume)} roleName={dataPermission.roleLabel} style={{ marginBottom: 16 }} />}
            <div className="document-heading">
              <h2>{chapter.title}</h2>
              <Tag>{volumeName(chapter.volume)}</Tag>
              {isCurrentVolumeFinalized ? <Tag color="success" data-testid="editor-volume-finalized-tag">分册已定稿</Tag> : <Tag color="default" data-testid="editor-volume-unfinalized-tag">分册编制中</Tag>}
            </div>
            <p className="document-subline">本节编写人 {activeChapter?.assignee_name || '未指定'} · 正文版本 v{chapter.revision} · {sources.length} 条关联要求 · {!canEdit ? '只读，请核对本节分工' : held ? '已取得编辑权' : '只读，请先取得编辑权'}</p>
            {sources.length > 0 && <div className="chapter-source-summary"><span className="source-label">招标原文</span><div>{sources.map(item => <p key={item.id}>{item.text} <Cite type="tender" marker={`P.${item.source.page}`} metadata={{ page: item.source.page, quote: item.text, title: '招标原文' }} /></p>)}</div></div>}
            <SourceBar kind="evidence" layout="bottom" sourceName={chapter.title} version={chapter.revision} fingerprint={editFingerprint} status={sourceStale ? 'stale' : 'confirmed'} onVerifySource={() => ops.reviewCurrentSources('editor')} />

            {isReadOnlyView ? (
              <div className="chapter-editor-readonly-view" data-testid="readonly-editor-view">
                <div className="chapter-editor-readonly-text" data-testid="readonly-editor-text" onMouseUp={handleContainerMouseUp} style={{ minHeight: 280, padding: 16, background: '#fafafa', border: '1px solid #e5e6eb', borderRadius: 4, whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: '#1d2129', lineHeight: 1.8, fontSize: 14 }}>
                  {content ? <RichParagraphWithCites content={content} knownCitations={knownCitations} onCiteClick={handleCiteClick} /> : <span className="muted" style={{ color: '#86909c' }}>（本章节暂无已提交正文）</span>}
                </div>
              </div>
            ) : !held ? (
              <div className="chapter-editor-unheld-view" data-testid="unheld-editor-view">
                <Alert type="info" showIcon message="当前未取得本节编辑锁" description="正文以纯文本方式呈现供浏览与校对。如需修改，请点击下方或工具栏的「取得编辑权」。" style={{ marginBottom: 12 }}
                  action={<Button size="small" type="primary" icon={<LockOutlined />} onClick={() => acquire()} disabled={combinedBusy || !canEdit} data-testid="unheld-acquire-btn">取得编辑权</Button>} />
                <div className="chapter-editor-unheld-text" data-testid="unheld-editor-text" onMouseUp={handleContainerMouseUp} style={{ minHeight: 280, padding: 16, background: '#fcfcfd', border: '1px dashed #d9d9d9', borderRadius: 4, whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: '#262626', lineHeight: 1.8, fontSize: 14 }}>
                  {content ? <RichParagraphWithCites content={content} knownCitations={knownCitations} onCiteClick={handleCiteClick} /> : <span className="muted" style={{ color: '#8c8c8c' }}>（本章节暂无正文内容）</span>}
                </div>
              </div>
            ) : (
              <div className="chapter-editor-editable-wrapper" style={{ position: 'relative' }}>
                <Input.TextArea className="chapter-editor" aria-label="章节正文" placeholder="根据招标原文、项目事实和可引用证据编制正文。不要把未经核实的承诺直接写入。" autoSize={{ minRows: 18, maxRows: 35 }} value={content} onSelect={e => { lock.markActivity(); handleTextareaSelect(e); }} onKeyDown={lock.markActivity} onMouseDown={lock.markActivity} onScroll={lock.markActivity} onChange={e => { lock.markActivity(); selection.current = { start: e.target.selectionStart, end: e.target.selectionEnd }; setContent(e.target.value); }} readOnly={!held || combinedBusy} />
                {detectedCitations.allIds.length > 0 && (
                  <div className="editor-citation-bar" data-testid="editor-citation-bar" style={{ marginTop: 8, padding: '8px 12px', background: '#f7f8fa', border: '1px solid #e5e6eb', borderRadius: 4, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 12, color: '#4e5969', fontWeight: 500 }}>正文引用依据 ({detectedCitations.allIds.length})：</span>
                    {detectedCitations.allIds.map(id => (<CiteCapsule key={id} id={id} type={detectedCitations.snippetIds.includes(id) ? 'snippet' : 'evidence'} meta={knownCitations[id]} onHighlightInSources={handleCiteClick} />))}
                  </div>
                )}
              </div>
            )}

            <div className="document-footer">
              <div className="document-footer-metrics" data-testid="editor-word-count" style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                <span className="muted" data-testid="word-count-text">{wordCountInfo.charCount} 字{wordCountInfo.targetLength ? ` / 目标 ${wordCountInfo.targetLength} 字` : ''} · {dirty ? '未保存修改' : modified ? '与已提交正文不一致' : '与已保存草稿/正文一致'}</span>
                {wordCountInfo.targetLength && wordCountInfo.targetLength > 0 ? (
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, minWidth: 160 }}>
                    <Progress percent={wordCountInfo.progressPercent} size="small" status={wordCountInfo.status === 'above_target' ? 'exception' : wordCountInfo.status === 'on_target' ? 'success' : 'active'} style={{ width: 100, margin: 0 }} data-testid="word-count-progress" />
                    <Tooltip title={wordCountInfo.hint}><Tag color={wordCountInfo.status === 'on_target' ? 'success' : wordCountInfo.status === 'above_target' ? 'warning' : 'default'} data-testid="word-count-status-tag">{wordCountInfo.label}</Tag></Tooltip>
                  </div>
                ) : null}
              </div>
              <Space>
                <Button size="small" onClick={ops.keepLocalText} disabled={!content}>保留当前文字到本地</Button>
                <Button size="small" type={dirty && held ? 'primary' : 'default'} icon={<SaveOutlined />} onClick={saveDraft} disabled={combinedBusy || !held || !dirty} data-testid="save-draft-btn">保存草稿{dirty ? ' *' : ''}</Button>
                {held ? <Button size="small" onClick={release} disabled={combinedBusy}>释放编辑权</Button> : <Button size="small" type="primary" icon={<LockOutlined />} onClick={() => acquire()} disabled={combinedBusy || !canEdit || isCurrentVolumeFinalized} title={isCurrentVolumeFinalized ? "当前分册已定稿锁定，如需修改请先解锁定稿" : undefined}>取得编辑权</Button>}
                {!held && chapter.lock && chapterCan(activeChapter, 'takeover') && <Button size="small" danger onClick={takeover} disabled={combinedBusy}>填写理由接管</Button>}
              </Space>
            </div>
            {chapter.draft && <Button size="small" danger disabled={combinedBusy} onClick={ops.deleteOwnDraft}>明确删除本人已保存草稿</Button>}
            {chapter.draft && chapter.draft.base_revision !== chapter.revision && <Card size="small" title={`旧草稿（基于 v${chapter.draft.base_revision}，未自动覆盖）`}
              extra={<Button size="small" disabled={combinedBusy || !held} onClick={() => ops.reviewRecovery({ title: `旧草稿 v${chapter.draft!.base_revision}`, content: chapter.draft!.content, source_kind: 'draft', input_fingerprint: chapter.draft!.input_fingerprint ?? null })}>核对并恢复</Button>} className="old-draft"><pre>{chapter.draft.content}</pre></Card>}
          </article> : <Empty description="当前分册没有可编辑章节" />}
        </div></Spin>
      </section>

      {/* 3. 右侧对话助手与面板 */}
      <EditorAssistantPanel
        rightTab={rightTab} setRightTab={setRightTab} candidate={candidate} candidateIssue={candidateIssue} instruction={ops.instruction} setInstruction={ops.setInstruction}
        combinedBusy={combinedBusy} held={held} canEdit={canEdit} canGenerate={canGenerate} chapter={chapter} planCurrent={planCurrent} modified={modified} workspace={workspace}
        chapterId={chapterId} onViewInput={() => ops.setInputOpen(true)} onShowDiff={ops.showDiff} onSuggest={ops.suggest}
        selectionTools={
          <SelectionRewritePanel projectId={workspace.project.id} chapter={chapter} content={content} selection={rewriteSelection}
            leaseToken={held && lease ? lease.lease_token : null} canGenerate={canEdit} busy={combinedBusy} token={token}
            onApplied={applyRewrite} onClear={() => setRewriteSelection(null)} report={report} />
        }
      />
    </div>

    {/* 4. 差异对比 Modal */}
    <Modal title="写入确认 · 整章建议差异" cancelText="放弃这次写入" width={960} open={!!ops.diff} onCancel={() => ops.setDiff(null)} onOk={ops.apply} okText="确认写入当前草稿"
      okButtonProps={{ disabled: !held || combinedBusy || !ops.reviewed || !chapter || !ops.diff || !!candidateProblem(ops.diff, workspace.input_fingerprint, chapter.revision) }}>
      <div className="diff-description"><AiTag variant={ops.diff?.is_real_model ? 'model' : 'demo'} />将替换当前整章编辑内容；保存草稿不会提交正文，提交本节后才用于检查和导出。</div>
      <div className="diff-columns"><div><h4>当前内容</h4><pre className="diff-before">{content || '（空正文）'}</pre></div><div><h4>建议写入</h4><pre className="diff-after">{ops.diff?.content}</pre></div></div>
      <label className="review-checkbox"><input type="checkbox" checked={ops.reviewed} onChange={e => ops.setReviewed(e.target.checked)} /> 我已逐字核对原文、证据和承诺，并确认整章修改合理</label>
    </Modal>

    {/* 5. 版本历史与差异对比抽屉 */}
    <EditorDiffDrawer open={versionsOpen} onClose={() => setVersionsOpen(false)} versions={versions} currentContent={content} currentRevision={chapter?.revision} combinedBusy={combinedBusy} held={held} inputFingerprint={workspace.input_fingerprint} onReviewRecovery={ops.reviewRecovery} />

    {/* 6. 辅助抽屉（方案、恢复、快照、来源核对） */}
    <EditorAuxiliaryDrawers
      chapterId={chapterId} candidate={candidate} candidateIssue={candidateIssue} inputOpen={ops.inputOpen} onCloseInput={() => ops.setInputOpen(false)}
      planOpen={ops.planOpen} onClosePlan={() => ops.setPlanOpen(false)} recovery={ops.recovery} recoveryReviewed={ops.recoveryReviewed}
      onReviewRecoveryChecked={ops.setRecoveryReviewed} onCancelRecovery={() => ops.setRecovery(null)} onSaveRecovery={ops.saveRecovery}
      onReviewSourcesForRecovery={() => ops.reviewCurrentSources('recovery')} sourceReview={ops.sourceReview} onCloseSourceReview={() => ops.setSourceReview(null)}
      sourceReviewed={ops.sourceReviewed} onSourceReviewedChange={ops.setSourceReviewed} onReloadSources={() => ops.sourceReview && ops.reviewCurrentSources(ops.sourceReview.target)}
      onConfirmSources={ops.confirmCurrentSources} content={content} busy={busy} combinedBusy={combinedBusy} held={held} canEdit={canEdit}
    />

    {/* 7. 章节大纲树抽屉 */}
    <Drawer title="章节大纲与目录树" open={outlineDrawerOpen} onClose={() => setOutlineDrawerOpen(false)} width={420} placement="left" data-testid="editor-outline-drawer">
      <OutlineTreeView
        nodes={outlineNodes} activeVolume={volume}
        onVolumeChange={v => { const nextVol = v as Volume; selectChapter(workspace.chapters.find(c => c.volume === nextVol)?.id || '', nextVol); }}
        selectedChapterId={chapterId} onSelectChapter={node => { selectChapter(node.id, node.volume as Volume); setOutlineDrawerOpen(false); }}
        onNavigateToEditor={id => { selectChapter(id); setOutlineDrawerOpen(false); }}
      />
    </Drawer>

    {/* 8. OCC 409 版本冲突检测与合并弹窗 */}
    <Modal
      title="409 版本冲突 · 内容已被其他成员修改" open={!!conflict} onCancel={() => setConflict(null)} width={880} data-testid="conflict-resolution-modal"
      footer={<Space>
        <Button onClick={() => setConflict(null)} data-testid="conflict-cancel-btn">稍后处理</Button>
        <Button danger onClick={() => applyConflictResolution('discard')} data-testid="conflict-discard-btn">放弃本地，采用远程最新 (v{conflict?.remoteRevision})</Button>
        <Button type="primary" onClick={() => applyConflictResolution('overwrite')} disabled={!held || combinedBusy} data-testid="conflict-overwrite-btn">保留本地修改并覆盖保存 (推进至 v{conflict?.remoteRevision})</Button>
      </Space>}
    >
      <Alert type="warning" showIcon message="检测到正文版本冲突 (OCC 409)" description={`您在保存草稿或提交时基于 v${conflict?.baseRevision}，但当前服务器已被更新为 v${conflict?.remoteRevision}。请对比双方内容后选择合并决策：`} style={{ marginBottom: 16 }} />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div>
          <h4 style={{ marginBottom: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}><span>您的本地内容（待保存）</span><Tag color="blue">本地</Tag></h4>
          <div data-testid="conflict-local-content" style={{ minHeight: 220, maxHeight: 360, overflowY: 'auto', padding: 12, background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: 4, whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: 13, lineHeight: 1.6 }}>{conflict?.localContent || '（空正文）'}</div>
        </div>
        <div>
          <h4 style={{ marginBottom: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}><span>服务器最新正文 (v{conflict?.remoteRevision})</span><Tag color="orange">远程最新</Tag></h4>
          <div data-testid="conflict-remote-content" style={{ minHeight: 220, maxHeight: 360, overflowY: 'auto', padding: 12, background: '#fffbe6', border: '1px solid #ffe58f', borderRadius: 4, whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: 13, lineHeight: 1.6 }}>{conflict?.remoteContent || '（空正文）'}</div>
        </div>
      </div>
      <p className="muted" style={{ marginTop: 12, fontSize: 12 }}>说明：「保留本地修改」将使用最新版本号覆盖并保存为您个人的草稿；「放弃本地」将使用远程最新正文替换当前编辑器内容。</p>
    </Modal>
  </>;
}
