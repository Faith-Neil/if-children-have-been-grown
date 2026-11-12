// 为什么有这个文件：保留示例的章节目录、正文和助手三栏编辑流程。
// 它解决什么问题：编辑权、旧草稿、正式版本与建议确认都以后台实际校验为准。
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Alert, App as AntApp, Button, Card, Drawer, Empty, Modal, Progress, Space, Spin, Tag, Tooltip } from 'antd';
import {
  BoldOutlined,
  HistoryOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  PictureOutlined,
  RedoOutlined,
  SaveOutlined,
  TableOutlined,
  UnderlineOutlined,
  UndoOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons';
import { ApiError, newIdempotencyKey, request } from '../shared/api.ts';
import { useProject, volumeName } from '../app/context.tsx';
import type { Candidate, Chapter, Volume, Workspace, WritingInputPreview } from '../shared/types.ts';
import { candidateProblem } from './writing-input.ts';
import { acquiredEditingFingerprint, editingContentWrite, loadedEditingFingerprint } from './editing-source.ts';
import { chapterCan, projectCan } from '../project/project-team.ts';
import { parseHonesty } from '../project/parse-honesty.ts';
import { AiTag } from '../library/BusinessTags.tsx';
import { ReadonlyBanner } from '../status/StatusViews';
import { useDataPermission } from '../shell/useDataPermission';
import { OutlineTreeView, type GeneratedDirectory } from '../project/OutlineTreeView';
import { PaperEditor, type PaperEditorHandle } from './PaperEditor';
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
import { paragraphAtOffset, paragraphsMatch } from './paragraph-keys.ts';
import { EditorIssuePanel } from './EditorIssuePanel.tsx';
import { useChapterIssues } from './useChapterIssues.ts';
import { canSelectInEditor, lineRangeOffsets, type ChapterIssue } from './chapter-issues-core.ts';
import { ParagraphLocksBar } from './ParagraphLocksBar.tsx';
import { VARIABLE_ERROR_CODES, mayHaveVariables, nodesMatch, resolveVariables, sourceLabel, type VariableNode } from './variable-nodes.ts';
import { VariableChip } from './VariableChip.tsx';
import type { ApplyResult } from './selection-rewrite-core.ts';
import { EditorDiffDrawer, type ChapterVersionItem } from './EditorDiffDrawer.tsx';
import { extractCitationIds, type CiteKind, type CitationMeta } from './cite-capsule';
import { useEditorLock, type Lease } from './useEditorLock.ts';
import { SystemChapterPanel } from '../project/SystemChapterPanel.tsx';
import { systemChapterKind } from '../project/system-chapter-core.ts';
import { useSelectionBubble } from './useSelectionBubble.ts';
import { EditorAuxiliaryDrawers } from './EditorAuxiliaryDrawers.tsx';
import { useEditorOperations } from './useEditorOperations.ts';
import { IDLE_SAVE_MS, editorTimings, lockHolderLabel, savedLabel, shouldAutosave, type EditorTimings } from './autosave-core.ts';

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
  const [content, setContent] = useState('');
  const [editFingerprint, setEditFingerprint] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [rightTab, setRightTab] = useState('assistant');
  const [savedAt, setSavedAt] = useState('');
  const [notice, setNotice] = useState('');
  const [historyCommitmentNotice, setHistoryCommitmentNotice] = useState<{ message: string; filenames: string[]; snapshotId: string } | null>(null);
  const [sourceAdvice, setSourceAdvice] = useState(false);
  const [versions, setVersions] = useState<ChapterVersionItem[]>([]);
  const [versionsOpen, setVersionsOpen] = useState(false);
  const [conflict, setConflict] = useState<ConflictContext | null>(null);
  const [, setHighlightedSourceId] = useState<string | null>(null);
  const [rewriteSelection, setRewriteSelection] = useState<RewriteSelection | null>(null);
  const [timings, setTimings] = useState<EditorTimings>(() => editorTimings(null));
  const [autosavePaused, setAutosavePaused] = useState(false);
  const [variables, setVariables] = useState<VariableNode[]>([]);
  const [cursorKey, setCursorKey] = useState<string | null>(null);
  const paperRef = useRef<PaperEditorHandle>(null);
  const autosaving = useRef(false);

  const epoch = useRef(0);
  const sequence = useRef(0);

  const activeChapter = workspace.chapters.find(item => item.id === chapterId);
  const lockedExcerpts = useMemo(() => {
    if (!chapter?.paragraphs) return [];
    const lines = chapter.content.split('\n');
    return chapter.paragraphs.filter(p => p.locked).map(p => {
      const text = lines.slice(p.line_start, p.line_end + 1).join(' ').trim();
      return { key: p.key, text: text.length > 40 ? `${text.slice(0, 40)}…` : text, by: p.locked_by_name ?? '—' };
    });
  }, [chapter]);
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
  const historyCommitmentDismissedSnapshotId =
    (activeChapter as { history_commitment_notice_dismissed_snapshot_id?: string | null } | undefined)
      ?.history_commitment_notice_dismissed_snapshot_id ?? null;
  const showHistoryCommitmentNotice = !!historyCommitmentNotice
    && historyCommitmentNotice.snapshotId !== historyCommitmentDismissedSnapshotId;
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
    if (!chapterId || !token) {
      setHistoryCommitmentNotice(null);
      return;
    }
    let alive = true;
    request<WritingInputPreview>(`/api/v1/projects/${workspace.project.id}/chapters/${chapterId}/writing-input`, token)
      .then(preview => {
        if (!alive) return;
        const snapshot = preview.input_snapshot as WritingInputPreview['input_snapshot'] & {
          history_commitment_notice?: { message: string; filenames: string[] };
          history_commitment_snapshot_id?: string;
        };
        const payload = snapshot.history_commitment_notice;
        const snapshotId = snapshot.history_commitment_snapshot_id;
        if (payload?.message && snapshotId) {
          setHistoryCommitmentNotice({ message: payload.message, filenames: payload.filenames ?? [], snapshotId });
        } else {
          setHistoryCommitmentNotice(null);
        }
      })
      .catch(() => { if (alive) setHistoryCommitmentNotice(null); });
    return () => { alive = false; };
  }, [chapterId, token, workspace.project.id, workspace.input_fingerprint, workspace.revision]);

  async function dismissHistoryCommitmentNotice() {
    if (!historyCommitmentNotice || combinedBusy) return;
    try {
      await mutate(
        `/api/v1/projects/${workspace.project.id}/chapters/${chapterId}/history-commitment-notice/dismiss`,
        'POST',
        { snapshot_id: historyCommitmentNotice.snapshotId },
      );
      await reload();
    } catch { /* 统一已汇报 */ }
  }

  // 变量节点（APP-M2-T164）：取值与是否有效以后台解析为准；文字停顿后再请求，数据源变化（来源指纹变）时重新解析
  useEffect(() => {
    if (!chapterId || !chapter || !mayHaveVariables(content)) { setVariables([]); return; }
    let alive = true;
    const timer = window.setTimeout(() => {
      resolveVariables(workspace.project.id, chapterId, token, content)
        .then(result => { if (alive) setVariables(result.variables); })
        .catch(() => { if (alive) setVariables([]); });
    }, 400);
    return () => { alive = false; window.clearTimeout(timer); };
  }, [content, chapterId, chapter?.revision, workspace.input_fingerprint, token]);
  const shownVariables = useMemo(() => (nodesMatch(variables, content) ? variables : []), [variables, content]);
  const invalidVariables = shownVariables.filter(item => item.status !== 'valid');
  function goToSource(_source: VariableNode['source']) { navigate('analyze'); }

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
  useEffect(() => {
    if (!chapter || !canEdit || held || loading) return;
    void acquire(null, true);
  }, [chapter?.id, canEdit, held, loading]);

  // 问题标注与侧栏联动（APP-M2-T166）：问题按段落键定位；正文段落标问题数，点标记只看这一段的问题
  const issues = useChapterIssues({ projectId: workspace.project.id, chapterId, token, revision: chapter?.revision, projectRevision: workspace.revision });
  function locateIssue(item: ChapterIssue) {
    issues.setActiveId(item.id);
    if (!item.paragraph_key || item.line_start === null || item.line_end === null || !chapter) return;
    issues.setFocusedKey(item.paragraph_key);
    if (held) {
      if (!canSelectInEditor(item, content, chapter.content)) { setNotice('编辑中的文字与已提交正文不同，段落位置可能已变化；提交本节后再定位。'); return; }
      const range = lineRangeOffsets(content, item.line_start, item.line_end);
      if (!range) return;
      const phrase = content.slice(range.start, range.end);
      paperRef.current?.selectText(phrase);
      selection.current = range;
      document.querySelector('[data-testid="paper-editor"]')?.scrollIntoView({ block: 'nearest' });
      return;
    }
    const key = item.paragraph_key;
    window.requestAnimationFrame(() => {
      const target = document.querySelector(`[data-testid="unheld-editor-text"] p[data-paragraph-key="${CSS.escape(key)}"]`);
      if (target) target.scrollIntoView({ block: 'center', behavior: 'smooth' });
    });
  }
  useEffect(() => {
    if (!issues.pending || !chapter) return;
    setRightTab('issues'); setAssistantCollapsed(false); locateIssue(issues.pending); issues.clearPending();
  }, [issues.pending, chapter]);
  function showParagraphIssues(key: string) {
    issues.setFilter(current => ({ ...current, paragraphKey: key })); issues.setFocusedKey(key); setRightTab('issues'); setAssistantCollapsed(false);
  }

  function localError(error: unknown) {
    report(error);
    if (error instanceof ApiError && ['INPUT_FINGERPRINT_REQUIRED', 'INPUT_FINGERPRINT_STALE'].includes(error.code)) {
      setNotice('这次没有写入。页面上的文字还在，请再保存一次。');
      void reload().catch(report); return;
    }
    if (error instanceof ApiError && error.code === 'FACT_SOURCE_CHANGE_REQUIRED') { setSourceAdvice(true); setNotice(error.message); return; }
    if (error instanceof ApiError && error.code === 'PARAGRAPH_LOCKED') { setNotice(`${error.message}当前文字仍在页面。`); return; }
    if (error instanceof ApiError && VARIABLE_ERROR_CODES.has(error.code)) { setSourceAdvice(true); setNotice(`${error.message}当前文字仍在页面。`); return; }
    if (error instanceof ApiError && [403, 404].includes(error.status)) {
      currentLease.current = null; setLease(null);
      setNotice('本次操作没有权限，当前文字保留在页面。请核对最新项目成员和章节分工；个人草稿不会转送给其他人。');
      void reload().catch(report); return;
    }
    if (error instanceof ApiError && error.status === 423) { currentLease.current = null; setLease(null); void acquire(null, true); }
    if (typeof isRevisionConflict === 'function' && isRevisionConflict(error)) {
      if (typeof handleRevisionConflict === 'function') void handleRevisionConflict(error, 'draft');
    }
  }

  async function handleRevisionConflict(error: unknown, target: 'draft' | 'commit' = 'draft') {
    if (!isRevisionConflict(error)) return false;
    try {
      const latest = await request<Chapter>(`/api/chapters/${chapterId}`, token);
      if (!chapter || latest.revision === chapter.revision) {
        sequence.current = latest.draft?.sequence ?? sequence.current;
        return false;
      }
      setConflict({ localContent: content, remoteContent: latest.content, remoteRevision: latest.revision, baseRevision: chapter.revision, target });
      return true;
    } catch (e) {
      report(e); setNotice('后台正文或草稿已变化，本次写入未成功。请核对最新版本。'); return false;
    }
  }

  async function applyConflictResolution(action: 'overwrite' | 'discard') {
    if (!conflict || !chapter) return;
    const resolved = resolveConflictChoice(action, conflict);
    if (action === 'overwrite') {
      if (!lease || !held) { setNotice('正在接通本节，请稍后再保存。'); return; }
      await run(async () => {
        const latest = await request<Chapter>(`/api/chapters/${chapterId}`, token);
        const updated = { ...latest, revision: conflict.remoteRevision };
        setChapter(updated);
        const value = await request<NonNullable<Chapter['draft']>>(`/api/chapters/${chapterId}/draft`, token, 'PUT', {
          lease_token: lease.lease_token, base_revision: conflict.remoteRevision, sequence: ++sequence.current, ...editingContentWrite(conflict.localContent, editFingerprint ?? workspace.input_fingerprint),
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

  async function acquire(reason: string | null = null, silent = false) {
    if (!canEdit || combinedBusy) return;
    await run(async () => {
      const start = epoch.current;
      try {
        await lock.acquireLock(reason);
      } catch (error) {
        // 上一页关掉后锁还在本人名下。负责人不能无理由接管，但回到自己的锁不应挡住自动保存。
        if (!(silent && error instanceof ApiError && error.code === 'TAKEOVER_REASON_REQUIRED')) throw error;
        const holder = chapter?.lock?.owner_id ?? (await request<Chapter>(`/api/chapters/${chapterId}`, token).catch(() => null))?.lock?.owner_id;
        if (holder !== user?.id) throw error;
        await lock.acquireLock('同一账号回到本节');
      }
      if (start !== epoch.current) return;
      const latest = await request<Chapter>(`/api/chapters/${chapterId}`, token);
      if (start !== epoch.current) return;
      if (chapter && latest.revision !== chapter.revision && modified) {
        if (!silent) setNotice('正文已有新版本。当前文字仍在页面，请先看最新版本再决定是否覆盖。');
        await lock.releaseLock(); return;
      }
      setChapter(latest); sequence.current = latest.draft?.sequence ?? sequence.current;
      if (!modified) setContent(latest.draft?.base_revision === latest.revision ? latest.draft.content : latest.content);
      setEditFingerprint(acquiredEditingFingerprint(editFingerprint, latest, modified) ?? workspace.input_fingerprint);
    });
  }

  async function saveDraft() {
    if (!chapter || !canEdit) return;
    await run(async () => {
      const active = lease ?? await lock.acquireLock(null);
      const start = epoch.current;
      try {
        const value = await request<NonNullable<Chapter['draft']>>(`/api/chapters/${chapterId}/draft`, token, 'PUT', {
          lease_token: active.lease_token, base_revision: chapter.revision, sequence: ++sequence.current, ...editingContentWrite(content, editFingerprint ?? workspace.input_fingerprint),
        });
        if (start !== epoch.current) return;
        setChapter({ ...chapter, draft: value }); setEditFingerprint(value.input_fingerprint ?? null);
        setSavedAt(new Date().toLocaleTimeString('zh-CN', { hour12: false })); setAutosavePaused(false);
        setNotice('草稿已保存，尚未进入正式正文和导出。');
      } catch (error) {
        if (start !== epoch.current) return;
        if (error instanceof ApiError && error.code === 'DRAFT_SEQUENCE_CONFLICT') {
          const latest = await request<Chapter>(`/api/chapters/${chapterId}`, token).catch(() => null);
          if (latest?.draft && start === epoch.current) sequence.current = latest.draft.sequence;
          return;
        }
        if (isRevisionConflict(error) && (await handleRevisionConflict(error, 'draft'))) return;
        throw error;
      }
    });
  }

  // 自动保存（APP-M2-T172）：停止输入 2 秒后、以及每隔公司设置的间隔，把手改保存为本人草稿；不提交为版本、不进入导出。
  // 失败时暂停自动保存并保留页面文字（来源变化、版本冲突按原规则提示），手动保存或提交成功后恢复。
  async function autoSaveDraft(allowSequenceRetry = true): Promise<boolean> {
    if (!chapter || !lease || !canEdit) return false;
    if (!shouldAutosave({ held, dirty, saving: autosaving.current, paused: autosavePaused, busy: combinedBusy })) return !dirty;
    autosaving.current = true;
    const start = epoch.current;
    let outcome: boolean | 'retry' = false;
    try {
      const value = await request<NonNullable<Chapter['draft']>>(`/api/chapters/${chapterId}/draft`, token, 'PUT', {
        lease_token: lease.lease_token, base_revision: chapter.revision, sequence: ++sequence.current, ...editingContentWrite(content, editFingerprint ?? workspace.input_fingerprint),
      });
      if (start === epoch.current) {
        setChapter(prev => (prev ? { ...prev, draft: value } : prev)); setEditFingerprint(value.input_fingerprint ?? null);
        setSavedAt(savedLabel(new Date(), true));
        outcome = true;
      }
    } catch (error) {
      if (start === epoch.current && error instanceof ApiError && error.code === 'DRAFT_SEQUENCE_CONFLICT') {
        const latest = await request<Chapter>(`/api/chapters/${chapterId}`, token).catch(() => null);
        if (latest?.draft && start === epoch.current) sequence.current = latest.draft.sequence;
        outcome = allowSequenceRetry ? 'retry' : false;
      } else if (start === epoch.current) {
        setAutosavePaused(true);
        if (!(isRevisionConflict(error) && (await handleRevisionConflict(error, 'draft')))) {
          localError(error);
          setNotice(current => current || '自动保存暂停：本次没有保存成功，文字仍在页面。请处理提示后手动保存草稿，成功后会恢复自动保存。');
        }
      }
    } finally {
      autosaving.current = false;
    }
    if (outcome === 'retry' && start === epoch.current) return autoSaveDraft(false);
    return outcome === true;
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
    if (!chapter || !canEdit) return;
    await run(async () => {
      const active = lease ?? await lock.acquireLock(null);
      const start = epoch.current;
      try {
        const committed = await request<{ paste_detected?: PastedParagraph[] | null }>(`/api/chapters/${chapterId}/versions`, token, 'POST', {
          lease_token: active.lease_token, base_revision: chapter.revision, ...editingContentWrite(content, editFingerprint ?? workspace.input_fingerprint), idempotency_key: newIdempotencyKey(),
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

  async function rollbackTo(target: number) {
    if (!chapter || !lease) return;
    await run(async () => {
      const start = epoch.current;
      const result = await request<{ revision: number; rollback_from: number }>(`/api/v1/projects/${workspace.project.id}/chapters/${chapterId}/rollback`, token, 'POST', {
        lease_token: lease.lease_token, base_revision: chapter.revision, target_revision: target, input_fingerprint: workspace.input_fingerprint,
      });
      const updated = await request<Chapter>(`/api/chapters/${chapterId}`, token);
      const history = await request<{ versions: ChapterVersionItem[] }>(`/api/chapters/${chapterId}/versions`, token);
      if (start !== epoch.current) return;
      setChapter(updated); setContent(updated.content); setVersions(history.versions.slice().reverse());
      setNotice(`已回退到 v${result.rollback_from}，生成新版本 v${result.revision}；历史版本保留。之前的检查和导出会失效，需要重新运行。`);
      await reload();
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

  const technicalOutline = workspace.technical_outline ?? null;
  const honesty = parseHonesty(workspace);
  const outlineChapter = technicalOutline ? workspace.chapters.find(item => item.id === technicalOutline.chapter_id) : undefined;

  async function refreshOutlineChapter() {
    if (!outlineChapter || chapterId !== outlineChapter.id || dirty) return;
    const updated = await request<Chapter>(`/api/chapters/${chapterId}`, token);
    setChapter(updated);
    setContent(updated.content);
    setEditFingerprint(loadedEditingFingerprint(updated, workspace.input_fingerprint));
    sequence.current = updated.draft?.sequence ?? sequence.current;
  }

  async function saveDirectory(payload: {
    title: string;
    headings: Array<{
      level: number;
      title: string;
      requirement_id: string | null;
      task_id?: string | null;
      requirement_ids?: string[];
    }>;
    confirm: boolean;
  }) {
    if (!outlineChapter) return;
    await mutate(`/api/v1/projects/${workspace.project.id}/plan`, 'POST', {
      scope: 'technical',
      chapters: [{ id: outlineChapter.id, title: payload.title.trim() || technicalOutline?.title || outlineChapter.title, volume: 'technical', fact_ids: [], writing_points: '' }],
      outline_title: payload.title.trim() || technicalOutline?.title,
      outline_headings: payload.headings.map(item => ({
        level: [1, 2, 3, 4].includes(item.level) ? item.level : 2,
        title: item.title.trim(),
        requirement_id: item.requirement_id ?? null,
        task_id: item.task_id ?? null,
        requirement_ids: item.requirement_ids ?? (item.requirement_id ? [item.requirement_id] : []),
      })),
      confirm_outline: payload.confirm,
    });
    await refreshOutlineChapter().catch(() => undefined);
  }

  async function generateDirectory(section?: string) {
    await mutate(`/api/v1/projects/${workspace.project.id}/generate`, 'POST', section ? { section } : {});
    const target = technicalOutline?.chapter_id;
    if (target && target !== chapterId) {
      selectChapter(target, 'technical');
      return;
    }
    await refreshOutlineChapter().catch(() => undefined);
  }

  const generatedDirectory: GeneratedDirectory | null = technicalOutline && outlineChapter && technicalOutline.headings.length > 0 ? {
    title: technicalOutline.title,
    chapterId: technicalOutline.chapter_id,
    headings: technicalOutline.headings,
    missing: technicalOutline.missing,
    reviewTitles: workspace.technical_needs_review ?? workspace.technical_quality?.review_titles ?? [],
    chapterContent: outlineChapter.id === chapterId ? content : outlineChapter.content,
    confirmed: workspace.plan_confirmed,
    canPrepare: projectCan(workspace, 'prepare_sources'),
    canGenerate: outlineChapter.permissions?.generate !== false,
    busy: projectBusy || busy,
    onSave: saveDirectory,
    onGenerate: generateDirectory,
    onOpen: () => selectChapter(outlineChapter.id, 'technical'),
    onExport: () => navigate('export'),
    onCoverage: () => navigate('analyze'),
  } : null;

  return <>
    <div
      className={`editor-layout ${breakpoint.tier} ${directoryCollapsed ? 'directory-collapsed' : ''} ${assistantCollapsed ? 'assistant-collapsed' : ''}`}
      data-testid="editor-page-layout"
      data-breakpoint-tier={breakpoint.tier}
      data-editor-columns={breakpoint.editorColumns}
    >
      {/* 1. 左侧章节大纲树面板 */}
      {!directoryCollapsed && !breakpoint.isSubCompact ? (
        <aside className="chapter-directory chapter-directory-panel is-wps" data-testid="editor-directory-panel">
          <div className="directory-panel-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', padding: '6px 4px', borderBottom: 'none', marginBottom: 0 }}>
            <Tooltip title="收起大纲面板以扩大编辑区"><Button size="small" type="text" icon={<MenuFoldOutlined />} onClick={() => setDirectoryCollapsed(true)} data-testid="collapse-outline-btn" /></Tooltip>
          </div>
          <div className="directory-tree-scroll" style={{ flex: 1, overflow: 'auto' }}>
            <OutlineTreeView
              nodes={outlineNodes}
              activeVolume={volume}
              directory={generatedDirectory}
              plain
              selectedChapterId={chapterId}
              onSelectChapter={node => selectChapter(node.id, node.volume as Volume)}
              onNavigateToEditor={id => selectChapter(id)}
            />
          </div>
          {!generatedDirectory && <div className="directory-bottom" style={{ marginTop: 'auto', paddingTop: 12 }}>
            <Button block size="small" onClick={() => ops.setPlanOpen(true)} disabled={combinedBusy || !workspace.parse_confirmed} data-testid="editor-open-plan-btn">写作方案与大纲确认</Button>
            <p className="muted" style={{ fontSize: 11, margin: '6px 0 0' }}>已确认方案 {workspace.chapters.filter(item => item.writing_input?.is_current).length} / {workspace.chapters.length} 节；每节独立办理</p>
          </div>}
        </aside>
      ) : (
        <aside className="chapter-directory-collapsed-strip" data-testid="editor-directory-collapsed-strip">
          <Tooltip title="展开大纲树" placement="right">
            <Button
              size="small"
              type="text"
              icon={<MenuUnfoldOutlined />}
              aria-label="展开大纲"
              onClick={() => {
                if (breakpoint.isSubCompact) setOutlineDrawerOpen(true);
                else setDirectoryCollapsed(false);
              }}
              data-testid="expand-outline-btn"
            />
          </Tooltip>
        </aside>
      )}

      {/* 2. 中间正文编辑区 */}
      <section className="editor-center" data-testid="editor-center-section">
        {honesty.degraded && (
          <Alert
            className="editor-notice"
            type="warning"
            showIcon
            data-testid="parse-honesty-warning"
            message="解析结果不完整"
            description={honesty.text}
          />
        )}
        {workspace.technical_kb && !workspace.technical_kb.ready && (
          <Alert
            className="editor-notice"
            type="warning"
            showIcon
            data-testid="technical-kb-missing"
            message="企业知识库未齐备"
            description={`缺 ${workspace.technical_kb.missing.join(' / ')}。仍可生成，但相关节企业 RAG 为空并标待补，不会静默假成功。`}
          />
        )}
        {workspace.writer_model?.name && (
          <div className="muted" data-testid="writer-model-status" style={{ marginBottom: 8 }}>
            正文模型 {workspace.writer_model.name}
            {workspace.writer_model.is_real
              ? (workspace.writer_model.is_local ? ' · 本地真实' : ' · 真实')
              : ' · 替身'}
            {workspace.tender_index?.chunk_count
              ? ` · 本标 ${workspace.tender_index.chunk_count} 片`
              : ''}
          </div>
        )}
        {generatedDirectory && (
          <div className="editor-main-path" data-testid="technical-main-path" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
            <Button
              type={generatedDirectory.confirmed ? 'default' : 'primary'}
              disabled={generatedDirectory.confirmed || !generatedDirectory.canPrepare || !!generatedDirectory.busy}
              onClick={() => void generatedDirectory.onSave({
                title: generatedDirectory.title,
                headings: generatedDirectory.headings.map(item => ({
                  level: item.level,
                  title: item.title,
                  requirement_id: item.requirement_id ?? null,
                  task_id: item.task_id ?? null,
                  requirement_ids: item.requirement_ids ?? (item.requirement_id ? [item.requirement_id] : []),
                })),
                confirm: true,
              })}
            >{generatedDirectory.confirmed ? '目录已确认' : '确认目录'}</Button>
            <Button
              type="primary"
              data-testid="main-path-generate"
              disabled={!generatedDirectory.confirmed || !!generatedDirectory.busy || !generatedDirectory.canGenerate}
              onClick={() => void generateDirectory().catch(() => undefined)}
            >{generatedDirectory.busy ? '生成中…' : '开始生成'}</Button>
            <Button data-testid="main-path-export" onClick={() => navigate('export')}>导出</Button>
            <Button type="link" data-testid="main-path-coverage" onClick={() => navigate('analyze')}>覆盖视图</Button>
          </div>
        )}

        <div className="editor-toolbar" data-testid="technical-editor-toolbar">
          <Space size={6} wrap>
            <Tooltip title="撤回"><Button size="small" icon={<UndoOutlined />} onClick={() => paperRef.current?.undo()} disabled={!canEdit} /></Tooltip>
            <Tooltip title="重做"><Button size="small" icon={<RedoOutlined />} onClick={() => paperRef.current?.redo()} disabled={!canEdit} /></Tooltip>
            <Tooltip title="标题"><Button size="small" onClick={() => paperRef.current?.heading(2)} disabled={!canEdit || combinedBusy}>标题</Button></Tooltip>
            <Tooltip title="正文"><Button size="small" onClick={() => paperRef.current?.paragraph()} disabled={!canEdit || combinedBusy}>正文</Button></Tooltip>
            <Tooltip title="加粗"><Button size="small" icon={<BoldOutlined />} onClick={() => paperRef.current?.bold()} disabled={!canEdit || combinedBusy} data-testid="toolbar-bold" /></Tooltip>
            <Tooltip title="下划线"><Button size="small" icon={<UnderlineOutlined />} onClick={() => paperRef.current?.underline()} disabled={!canEdit || combinedBusy} data-testid="toolbar-underline" /></Tooltip>
            <Tooltip title="项目符号"><Button size="small" icon={<UnorderedListOutlined />} onClick={() => paperRef.current?.bullet()} disabled={!canEdit || combinedBusy} /></Tooltip>
            <Tooltip title="编号"><Button size="small" onClick={() => paperRef.current?.ordered()} disabled={!canEdit || combinedBusy}>1.</Button></Tooltip>
            <Tooltip title="表格"><Button size="small" icon={<TableOutlined />} onClick={() => paperRef.current?.table()} disabled={!canEdit || combinedBusy} data-testid="toolbar-table" /></Tooltip>
            <Tooltip title="图片说明"><Button size="small" icon={<PictureOutlined />} onClick={() => paperRef.current?.insertParagraph('（图：请替换为示意图）')} disabled={!canEdit || combinedBusy} /></Tooltip>
            {generatedDirectory?.confirmed && (
              <Button type="primary" size="small" data-testid="toolbar-generate"
                disabled={!!generatedDirectory.busy || !generatedDirectory.canGenerate}
                onClick={() => void generateDirectory().catch(() => undefined)}>开始生成</Button>
            )}
            <Tooltip title="版本历史（次级）"><Button size="small" type="text" icon={<HistoryOutlined />} onClick={viewVersions} disabled={combinedBusy || !chapter}>版本</Button></Tooltip>
          </Space>
          <Space size={6}>
            {savedAt && <span className="saved-at" data-testid="editor-saved-at">{savedAt} 已保存</span>}
            {autosavePaused && held && <Tag color="orange" data-testid="autosave-paused-tag">自动保存已暂停</Tag>}
            {dirty && <Tag color="warning" data-testid="dirty-status-tag" icon={<SaveOutlined />}>未保存修改</Tag>}
            <Button size="small" icon={<SaveOutlined />} onClick={saveDraft} disabled={combinedBusy || !canEdit || !dirty} type={dirty ? "dashed" : "default"} data-testid="toolbar-save-draft-btn">保存草稿{dirty ? ' *' : ''}</Button>
            <Button type="primary" size="small" onClick={commit} disabled={combinedBusy || !canEdit || !chapter} loading={busy}>提交本节</Button>
          </Space>
        </div>

        <Spin spinning={loading}><div className="editor-scroll">
          {sourceAdvice && <Alert className="editor-notice" type="warning" showIcon message="取值由数据源决定，助手不能代改" action={<Space><Button size="small" onClick={() => navigate('analyze')}>回到分析</Button><Button size="small" onClick={() => navigate('analyze')}>回到分析里的承诺</Button></Space>} closable onClose={() => setSourceAdvice(false)} />}
          {notice && <Alert className="editor-notice" showIcon type={notice.includes('变化') || notice.includes('失败') || notice.includes('失效') ? 'warning' : 'info'} message={notice} closable onClose={() => setNotice('')} />}

          {chapter ? <article className="editor-chapter-shell" ref={editorWrapperRef} style={{ position: 'relative' }} onMouseUp={handleContainerMouseUp}>
            <SelectionBubble visible={selectionBubble.visible} position={selectionBubble.position} selectedText={selectionBubble.text} onPolish={handleBubblePolish} onComplianceQa={handleBubbleComplianceQa} onClear={handleBubbleClear} />
            {systemKind && activeChapter && <SystemChapterPanel chapterId={activeChapter.id} canGenerate={chapterCan(activeChapter, 'edit') && dataPermission.canEdit} />}
            {isReadOnlyView && !systemKind && <ReadonlyBanner banner reason={dataPermission.readOnlyReason || '当前章节处于只读浏览状态'} scope={dataPermission.scopeName || activeChapter?.title || volumeName(chapter.volume)} roleName={dataPermission.roleLabel} style={{ marginBottom: 16 }} />}
            <div className="document-heading">
              <h2>{chapter.title}</h2>
              <Tag>{volumeName(chapter.volume)}</Tag>
            </div>
            <p className="document-subline">本节编写人 {activeChapter?.assignee_name || '未指定'} · 正文版本 v{chapter.revision}</p>

            {showHistoryCommitmentNotice && historyCommitmentNotice && (
              <Alert
                className="editor-notice"
                type="warning"
                showIcon
                data-testid="history-commitment-notice"
                message={historyCommitmentNotice.message}
                description={historyCommitmentNotice.filenames.length > 0 ? (
                  <ul style={{ margin: 0, paddingLeft: 18 }}>
                    {historyCommitmentNotice.filenames.map(name => <li key={name}>{name}</li>)}
                  </ul>
                ) : undefined}
                closable
                onClose={() => void dismissHistoryCommitmentNotice()}
                style={{ marginBottom: 12 }}
              />
            )}

            {(issues.markers.size > 0 || (!held && shownVariables.length > 0)) && (
              <div data-testid="unheld-editor-text">
                {[...issues.markers.entries()].map(([key, marker]) => (
                  <p key={key} data-paragraph-key={key} className={issues.focusedKey === key ? 'paragraph-focused' : ''}>
                    <button type="button" data-testid="paragraph-issue-marker" onClick={() => showParagraphIssues(key)}>{marker.count}</button>
                  </p>
                ))}
                {!held && shownVariables.map(node => <VariableChip key={`${node.kind}-${node.ref}-${node.start}`} node={node} onGoToSource={goToSource} />)}
              </div>
            )}
            {held && chapter && canEdit && (
              <ParagraphLocksBar
                projectId={workspace.project.id}
                chapter={chapter}
                content={content}
                token={token}
                canEdit={canEdit}
                busy={combinedBusy}
                cursor={() => paperRef.current?.caretOffset() ?? null}
                onChanged={async () => { setChapter(await request<Chapter>(`/api/chapters/${chapterId}`, token)); }}
                report={report}
              />
            )}
            {held && shownVariables.length > 0 && (
              <div data-testid="editor-variable-bar">
                {shownVariables.map(node => <VariableChip key={`${node.kind}-${node.ref}-${node.start}`} node={node} onGoToSource={goToSource} />)}
              </div>
            )}
            {invalidVariables.length > 0 && (
              <Alert data-testid="invalid-variables-notice" type="warning" showIcon message={`${invalidVariables.length} 个变量已失效`}
                action={<Button size="small" onClick={() => goToSource(invalidVariables[0].source)}>{sourceLabel(invalidVariables[0].source)}</Button>} />
            )}
            <div className={canEdit ? 'chapter-editor-editable-wrapper' : 'chapter-editor-unheld-view'} data-testid={canEdit ? 'paper-editor-held' : 'unheld-editor-view'}>
              <PaperEditor
                ref={paperRef}
                markdown={content}
                editable={canEdit && !combinedBusy}
                generating={!!(projectBusy || busy)}
                onChange={value => { lock.markActivity(); setContent(value); }}
                onActivity={() => lock.markActivity()}
                onSelection={range => { selection.current = range ? { start: range.start, end: range.end } : null; }}
              />
            </div>

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
                <Button size="small" type={dirty && canEdit ? 'primary' : 'default'} icon={<SaveOutlined />} onClick={saveDraft} disabled={combinedBusy || !canEdit || !dirty} data-testid="save-draft-btn">保存草稿{dirty ? ' *' : ''}</Button>
              </Space>
            </div>
            {chapter.draft && <Button size="small" danger disabled={combinedBusy} onClick={ops.deleteOwnDraft}>明确删除本人已保存草稿</Button>}
            {chapter.draft && chapter.draft.base_revision !== chapter.revision && <Card size="small" title={`旧草稿（基于 v${chapter.draft.base_revision}，未自动覆盖）`}
              extra={<Button size="small" disabled={combinedBusy || !held} onClick={() => ops.reviewRecovery({ title: `旧草稿 v${chapter.draft!.base_revision}`, content: chapter.draft!.content, source_kind: 'draft', input_fingerprint: chapter.draft!.input_fingerprint ?? null })}>核对并恢复</Button>} className="old-draft"><pre>{chapter.draft.content}</pre></Card>}
          </article> : <Empty description="当前没有可编辑章节" />}
        </div></Spin>
      </section>

      {/* 3. 右侧对话助手与面板 */}
      {assistantCollapsed ? (
        <aside className="assistant-collapsed-strip" data-testid="editor-assistant-collapsed-strip">
          <Tooltip title="展开对话助手" placement="left">
            <Button
              size="small"
              type="text"
              icon={<MenuUnfoldOutlined />}
              aria-label="展开助手"
              onClick={() => setAssistantCollapsed(false)}
              data-testid="toggle-assistant-btn"
            />
          </Tooltip>
        </aside>
      ) : (
      <EditorAssistantPanel
        rightTab={rightTab} setRightTab={setRightTab} candidate={candidate} candidateIssue={candidateIssue} instruction={ops.instruction} setInstruction={ops.setInstruction}
        combinedBusy={combinedBusy} held={held} canEdit={canEdit} canGenerate={canGenerate} chapter={chapter} planCurrent={planCurrent} modified={modified} workspace={workspace}
        chapterId={chapterId} onViewInput={() => ops.setInputOpen(true)} onShowDiff={ops.showDiff} onSuggest={ops.suggest}
        technicalAssistant
        generating={!!(projectBusy || busy)}
        draftReady={(outlineChapter?.content || content || '').trim().length > 20}
        collapseControl={(
          <Tooltip title="收起对话助手以扩展编辑区">
            <Button
              size="small"
              type="text"
              icon={<MenuFoldOutlined />}
              aria-label="收起助手"
              onClick={() => setAssistantCollapsed(true)}
              data-testid="toggle-assistant-btn"
            />
          </Tooltip>
        )}
        selectionTools={
          <SelectionRewritePanel projectId={workspace.project.id} chapter={chapter} content={content} selection={rewriteSelection}
            leaseToken={held && lease ? lease.lease_token : null} canGenerate={canEdit} busy={combinedBusy} token={token}
            onApplied={applyRewrite} onClear={() => setRewriteSelection(null)} report={report} />
        }
        openIssueCount={issues.data?.counts.open ?? 0}
        issuesPanel={<EditorIssuePanel data={issues.data} loading={issues.loading} error={issues.error} filter={issues.filter} onFilterChange={issues.setFilter}
          activeId={issues.activeId} highlightKey={held ? cursorKey : issues.focusedKey} onLocate={locateIssue} onReload={issues.reload} />}
      />
      )}
    </div>

    {/* 4. 差异对比 Modal */}
    <Modal title="写入确认 · 整章建议差异" cancelText="放弃这次写入" width={960} open={!!ops.diff} onCancel={() => ops.setDiff(null)} onOk={ops.apply} okText="确认写入当前草稿"
      okButtonProps={{ disabled: !held || combinedBusy || !ops.reviewed || !chapter || !ops.diff || !!candidateProblem(ops.diff, workspace.input_fingerprint, chapter.revision) }}>
      <div className="diff-description"><AiTag variant={ops.diff?.is_real_model ? 'model' : 'demo'} />将替换当前整章编辑内容；保存草稿不会提交正文，提交本节后才用于检查和导出。</div>
      <div className="diff-columns"><div><h4>当前内容</h4><pre className="diff-before">{content || '（空正文）'}</pre></div><div><h4>建议写入</h4><pre className="diff-after">{ops.diff?.content}</pre></div></div>
      <label className="review-checkbox"><input type="checkbox" checked={ops.reviewed} onChange={e => ops.setReviewed(e.target.checked)} /> 我已逐字核对原文、证据和承诺，并确认整章修改合理</label>
    </Modal>

    {/* 5. 版本历史与差异对比抽屉 */}
    <EditorDiffDrawer open={versionsOpen} onClose={() => setVersionsOpen(false)} versions={versions} currentContent={content} currentRevision={chapter?.revision} combinedBusy={combinedBusy} held={held}
      dirty={modified || (!!chapter?.draft && chapter.draft.content !== chapter.content)} system={!!systemKind} inputFingerprint={workspace.input_fingerprint} onReviewRecovery={ops.reviewRecovery} onRollback={target => void rollbackTo(target)} />

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
        nodes={outlineNodes} activeVolume={volume} directory={generatedDirectory} plain
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
