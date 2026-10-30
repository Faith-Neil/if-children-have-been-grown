// 为什么有这个文件：提取编辑台字数统计、脏状态判定与 OCC 409 版本冲突处理纯逻辑。
// 它解决什么问题：
// 1. 实时字符数统计与目标字数区间（未达标 / 符合预期 / 超出上限）智能诊断；
// 2. 章节草稿与正文脏状态（dirty flag）严格判定；
// 3. 后端 OCC（乐观并发控制）409 REVISION_CONFLICT 冲突识别与合并动作决策（保留本地覆盖 / 放弃本地采用远程最新）。

import type { Chapter } from '../shared/types.ts';
import { ApiError } from '../shared/api.ts';

/**
 * 字数统计与目标符合状态
 */
export type WordCountStatus = 'below_target' | 'on_target' | 'above_target' | 'no_target';

export interface WordCountInfo {
  charCount: number;
  targetLength: number | null;
  progressPercent: number;
  current: number;
  target: number | null;
  percentage: number;
  status: WordCountStatus;
  label: string;
  hint: string;
  color: 'success' | 'warning' | 'default';
}

/**
 * 实时计算章节字符数与目标字数符合状态
 * @param content 当前编辑区文本
 * @param targetLength 写作方案设定的目标字数
 */
export function calculateWordCount(
  content: string,
  targetLength?: number | null
): WordCountInfo {
  const safeContent = typeof content === 'string' ? content : '';
  const charCount = safeContent.length;

  if (typeof targetLength !== 'number' || targetLength <= 0) {
    return {
      charCount,
      targetLength: null,
      progressPercent: 0,
      current: charCount,
      target: null,
      percentage: 0,
      status: 'no_target',
      label: `${charCount} 字`,
      hint: charCount > 0 ? '未设目标字数（建议保持在 500~3000 字之间）' : '未填写正文内容',
      color: 'default',
    };
  }

  const progressPercent = Math.min(100, Math.round((charCount / targetLength) * 100));

  // 低于目标的 80%
  if (charCount < targetLength * 0.8) {
    const diff = targetLength - charCount;
    return {
      charCount,
      targetLength,
      progressPercent,
      current: charCount,
      target: targetLength,
      percentage: progressPercent,
      status: 'below_target',
      label: `${charCount} / ${targetLength} 字`,
      hint: `当前字数偏少，距离目标预期还差约 ${diff} 字`,
      color: 'warning',
    };
  }

  // 超出目标的 120%
  if (charCount > targetLength * 1.2) {
    const diff = charCount - targetLength;
    return {
      charCount,
      targetLength,
      progressPercent,
      current: charCount,
      target: targetLength,
      percentage: progressPercent,
      status: 'above_target',
      label: `${charCount} / ${targetLength} 字`,
      hint: `当前字数超出目标预期约 ${diff} 字，建议适当精炼`,
      color: 'warning',
    };
  }

  // 80% ~ 120% 区间，符合预期
  return {
    charCount,
    targetLength,
    progressPercent,
    current: charCount,
    target: targetLength,
    percentage: progressPercent,
    status: 'on_target',
    label: `${charCount} / ${targetLength} 字`,
    hint: `正文字数符合方案预期（目标 ${targetLength} 字）`,
    color: 'success',
  };
}

/**
 * 计算段落脏状态与修改状态
 */
export function calculateDirtyState(
  currentContent: string,
  chapterOrDraft?: Chapter | string | null,
  officialContent?: string | null,
  draftBaseRevision?: number | null,
  chapterRevision?: number | null
): { dirty: boolean; modified: boolean } {
  const content = currentContent ?? '';

  if (!chapterOrDraft && officialContent === undefined) {
    return { dirty: false, modified: false };
  }

  if (chapterOrDraft && typeof chapterOrDraft === 'object') {
    const chapter = chapterOrDraft as Chapter;
    const official = chapter.content ?? '';
    const draft = chapter.draft;
    let baseline = official;
    if (draft && draft.base_revision === chapter.revision) {
      baseline = draft.content ?? '';
    }
    return {
      dirty: content !== baseline,
      modified: content !== official,
    };
  }

  const draftContent = typeof chapterOrDraft === 'string' ? chapterOrDraft : null;
  const official = officialContent ?? '';

  let baseline = official;
  if (
    typeof draftContent === 'string' &&
    typeof draftBaseRevision === 'number' &&
    typeof chapterRevision === 'number' &&
    draftBaseRevision === chapterRevision
  ) {
    baseline = draftContent;
  }

  const dirty = content !== baseline;
  const modified = content !== official;

  return { dirty, modified };
}

/**
 * 判定错误是否为 OCC 409 版本冲突
 */
/** 状态码同为 409、但不是版本冲突的业务拒绝：不能走合并流程，按原提示处理。 */
// 这些 409 是内容或来源被拒，不是别人先提交了新版本，不能进入合并流程（T163 锁定段落、T164 失效变量）
const NOT_A_REVISION_CONFLICT = new Set([
  'PARAGRAPH_LOCKED', 'PARAGRAPH_ALREADY_LOCKED', 'SYSTEM_CHAPTER_READONLY', 'VOLUME_FINALIZED',
  'INPUT_FINGERPRINT_REQUIRED', 'INPUT_FINGERPRINT_STALE', 'FACT_SOURCE_CHANGE_REQUIRED', 'FACT_LITERAL_REPLACEMENT',
  'FACT_VARIABLE_INVALID', 'FACT_VARIABLE_UNIT_MISMATCH', 'FACT_VARIABLE_UNIT_DUPLICATED', 'FACT_VARIABLE_LOST',
  'SLA_VARIABLE_UNKNOWN', 'SLA_VARIABLE_UNCONFIRMED', 'SLA_VARIABLE_UNIT_MISMATCH', 'SLA_VARIABLE_UNIT_UNRESOLVED', 'SLA_VARIABLE_REMOVED',
]);

export function isRevisionConflict(error: unknown): boolean {
  if (!error) return false;
  if (error instanceof ApiError) {
    if (NOT_A_REVISION_CONFLICT.has(error.code)) return false;
    if (error.status === 409) return true;
    if (error.code === 'REVISION_CONFLICT' || error.code === 'CHAPTER_CONFLICT') return true;
  }
  const anyErr = error as { status?: number; code?: string; message?: string; error?: { code?: string; message?: string } };
  if (anyErr.status === 409) return true;
  if (anyErr.code === 'REVISION_CONFLICT' || anyErr.code === 'CHAPTER_CONFLICT') return true;
  if (anyErr.error?.code === 'REVISION_CONFLICT' || anyErr.error?.code === 'CHAPTER_CONFLICT') return true;
  if (typeof anyErr.message === 'string') {
    const msg = anyErr.message.toLowerCase();
    if (msg.includes('409') || msg.includes('revision_conflict') || msg.includes('chapter_conflict') || msg.includes('冲突')) {
      return true;
    }
  }
  return false;
}

/**
 * 冲突上下文信息
 */
export interface ConflictContext {
  localContent: string;
  remoteContent: string;
  remoteRevision: number;
  baseRevision: number;
  target?: 'draft' | 'commit';
}

export interface ConflictResolution {
  action: 'overwrite' | 'discard';
  nextContent: string;
  nextBaseRevision: number;
  nextRevision: number;
  message: string;
}

/**
 * 冲突解决决策纯函数
 */
export function resolveConflictChoice(
  choice: 'overwrite' | 'discard',
  context: ConflictContext
): ConflictResolution {
  if (choice === 'overwrite') {
    return {
      action: 'overwrite',
      nextContent: context.localContent,
      nextBaseRevision: context.remoteRevision,
      nextRevision: context.remoteRevision,
      message: `保留本地修改，已将基线版本推进至 v${context.remoteRevision}，可继续覆盖保存。`,
    };
  }

  return {
    action: 'discard',
    nextContent: context.remoteContent,
    nextBaseRevision: context.remoteRevision,
    nextRevision: context.remoteRevision,
    message: `放弃本地修改，已成功载入远程最新版本 v${context.remoteRevision}。`,
  };
}
