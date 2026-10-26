// 为什么有这个文件：保留示例的章节目录、正文和助手三栏编辑流程。
// 它解决什么问题：编辑权、旧草稿、正式版本与建议确认都以后台实际校验为准。
import { useEffect, useMemo, useRef, useState } from 'react';
import { displaySlaValue, insertSlaMeasurement } from '../admin/sla-form';
import { Alert, App as AntApp, Button, Card, Checkbox, Drawer, Empty, Input, Modal, Progress, Radio, Select, Space, Spin, Tabs, Tag, Tooltip } from 'antd';
import {
  FileTextOutlined,
  HistoryOutlined,
  LockOutlined,
  SaveOutlined,
  SendOutlined,
  UnlockOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  BarsOutlined,
  UnorderedListOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { ApiError, request } from '../shared/api';
import { formatTime, useProject, volumeName } from '../app/context';
import type { Candidate, Chapter, Volume, Workspace, WritingInputPreview } from '../shared/types';
import { recoveryWrite } from './editor-recovery';
import RecoveryReview, { type RecoveryChoice } from './RecoveryReview';
import WritingPlanReview from './WritingPlanReview';
import WritingInputPreviewContent, { WritingSources } from './WritingInputPreview';
import { candidateProblem, insertFactToken } from './writing-input';
import { acquiredEditingFingerprint, editingContentWrite, loadedEditingFingerprint, recoveryEditingFingerprint, reviewedEditingFingerprint } from './editing-source';
import { chapterCan } from '../project/project-team';
import { AiTag, Cite, SourceBar } from '../library/BusinessTags';
import { ReadonlyBanner } from '../status/StatusViews';
import { useDataPermission } from '../shell/useDataPermission';
import { useVolumesStatus, isVolumeFinalized } from '../project/volume-api';
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
import { EditorAssistantPanel } from './EditorAssistantPanel';
import { EditorVersionsDrawer } from './EditorVersionsDrawer';
import { extractCitationIds, type CiteKind, type CitationMeta } from './cite-capsule';

type Lease = { lease_token: string; expires_at: string; owner_id: string };
type Version = { revision: number; content: string; actor_id: string; created_at: string };

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
    if (initialChapterId && workspace.chapters.some(item => item.id === initialChapterId)) {
      setChapterId(initialChapterId);
    }
  }, [initialChapterId]);
  const [chapter, setChapter] = useState<Chapter | null>(null);
  const { volumes: volumesStatus } = useVolumesStatus(workspace.project.id, token, workspace.revision);
  const isCurrentVolumeFinalized = isVolumeFinalized(volumesStatus, chapter?.volume);
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
  const [conflict, setConflict] = useState<ConflictContext | null>(null);
  const [highlightedSourceId, setHighlightedSourceId] = useState<string | null>(null);
  const [selectionBubble, setSelectionBubble] = useState<{
    visible: boolean;
    position: { top: number; left: number } | null;
    text: string;
  }>({ visible: false, position: null, text: '' });
  const editorWrapperRef = useRef<HTMLElement | null>(null);
  const epoch = useRef(0);
  const currentLease = useRef<Lease | null>(null);
  const currentId = useRef(chapterId);
  const sequence = useRef(0);
  const dirty = chapter ? content !== (chapter.draft?.base_revision === chapter.revision ? chapter.draft.content : chapter.content) : false;
  const modified = chapter ? content !== chapter.content : false;
  const combinedBusy = busy || projectBusy || loading;
  const activeChapter = workspace.chapters.find(item => item.id === chapterId);
  const targetLength = activeChapter?.writing_input?.target_length ?? chapter?.writing_input?.target_length ?? null;
  const wordCountInfo = useMemo(() => {
    return calculateWordCount(content, targetLength);
  }, [content, targetLength]);
  const outlineNodes = useMemo(() => {
    return mapChaptersToOutlineNodes(workspace.chapters, workspace.requirements);
  }, [workspace.chapters, workspace.requirements]);
  const dataPermission = useDataPermission({
    volume,
    chapterId,
    chapter: activeChapter,
    workspace,
    role: user?.role,
    userId: user?.id,
  });
  const canEdit = chapterCan(activeChapter, 'edit') && dataPermission.canEdit;
  const isReadOnlyView = !canEdit || dataPermission.readOnly;
  const canGenerate = chapterCan(activeChapter, 'generate') && dataPermission.canEdit;
  const planCurrent = activeChapter?.writing_input?.is_current === true;
  const held = canEdit && !!lease && Date.parse(lease.expires_at) > Date.now();
  const proposed = suggestion ?? workspace.chapters.find(item => item.id === chapterId)?.candidate ?? null;
  const candidate = proposed;
  const candidateIssue = candidate ? candidateProblem(candidate, workspace.input_fingerprint, chapter?.revision) : null;
  const sources = workspace.requirements.filter(item => item.chapter_id === chapterId || workspace.chapters.find(value => value.id === chapterId)?.requirement_ids?.includes(item.id));
  const sourceStale = !!chapter && editFingerprint !== workspace.input_fingerprint;

  const detectedCitations = useMemo(() => {
    return extractCitationIds(content);
  }, [content]);

  const knownCitations = useMemo(() => {
    const map: Record<string, Partial<CitationMeta>> = {};
    workspace.requirements.forEach(req => {
      req.evidence_ids.forEach(evId => {
        map[evId] = {
          id: evId,
          kind: 'evidence',
          title: `关联证据 (${evId})`,
          code: evId,
          status: 'confirmed',
          quote: req.text,
        };
      });
      map[req.id] = {
        id: req.id,
        kind: 'evidence',
        title: req.text.slice(0, 30),
        code: req.id,
        status: req.status,
        quote: req.text,
        page: req.source?.page,
      };
    });
    return map;
  }, [workspace.requirements]);

  function handleCiteClick(id: string, kind: CiteKind) {
    setRightTab('sources');
    setHighlightedSourceId(id);
    setNotice(`已在右侧定位依据：${kind === 'evidence' ? '资料证据' : '方案片段'} [${kind === 'evidence' ? '证' : '片'}:${id}]`);
  }

  const handleTextareaSelect = (e: React.SyntheticEvent<HTMLTextAreaElement>) => {
    const target = e.currentTarget;
    selection.current = { start: target.selectionStart, end: target.selectionEnd };
    const selText = content.slice(target.selectionStart, target.selectionEnd);
    if (selText.trim().length > 0) {
      const rect = target.getBoundingClientRect();
      const wrapperRect = editorWrapperRef.current?.getBoundingClientRect();
      const offsetTop = wrapperRect ? Math.max(10, rect.top - wrapperRect.top + 20) : 20;
      const offsetLeft = wrapperRect ? Math.max(120, rect.left - wrapperRect.left + 220) : 220;
      setSelectionBubble({
        visible: true,
        position: { top: offsetTop, left: offsetLeft },
        text: selText,
      });
    } else {
      setSelectionBubble(prev => ({ ...prev, visible: false }));
    }
  };

  const handleContainerMouseUp = () => {
    const winSel = window.getSelection();
    const selText = winSel?.toString() || '';
    if (selText.trim().length > 0) {
      const range = winSel?.getRangeAt(0);
      const rect = range?.getBoundingClientRect();
      const wrapperRect = editorWrapperRef.current?.getBoundingClientRect();
      if (rect && wrapperRect) {
        setSelectionBubble({
          visible: true,
          position: {
            top: Math.max(10, rect.top - wrapperRect.top - 8),
            left: Math.max(120, rect.left - wrapperRect.left + rect.width / 2),
          },
          text: selText,
        });
        return;
      }
    }
  };

  const handleBubblePolish = (selectedText: string) => {
    setRightTab('assistant');
    setAssistantCollapsed(false);
    setInstruction(`针对选区「${selectedText.slice(0, 100)}${selectedText.length > 100 ? '...' : ''}」进行AI润色：保持原文事实，优化文字表达，不新增未经核实的承诺。`);
    setNotice('已将选区文本载入AI助手（润色模式）');
    setSelectionBubble(prev => ({ ...prev, visible: false }));
  };

  const handleBubbleComplianceQa = (selectedText: string) => {
    setRightTab('assistant');
    setAssistantCollapsed(false);
    setInstruction(`针对选区「${selectedText.slice(0, 100)}${selectedText.length > 100 ? '...' : ''}」进行合规性核对：核对是否与招标要求或服务承诺相冲突，是否存在不可核实承诺。`);
    setNotice('已将选区文本载入AI助手（合规问答模式）');
    setSelectionBubble(prev => ({ ...prev, visible: false }));
  };

  const handleBubbleClear = () => {
    setSelectionBubble({ visible: false, position: null, text: '' });
    selection.current = null;
    if (window.getSelection) {
      window.getSelection()?.removeAllRanges();
    }
  };

  useEffect(() => { onDirtyChange(dirty); }, [dirty]);
  useEffect(() => {
    if (!canEdit && currentLease.current) {
      currentLease.current = null; setLease(null);
      setNotice('本节分工或项目权限已经变化，写入口已关闭。当前文字仍保留，可先保留一份本地文字，再核对最新分工。');
    }
  }, [canEdit]);
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
    if (typeof isRevisionConflict === 'function' && isRevisionConflict(error)) {
      if (typeof handleRevisionConflict === 'function') {
        void handleRevisionConflict(error, 'draft');
      }
      return;
    }
  }

  async function handleRevisionConflict(error: unknown, target: 'draft' | 'commit' = 'draft') {
    if (!isRevisionConflict(error)) return false;
    try {
      const latest = await request<Chapter>(`/api/chapters/${chapterId}`, token);
      setConflict({
        localContent: content,
        remoteContent: latest.content,
        remoteRevision: latest.revision,
        baseRevision: chapter?.revision ?? 0,
        target,
      });
      return true;
    } catch (e) {
      report(e);
      setNotice('后台正文或草稿已变化，本次写入未成功。请核对最新版本。');
      return false;
    }
  }

  async function applyConflictResolution(action: 'overwrite' | 'discard') {
    if (!conflict || !chapter) return;
    const resolved = resolveConflictChoice(action, conflict);
    if (action === 'overwrite') {
      if (!lease || !held) {
        setNotice('保留本地覆盖前请先取得编辑权。');
        return;
      }
      await run(async () => {
        const latest = await request<Chapter>(`/api/chapters/${chapterId}`, token);
        const updatedChapter = { ...latest, revision: conflict.remoteRevision };
        setChapter(updatedChapter);
        const value = await request<NonNullable<Chapter['draft']>>(`/api/chapters/${chapterId}/draft`, token, 'PUT', {
          lease_token: lease.lease_token,
          base_revision: conflict.remoteRevision,
          sequence: ++sequence.current,
          ...editingContentWrite(conflict.localContent, editFingerprint),
        });
        setChapter({ ...updatedChapter, draft: value });
        setEditFingerprint(value.input_fingerprint ?? null);
        setSavedAt(new Date().toLocaleTimeString('zh-CN', { hour12: false }));
        setNotice(`内容冲突已合并：${resolved.message}`);
        setConflict(null);
      });
    } else {
      setContent(conflict.remoteContent);
      setChapter({ ...chapter, content: conflict.remoteContent, revision: conflict.remoteRevision });
      setNotice(`内容冲突已合并：${resolved.message}`);
      setConflict(null);
      void reload().catch(report);
    }
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
  async function saveDraft() {
    if (!chapter || !lease || !canEdit) return;
    await run(async () => {
      const start = epoch.current;
      try {
        const value = await request<NonNullable<Chapter['draft']>>(`/api/chapters/${chapterId}/draft`, token, 'PUT', {
          lease_token: lease.lease_token,
          base_revision: chapter.revision,
          sequence: ++sequence.current,
          ...editingContentWrite(content, editFingerprint),
        });
        if (start !== epoch.current) return;
        setChapter({ ...chapter, draft: value });
        setEditFingerprint(value.input_fingerprint ?? null);
        setSavedAt(new Date().toLocaleTimeString('zh-CN', { hour12: false }));
        setNotice('个人草稿及对应来源依据已保存；尚未进入正式正文和导出。');
      } catch (error) {
        if (isRevisionConflict(error)) {
          const handled = await handleRevisionConflict(error, 'draft');
          if (handled) return;
        }
        throw error;
      }
    });
  }
  async function commit() {
    if (!chapter || !lease || !canEdit) return;
    await run(async () => {
      const start = epoch.current;
      try {
        await request(`/api/chapters/${chapterId}/versions`, token, 'POST', {
          lease_token: lease.lease_token,
          base_revision: chapter.revision,
          ...editingContentWrite(content, editFingerprint),
          idempotency_key: crypto.randomUUID(),
        });
        const updated = await request<Chapter>(`/api/chapters/${chapterId}`, token);
        const current = await request<Workspace>(`/api/v1/projects/${workspace.project.id}/workspace`, token);
        if (start !== epoch.current) return;
        setChapter(updated);
        setContent(updated.content);
        setEditFingerprint(current.input_fingerprint);
        setSuggestion(null);
        sequence.current = updated.draft?.sequence ?? sequence.current;
        setSavedAt(new Date().toLocaleTimeString('zh-CN', { hour12: false }));
        setNotice(`已提交正文 v${updated.revision}；之前的检查和导出会失效，需要重新运行。`);
        await reload();
      } catch (error) {
        if (isRevisionConflict(error)) {
          const handled = await handleRevisionConflict(error, 'commit');
          if (handled) return;
        }
        throw error;
      }
    });
  }
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
    <div
      className={`editor-layout ${breakpoint.tier} ${directoryCollapsed ? 'directory-collapsed' : ''} ${assistantCollapsed ? 'assistant-collapsed' : ''}`}
      data-testid="editor-page-layout"
      data-breakpoint-tier={breakpoint.tier}
      data-editor-columns={breakpoint.editorColumns}
    >
      {/* 1. 左侧章节大纲树面板（支持展开或收起为迷你竖条） */}
      {!directoryCollapsed && !breakpoint.isSubCompact ? (
        <aside className="chapter-directory chapter-directory-panel" data-testid="editor-directory-panel">
          <div
            className="directory-panel-header"
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '6px 4px',
              borderBottom: '1px solid #e8ebf0',
              marginBottom: 8,
            }}
          >
            <Space size={6}>
              <UnorderedListOutlined style={{ color: '#1e4db7' }} />
              <span style={{ fontWeight: 600, fontSize: 13, color: '#1d2129' }}>章节大纲树</span>
            </Space>
            <Tooltip title="收起大纲面板以扩大编辑区">
              <Button
                size="small"
                type="text"
                icon={<MenuFoldOutlined />}
                onClick={() => setDirectoryCollapsed(true)}
                data-testid="collapse-outline-btn"
              />
            </Tooltip>
          </div>

          <div className="directory-tree-scroll" style={{ flex: 1, overflow: 'auto' }}>
            <OutlineTreeView
              nodes={outlineNodes}
              activeVolume={volume}
              onVolumeChange={v => {
                const nextVol = v as Volume;
                const firstChapterInVolume = workspace.chapters.find(c => c.volume === nextVol)?.id || '';
                selectChapter(firstChapterInVolume, nextVol);
              }}
              selectedChapterId={chapterId}
              onSelectChapter={node => selectChapter(node.id, node.volume as Volume)}
              onNavigateToEditor={id => selectChapter(id)}
            />
          </div>

          <div className="directory-bottom" style={{ marginTop: 'auto', paddingTop: 12 }}>
            <Button
              block
              size="small"
              onClick={() => setPlanOpen(true)}
              disabled={combinedBusy || !workspace.parse_confirmed}
              data-testid="editor-open-plan-btn"
            >
              写作方案与大纲确认
            </Button>
            <p className="muted" style={{ fontSize: 11, margin: '6px 0 0' }}>
              已确认方案 {workspace.chapters.filter(item => item.writing_input?.is_current).length} / {workspace.chapters.length} 节；每节独立办理
            </p>
          </div>
        </aside>
      ) : (
        <aside
          className="chapter-directory-collapsed-strip"
          data-testid="editor-directory-collapsed-strip"
        >
          <Tooltip title="展开大纲树" placement="right">
            <Button
              size="small"
              type="text"
              icon={<MenuUnfoldOutlined />}
              onClick={() => {
                if (breakpoint.isSubCompact) {
                  setOutlineDrawerOpen(true);
                } else {
                  setDirectoryCollapsed(false);
                }
              }}
              data-testid="expand-outline-btn"
            />
          </Tooltip>
          <Tooltip title="以抽屉查看大纲树" placement="right">
            <Button
              size="small"
              type="text"
              icon={<BarsOutlined />}
              onClick={() => setOutlineDrawerOpen(true)}
              data-testid="open-outline-drawer-btn"
            />
          </Tooltip>
          <span style={{ writingMode: 'vertical-rl', fontSize: 12, color: '#4e5969', letterSpacing: 2, marginTop: 8 }}>
            大纲目录
          </span>
        </aside>
      )}

      {/* 2. 中间正文编辑区 */}
      <section className="editor-center" data-testid="editor-center-section">
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
        <div className="editor-toolbar">
          <Space size={6}>
            {(directoryCollapsed || breakpoint.isSubCompact) && (
              <Tooltip title="展开大纲树">
                <Button
                  size="small"
                  icon={<BarsOutlined />}
                  onClick={() => setOutlineDrawerOpen(true)}
                  data-testid="toolbar-outline-drawer-btn"
                >
                  大纲
                </Button>
              </Tooltip>
            )}
            <Tooltip title="正文格式与选区工具将在结构化编辑器中实现"><Button size="small" disabled>格式</Button></Tooltip>
            <Button size="small" icon={<HistoryOutlined />} onClick={viewVersions} disabled={combinedBusy || !chapter}>版本</Button>
            <Tooltip title="生成整章候选，不会直接改动正文"><Button size="small" onClick={generate} disabled={combinedBusy || !planCurrent || !canGenerate || !chapter}>生成候选</Button></Tooltip>
          </Space>
          <Space size={6}>
            <Tag color={held ? 'green' : canEdit && chapter?.lock ? 'orange' : 'default'} icon={held ? <LockOutlined /> : <UnlockOutlined />}>{!canEdit ? '当前无本节编辑权限' : held ? '本人锁定' : chapter?.lock ? '他人 / 其他会话编辑中' : '未取得编辑权'}</Tag>
            {savedAt && <span className="saved-at">{savedAt} 已保存</span>}
            {dirty && (
              <Tag color="warning" data-testid="dirty-status-tag" icon={<SaveOutlined />}>
                未保存
              </Tag>
            )}
            <Button
              size="small"
              icon={<SaveOutlined />}
              onClick={saveDraft}
              disabled={combinedBusy || !held || !dirty}
              type={dirty ? "dashed" : "default"}
              data-testid="toolbar-save-draft-btn"
            >
              保存草稿{dirty ? ' *' : ''}
            </Button>
            <Button type="primary" size="small" onClick={commit} disabled={combinedBusy || !held || !chapter} loading={busy}>提交本节</Button>
            <Tooltip title={assistantCollapsed ? "展开对话助手" : "收起对话助手以扩展编辑区"}>
              <Button
                size="small"
                type="text"
                icon={assistantCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                onClick={() => setAssistantCollapsed(!assistantCollapsed)}
                data-testid="toggle-assistant-btn"
              >
                {assistantCollapsed ? '展开助手' : '收起助手'}
              </Button>
            </Tooltip>
          </Space>
        </div>
        <Spin spinning={loading}><div className="editor-scroll">
          {sourceAdvice && <Alert className="editor-notice" type="warning" showIcon message="取值由数据源决定，助手不能代改" action={<Space><Button size="small" onClick={() => navigate('facts')}>去项目事实表</Button><Button size="small" onClick={() => navigate('matrix')}>去服务承诺矩阵</Button></Space>} closable onClose={() => setSourceAdvice(false)} />}
          {sourceStale && <Alert className="editor-notice" type="warning" showIcon message={editFingerprint ? '当前文字依据的来源已经变化' : '当前草稿没有记录来源依据'} description="文字和原依据仍保留，不能直接视为采用了最新资料。请核对当前条款、事实和证据，再决定是否使用这些文字。" action={<Button size="small" disabled={combinedBusy} onClick={() => reviewCurrentSources('editor')}>核对最新来源</Button>} />}
        {notice && <Alert className="editor-notice" showIcon type={notice.includes('变化') || notice.includes('失败') || notice.includes('失效') ? 'warning' : 'info'} message={notice} closable onClose={() => setNotice('')} />}
          {chapter ? <article className="document-paper" ref={editorWrapperRef} style={{ position: 'relative' }}>
            <SelectionBubble
              visible={selectionBubble.visible}
              position={selectionBubble.position}
              selectedText={selectionBubble.text}
              onPolish={handleBubblePolish}
              onComplianceQa={handleBubbleComplianceQa}
              onClear={handleBubbleClear}
            />
            {isReadOnlyView && (
              <ReadonlyBanner
                banner
                reason={dataPermission.readOnlyReason || '当前章节处于只读浏览状态'}
                scope={dataPermission.scopeName || activeChapter?.title || volumeName(chapter.volume)}
                roleName={dataPermission.roleLabel}
                style={{ marginBottom: 16 }}
              />
            )}
            <div className="document-heading">
              <h2>{chapter.title}</h2>
              <Tag>{volumeName(chapter.volume)}</Tag>
              {isCurrentVolumeFinalized ? (
                <Tag color="success" data-testid="editor-volume-finalized-tag">分册已定稿</Tag>
              ) : (
                <Tag color="default" data-testid="editor-volume-unfinalized-tag">分册编制中</Tag>
              )}
            </div>
            <p className="document-subline">本节编写人 {activeChapter?.assignee_name || '未指定'} · 正文版本 v{chapter.revision} · {sources.length} 条关联要求 · {!canEdit ? '只读，请核对本节分工' : held ? '已取得编辑权' : '只读，请先取得编辑权'}</p>
            {sources.length > 0 && <div className="chapter-source-summary"><span className="source-label">招标原文</span><div>{sources.map(item => <p key={item.id}>{item.text} <Cite type="tender" marker={`P.${item.source.page}`} metadata={{ page: item.source.page, quote: item.text, title: '招标原文' }} /></p>)}</div></div>}
            <SourceBar kind="evidence" layout="bottom" sourceName={chapter.title} version={chapter.revision} fingerprint={editFingerprint} status={sourceStale ? 'stale' : 'confirmed'} onVerifySource={() => reviewCurrentSources('editor')} />
            {isReadOnlyView ? (
              <div className="chapter-editor-readonly-view" data-testid="readonly-editor-view">
                <div
                  className="chapter-editor-readonly-text"
                  data-testid="readonly-editor-text"
                  onMouseUp={handleContainerMouseUp}
                  style={{
                    minHeight: 280,
                    padding: '16px',
                    background: '#fafafa',
                    border: '1px solid #e5e6eb',
                    borderRadius: 4,
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    color: '#1d2129',
                    lineHeight: 1.8,
                    fontSize: 14,
                  }}
                >
                  {content ? (
                    <RichParagraphWithCites
                      content={content}
                      knownCitations={knownCitations}
                      onCiteClick={handleCiteClick}
                    />
                  ) : (
                    <span className="muted" style={{ color: '#86909c' }}>（本章节暂无已提交正文）</span>
                  )}
                </div>
              </div>
            ) : !held ? (
              <div className="chapter-editor-unheld-view" data-testid="unheld-editor-view">
                <Alert
                  type="info"
                  showIcon
                  message="当前未取得本节编辑锁"
                  description="正文以纯文本方式呈现供浏览与校对。如需修改，请点击下方或工具栏的「取得编辑权」。"
                  style={{ marginBottom: 12 }}
                  action={
                    <Button
                      size="small"
                      type="primary"
                      icon={<LockOutlined />}
                      onClick={() => acquire()}
                      disabled={combinedBusy || !canEdit}
                      data-testid="unheld-acquire-btn"
                    >
                      取得编辑权
                    </Button>
                  }
                />
                <div
                  className="chapter-editor-unheld-text"
                  data-testid="unheld-editor-text"
                  onMouseUp={handleContainerMouseUp}
                  style={{
                    minHeight: 280,
                    padding: '16px',
                    background: '#fcfcfd',
                    border: '1px dashed #d9d9d9',
                    borderRadius: 4,
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    color: '#262626',
                    lineHeight: 1.8,
                    fontSize: 14,
                  }}
                >
                  {content ? (
                    <RichParagraphWithCites
                      content={content}
                      knownCitations={knownCitations}
                      onCiteClick={handleCiteClick}
                    />
                  ) : (
                    <span className="muted" style={{ color: '#8c8c8c' }}>（本章节暂无正文内容）</span>
                  )}
                </div>
              </div>
            ) : (
              <div className="chapter-editor-editable-wrapper" style={{ position: 'relative' }}>
                <Input.TextArea
                  className="chapter-editor"
                  aria-label="章节正文"
                  placeholder="根据招标原文、项目事实和可引用证据编制正文。不要把未经核实的承诺直接写入。"
                  autoSize={{ minRows: 18, maxRows: 35 }}
                  value={content}
                  onSelect={handleTextareaSelect}
                  onChange={e => {
                    selection.current = { start: e.target.selectionStart, end: e.target.selectionEnd };
                    setContent(e.target.value);
                  }}
                  readOnly={!held || combinedBusy}
                />
                {detectedCitations.allIds.length > 0 && (
                  <div
                    className="editor-citation-bar"
                    data-testid="editor-citation-bar"
                    style={{
                      marginTop: 8,
                      padding: '8px 12px',
                      background: '#f7f8fa',
                      border: '1px solid #e5e6eb',
                      borderRadius: 4,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      flexWrap: 'wrap',
                    }}
                  >
                    <span style={{ fontSize: 12, color: '#4e5969', fontWeight: 500 }}>
                      正文引用依据 ({detectedCitations.allIds.length})：
                    </span>
                    {detectedCitations.allIds.map(id => {
                      const isSnippet = detectedCitations.snippetIds.includes(id);
                      return (
                        <CiteCapsule
                          key={id}
                          id={id}
                          type={isSnippet ? 'snippet' : 'evidence'}
                          meta={knownCitations[id]}
                          onHighlightInSources={handleCiteClick}
                        />
                      );
                    })}
                  </div>
                )}
              </div>
            )}
            <div className="document-footer">
              <div
                className="document-footer-metrics"
                data-testid="editor-word-count"
                style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}
              >
                <span className="muted" data-testid="word-count-text">
                  {wordCountInfo.charCount} 字
                  {wordCountInfo.targetLength ? ` / 目标 ${wordCountInfo.targetLength} 字` : ''} · {dirty ? '未保存修改' : modified ? '与已提交正文不一致' : '与已保存草稿/正文一致'}
                </span>
                {wordCountInfo.targetLength && wordCountInfo.targetLength > 0 ? (
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, minWidth: 160 }}>
                    <Progress
                      percent={wordCountInfo.progressPercent}
                      size="small"
                      status={
                        wordCountInfo.status === 'above_target'
                          ? 'exception'
                          : wordCountInfo.status === 'on_target'
                          ? 'success'
                          : 'active'
                      }
                      style={{ width: 100, margin: 0 }}
                      data-testid="word-count-progress"
                    />
                    <Tooltip title={wordCountInfo.hint}>
                      <Tag
                        color={
                          wordCountInfo.status === 'on_target'
                            ? 'success'
                            : wordCountInfo.status === 'above_target'
                            ? 'warning'
                            : 'default'
                        }
                        data-testid="word-count-status-tag"
                      >
                        {wordCountInfo.label}
                      </Tag>
                    </Tooltip>
                  </div>
                ) : null}
              </div>
              <Space>
                <Button size="small" onClick={keepLocalText} disabled={!content}>保留当前文字到本地</Button>
                <Button
                  size="small"
                  type={dirty && held ? 'primary' : 'default'}
                  icon={<SaveOutlined />}
                  onClick={saveDraft}
                  disabled={combinedBusy || !held || !dirty}
                  data-testid="save-draft-btn"
                >
                  保存草稿{dirty ? ' *' : ''}
                </Button>
                {held ? <Button size="small" onClick={release} disabled={combinedBusy}>释放编辑权</Button> : <Button size="small" type="primary" icon={<LockOutlined />} onClick={() => acquire()} disabled={combinedBusy || !canEdit || isCurrentVolumeFinalized} title={isCurrentVolumeFinalized ? "当前分册已定稿锁定，如需修改请先解锁定稿" : undefined}>取得编辑权</Button>}
                {!held && chapter.lock && chapterCan(activeChapter, 'takeover') && <Button size="small" danger onClick={takeover} disabled={combinedBusy}>填写理由接管</Button>}
              </Space>
            </div>
            {chapter.draft && <Button size="small" danger disabled={combinedBusy} onClick={deleteOwnDraft}>明确删除本人已保存草稿</Button>}
            {chapter.draft && chapter.draft.base_revision !== chapter.revision && <Card size="small" title={`旧草稿（基于 v${chapter.draft.base_revision}，未自动覆盖）`}
              extra={<Button size="small" disabled={combinedBusy || !held} onClick={() => reviewRecovery({ title: `旧草稿 v${chapter.draft!.base_revision}`, content: chapter.draft!.content, source_kind: 'draft', input_fingerprint: chapter.draft!.input_fingerprint ?? null })}>核对并恢复</Button>} className="old-draft"><pre>{chapter.draft.content}</pre></Card>}
          </article> : <Empty description="当前分册没有可编辑章节" />}
        </div></Spin>
      </section>
      <EditorAssistantPanel
        rightTab={rightTab}
        setRightTab={setRightTab}
        candidate={candidate}
        candidateIssue={candidateIssue}
        instruction={instruction}
        setInstruction={setInstruction}
        combinedBusy={combinedBusy}
        held={held}
        canEdit={canEdit}
        canGenerate={canGenerate}
        chapter={chapter}
        planCurrent={planCurrent}
        modified={modified}
        workspace={workspace}
        chapterId={chapterId}
        onViewInput={() => setInputOpen(true)}
        onShowDiff={showDiff}
        onSuggest={suggest}
      />
    </div>
    <Modal title="写入确认 · 整章建议差异" cancelText="放弃这次写入" width={960} open={!!diff} onCancel={() => setDiff(null)} onOk={apply} okText="确认写入当前草稿"
      okButtonProps={{ disabled: !held || combinedBusy || !reviewed || !chapter || !diff || !!candidateProblem(diff, workspace.input_fingerprint, chapter.revision) }}>
      <div className="diff-description"><AiTag variant={diff?.is_real_model ? 'model' : 'demo'} />将替换当前整章编辑内容；保存草稿不会提交正文，提交本节后才用于检查和导出。</div>
      <div className="diff-columns"><div><h4>当前内容</h4><pre className="diff-before">{content || '（空正文）'}</pre></div><div><h4>建议写入</h4><pre className="diff-after">{diff?.content}</pre></div></div>
      <label className="review-checkbox"><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} /> 我已逐字核对原文、证据和承诺，并确认整章修改合理</label>
    </Modal>
    <Drawer title="当次写作输入 · 候选历史快照" open={inputOpen} onClose={() => setInputOpen(false)} width={760}>
      {candidateIssue && <Alert className="page-notice" showIcon type="warning" message="候选已失效；下方仍保留生成时的输入供核对" />}
      <WritingInputPreviewContent snapshot={candidate?.input_snapshot} historical />
    </Drawer>
    <EditorVersionsDrawer
      open={versionsOpen}
      onClose={() => setVersionsOpen(false)}
      versions={versions}
      combinedBusy={combinedBusy}
      held={held}
      currentRevision={chapter?.revision}
      inputFingerprint={workspace.input_fingerprint}
      onReviewRecovery={reviewRecovery}
    />
    <RecoveryReview choice={recovery} current={content} reviewed={recoveryReviewed} busy={busy} writable={held && !combinedBusy && canEdit} onReview={setRecoveryReviewed} onCancel={() => setRecovery(null)} onSave={saveRecovery} onReviewSources={() => reviewCurrentSources('recovery')} />
    <WritingPlanReview chapterId={chapterId} open={planOpen} onClose={() => setPlanOpen(false)} />
    <Drawer title="核对最新来源 · 更新这次文字的写作依据" open={!!sourceReview} onClose={() => setSourceReview(null)} width={760} zIndex={1200}
      footer={<Space wrap><Checkbox checked={sourceReviewed} onChange={event => setSourceReviewed(event.target.checked)}>我已核对当前来源，并确认待保存文字仍然适用</Checkbox><Button size="small" disabled={combinedBusy} onClick={() => sourceReview && reviewCurrentSources(sourceReview.target)}>重新读取来源</Button><Button type="primary" loading={busy} disabled={!sourceReviewed || combinedBusy || !held || !canEdit} onClick={confirmCurrentSources}>按已核对来源更新依据</Button></Space>}>
      <Alert className="page-notice" showIcon type="warning" message="这一步只更新本次文字的写作依据，不会修改原文、事实、服务承诺或正式正文" description="先取得编辑权再确认。确认期间如果来源或正文又有变化，仍会拒绝更新；确认后也须人工修订，再保存草稿或提交。" />
      {sourceReview && <WritingInputPreviewContent snapshot={sourceReview.preview.input_snapshot} historical={false} />}
    </Drawer>
    <Drawer
      title="章节大纲与目录树"
      open={outlineDrawerOpen}
      onClose={() => setOutlineDrawerOpen(false)}
      width={420}
      placement="left"
      data-testid="editor-outline-drawer"
    >
      <OutlineTreeView
        nodes={outlineNodes}
        activeVolume={volume}
        onVolumeChange={v => {
          const nextVol = v as Volume;
          const firstChapterInVolume = workspace.chapters.find(c => c.volume === nextVol)?.id || '';
          selectChapter(firstChapterInVolume, nextVol);
        }}
        selectedChapterId={chapterId}
        onSelectChapter={node => {
          selectChapter(node.id, node.volume as Volume);
          setOutlineDrawerOpen(false);
        }}
        onNavigateToEditor={id => {
          selectChapter(id);
          setOutlineDrawerOpen(false);
        }}
      />
    </Drawer>
    <Modal
      title="409 版本冲突 · 内容已被其他成员修改"
      open={!!conflict}
      onCancel={() => setConflict(null)}
      footer={
        <Space>
          <Button
            onClick={() => setConflict(null)}
            data-testid="conflict-cancel-btn"
          >
            稍后处理
          </Button>
          <Button
            danger
            onClick={() => applyConflictResolution('discard')}
            data-testid="conflict-discard-btn"
          >
            放弃本地，采用远程最新 (v{conflict?.remoteRevision})
          </Button>
          <Button
            type="primary"
            onClick={() => applyConflictResolution('overwrite')}
            disabled={!held || combinedBusy}
            data-testid="conflict-overwrite-btn"
          >
            保留本地修改并覆盖保存 (推进至 v{conflict?.remoteRevision})
          </Button>
        </Space>
      }
      width={880}
      data-testid="conflict-resolution-modal"
    >
      <Alert
        type="warning"
        showIcon
        message="检测到正文版本冲突 (OCC 409)"
        description={`您在保存草稿或提交时基于 v${conflict?.baseRevision}，但当前服务器已被更新为 v${conflict?.remoteRevision}。请对比双方内容后选择合并决策：`}
        style={{ marginBottom: 16 }}
      />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div>
          <h4 style={{ marginBottom: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>您的本地内容（待保存）</span>
            <Tag color="blue">本地</Tag>
          </h4>
          <div
            data-testid="conflict-local-content"
            style={{
              minHeight: 220,
              maxHeight: 360,
              overflowY: 'auto',
              padding: 12,
              background: '#f6ffed',
              border: '1px solid #b7eb8f',
              borderRadius: 4,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              fontSize: 13,
              lineHeight: 1.6,
            }}
          >
            {conflict?.localContent || '（空正文）'}
          </div>
        </div>
        <div>
          <h4 style={{ marginBottom: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>服务器最新正文 (v{conflict?.remoteRevision})</span>
            <Tag color="orange">远程最新</Tag>
          </h4>
          <div
            data-testid="conflict-remote-content"
            style={{
              minHeight: 220,
              maxHeight: 360,
              overflowY: 'auto',
              padding: 12,
              background: '#fffbe6',
              border: '1px solid #ffe58f',
              borderRadius: 4,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              fontSize: 13,
              lineHeight: 1.6,
            }}
          >
            {conflict?.remoteContent || '（空正文）'}
          </div>
        </div>
      </div>
      <p className="muted" style={{ marginTop: 12, fontSize: 12 }}>
        说明：「保留本地修改」将使用最新版本号覆盖并保存为您个人的草稿；「放弃本地」将使用远程最新正文替换当前编辑器内容。
      </p>
    </Modal>
  </>;
}
