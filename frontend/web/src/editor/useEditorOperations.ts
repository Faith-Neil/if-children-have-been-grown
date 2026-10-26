// 为什么有这个文件：提取编辑台业务动作操作流（useEditorOperations）。
// 它解决什么问题：解耦草稿保存/恢复、整章建议采纳、变量插入、来源依据更新及本地备份等操作流，降低 EditorPage 复杂度。

import { useState } from 'react';
import { request } from '../shared/api.ts';
import type { Candidate, Chapter, Volume, Workspace, WritingInputPreview } from '../shared/types.ts';
import { recoveryWrite } from './editor-recovery.ts';
import type { RecoveryChoice } from './RecoveryReview.tsx';
import { candidateProblem, insertFactToken } from './writing-input.ts';
import { insertSlaMeasurement } from '../admin/sla-form.ts';
import { editingContentWrite, recoveryEditingFingerprint, reviewedEditingFingerprint } from './editing-source.ts';
import type { Lease } from './useEditorLock.ts';

export interface UseEditorOperationsOptions {
  chapter: Chapter | null;
  setChapter: React.Dispatch<React.SetStateAction<Chapter | null>>;
  content: string;
  setContent: React.Dispatch<React.SetStateAction<string>>;
  editFingerprint: string | null;
  setEditFingerprint: React.Dispatch<React.SetStateAction<string | null>>;
  chapterId: string;
  token: string;
  workspace: Workspace;
  lease: Lease | null;
  held: boolean;
  canEdit: boolean;
  canGenerate: boolean;
  planCurrent: boolean;
  combinedBusy: boolean;
  epoch: React.MutableRefObject<number>;
  sequence: React.MutableRefObject<number>;
  selection: React.MutableRefObject<{ start: number; end: number } | null>;
  setSavedAt: React.Dispatch<React.SetStateAction<string>>;
  setNotice: React.Dispatch<React.SetStateAction<string>>;
  run: (action: () => Promise<void>) => Promise<void>;
  reload: () => Promise<unknown>;
  mutate: (url: string, method: string, data?: unknown) => Promise<unknown>;
  report: (error: unknown) => void;
  modal: any;
  saveRecovery?: () => Promise<void>;
}

export function useEditorOperations({
  chapter,
  setChapter,
  content,
  setContent,
  editFingerprint,
  setEditFingerprint,
  chapterId,
  token,
  workspace,
  lease,
  held,
  canEdit,
  canGenerate,
  planCurrent,
  combinedBusy,
  epoch,
  sequence,
  selection,
  setSavedAt,
  setNotice,
  run,
  reload,
  mutate,
  report,
  modal,
}: UseEditorOperationsOptions) {
  const [slaKey, setSlaKey] = useState('');
  const [factId, setFactId] = useState('');
  const [instruction, setInstruction] = useState('写得更具体，按原文和已确认事实说明工作步骤，不能新增未经核实的承诺。');
  const [suggestion, setSuggestion] = useState<Candidate | null>(null);
  const [diff, setDiff] = useState<Candidate | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const [planOpen, setPlanOpen] = useState(false);
  const [inputOpen, setInputOpen] = useState(false);
  const [recovery, setRecovery] = useState<RecoveryChoice | null>(null);
  const [recoveryReviewed, setRecoveryReviewed] = useState(false);
  const [sourceReview, setSourceReview] = useState<{ preview: WritingInputPreview; target: 'editor' | 'recovery' } | null>(null);
  const [sourceReviewed, setSourceReviewed] = useState(false);

  // 1. 生成与建议
  const suggest = async () => {
    if (!canGenerate || !planCurrent || combinedBusy) return;
    await run(async () => {
      const start = epoch.current;
      const value = await request<Candidate>(`/api/chapters/${chapterId}/suggestions`, token, 'POST', { instruction });
      if (start === epoch.current) setSuggestion(value);
    });
  };

  const generate = async () => {
    if (!canGenerate || !planCurrent || combinedBusy) return;
    try {
      await mutate(`/api/v1/projects/${workspace.project.id}/generate`, 'POST', { chapter_ids: [chapterId] });
      setSuggestion(null);
      setNotice('已生成候选，尚未改动正式正文。请在右侧比较并确认。');
    } catch { /* 统一已汇报 */ }
  };

  const showDiff = (value: Candidate) => {
    if (candidateProblem(value, workspace.input_fingerprint, chapter?.revision)) return;
    setReviewed(false);
    setDiff(value);
  };

  const apply = async () => {
    if (!chapter || !lease || !held || !diff || candidateProblem(diff, workspace.input_fingerprint, chapter.revision) || !reviewed) return;
    await run(async () => {
      const start = epoch.current;
      const latest = await request<Workspace>(`/api/v1/projects/${workspace.project.id}/workspace`, token);
      if (start !== epoch.current) return;
      if (!diff.input_fingerprint || diff.input_fingerprint !== latest.input_fingerprint) {
        setDiff(null);
        setSuggestion(null);
        await reload();
        throw new Error('条款、事实、证据或正文已变化，这份候选已过期。请重新生成后核对。');
      }
      setContent(diff.content);
      setEditFingerprint(diff.input_fingerprint);
      setDiff(null);
      setSuggestion(null);
      setNotice('候选及生成时的来源依据已写入当前编辑内容。请人工修订，再保存草稿或提交本节。');
    });
  };

  // 2. 草稿恢复
  const reviewRecovery = (choice: RecoveryChoice) => {
    setRecoveryReviewed(false);
    setRecovery(choice);
  };

  const saveRecovery = async () => {
    if (!chapter || !lease || !held || !recovery || !recoveryReviewed) return;
    await run(async () => {
      const start = epoch.current;
      const latest = await request<Chapter>(`/api/chapters/${chapterId}`, token);
      if (start !== epoch.current) return;
      const current = await request<Workspace>(`/api/v1/projects/${workspace.project.id}/workspace`, token);
      if (start !== epoch.current) return;
      const draft = await request<NonNullable<Chapter['draft']>>(`/api/chapters/${chapterId}/draft`, token, 'PUT', {
        ...recoveryWrite(chapter, latest, recovery.content),
        ...editingContentWrite(recovery.content, recoveryEditingFingerprint(recovery, current.input_fingerprint)),
        lease_token: lease.lease_token,
      });
      if (start !== epoch.current) return;
      sequence.current = draft.sequence;
      setChapter({ ...latest, draft });
      setContent(draft.content);
      setEditFingerprint(draft.input_fingerprint ?? null);
      setRecovery(null);
      setSavedAt(new Date().toLocaleTimeString('zh-CN', { hour12: false }));
      setNotice('恢复内容及其来源依据已保存为新的个人草稿，正式正文未变。请修订后提交本节。');
    });
  };

  // 3. 来源依据核对
  const reviewCurrentSources = async (target: 'editor' | 'recovery') => {
    await run(async () => {
      const start = epoch.current;
      const preview = await request<WritingInputPreview>(`/api/v1/projects/${workspace.project.id}/chapters/${chapterId}/writing-input`, token);
      if (start !== epoch.current) return;
      setSourceReviewed(false);
      setSourceReview({ preview, target });
    });
  };

  const confirmCurrentSources = async () => {
    if (!sourceReview || !sourceReviewed || !chapter || !held || !canEdit) return;
    await run(async () => {
      const start = epoch.current;
      const current = await request<Workspace>(`/api/v1/projects/${workspace.project.id}/workspace`, token);
      if (start !== epoch.current) return;
      const fingerprint = reviewedEditingFingerprint(sourceReview.preview.input_snapshot.input_fingerprint, current, chapterId, chapter.revision);
      if (sourceReview.target === 'recovery') {
        if (!recovery) return;
        setRecovery({ ...recovery, reviewed_input_fingerprint: fingerprint });
        setRecoveryReviewed(false);
      } else {
        setEditFingerprint(fingerprint);
      }
      setSourceReview(null);
      setSourceReviewed(false);
      setNotice('已人工核对当前来源并更新本次文字的写作依据；正文、草稿和原资料尚未改变，仍须保存或提交。');
      await reload();
    });
  };

  // 4. 变量插入
  const insertVariable = () => {
    const row = workspace.sla?.rows.find(item => item.var_key === slaKey);
    if (!held || combinedBusy || !row || row.fact_status !== 'confirmed' || row.source_stale || workspace.sla?.template_stale) return;
    try {
      const range = selection.current ?? { start: content.length, end: content.length };
      const result = insertSlaMeasurement(content, range.start, range.end, row.variable_token, row.unit);
      setContent(result.content);
      selection.current = { start: result.cursor, end: result.cursor };
      setNotice('已插入完整服务变量，导出读取矩阵的当前已确认值；本次修改仍须保存或提交。');
    } catch (error) { report(error); }
  };

  const insertProjectFact = () => {
    const fact = workspace.facts.find(item => item.id === factId);
    if (!held || combinedBusy || !fact) return;
    try {
      const range = selection.current ?? { start: content.length, end: content.length };
      const result = insertFactToken(content, range.start, range.end, fact);
      setContent(result.content);
      selection.current = { start: result.cursor, end: result.cursor };
      setNotice('已插入项目事实变量，导出读取当前已确认取值；本次修改仍须保存或提交。');
    } catch (error) { report(error); }
  };

  // 5. 本地备份与草稿删除
  const keepLocalText = () => {
    const link = document.createElement('a');
    const url = URL.createObjectURL(new Blob([content], { type: 'text/plain;charset=utf-8' }));
    link.href = url;
    link.download = `${chapter?.title ?? '本节'}-未提交文字.txt`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const deleteOwnDraft = () => {
    if (!chapter?.draft || combinedBusy) return;
    modal.confirm({
      title: '明确删除本人已保存草稿',
      content: '只删除这个账号在本节已保存的个人草稿，不删除其他人草稿、正式正文或历史。当前编辑框的文字仍保留；需要的话请先保留一份本地文字。',
      okText: '删除本人草稿',
      cancelText: '保留草稿',
      onOk: async () => {
        await run(async () => {
          const start = epoch.current;
          await request(`/api/chapters/${chapterId}/draft`, token, 'DELETE', { sequence: chapter.draft!.sequence });
          const latest = await request<Chapter>(`/api/chapters/${chapterId}`, token);
          if (start !== epoch.current) return;
          setChapter(latest);
          sequence.current = latest.draft?.sequence ?? 0;
          setNotice('本人已保存草稿已删除，当前编辑框文字、正式正文和历史仍保留。');
          await reload();
        });
      },
    });
  };

  const resetChapterStates = () => {
    setSlaKey('');
    setFactId('');
    setSuggestion(null);
    setDiff(null);
    setInputOpen(false);
    setRecovery(null);
    setSourceReview(null);
    setSourceReviewed(false);
  };

  return {
    slaKey, setSlaKey,
    factId, setFactId,
    instruction, setInstruction,
    suggestion, setSuggestion,
    diff, setDiff,
    reviewed, setReviewed,
    planOpen, setPlanOpen,
    inputOpen, setInputOpen,
    recovery, setRecovery,
    recoveryReviewed, setRecoveryReviewed,
    sourceReview, setSourceReview,
    sourceReviewed, setSourceReviewed,
    suggest,
    generate,
    showDiff,
    apply,
    reviewRecovery,
    saveRecovery,
    reviewCurrentSources,
    confirmCurrentSources,
    insertVariable,
    insertProjectFact,
    keepLocalText,
    deleteOwnDraft,
    resetChapterStates,
  };
}
