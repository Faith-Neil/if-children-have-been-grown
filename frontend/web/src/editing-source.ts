// 为什么有这个文件：把正在编辑的文字与它实际依据的来源版本一起保存。
// 它解决什么问题：旧草稿和候选不会因刷新页面或取得编辑权而悄悄变成依据最新资料写成。
import type { Chapter, Workspace } from './types';

export type RecoverySource = { source_kind: 'draft' | 'history'; input_fingerprint: string | null; reviewed_input_fingerprint?: string };

export function loadedEditingFingerprint(chapter: Pick<Chapter, 'revision' | 'draft'>, current: string) {
  return chapter.draft?.base_revision === chapter.revision ? chapter.draft.input_fingerprint ?? null : current;
}

export function acquiredEditingFingerprint(previous: string | null, latest: Pick<Chapter, 'revision' | 'draft'>, modified: boolean) {
  if (modified) return previous;
  if (latest.draft?.base_revision === latest.revision) return latest.draft.input_fingerprint ?? null;
  return previous;
}

export function editingContentWrite(content: string, fingerprint: string | null) {
  return { content, input_fingerprint: fingerprint };
}

export function recoveryEditingFingerprint(choice: RecoverySource, current: string) {
  const basis = choice.reviewed_input_fingerprint ?? choice.input_fingerprint;
  if (choice.source_kind === 'history' && basis !== current) throw new Error('核对历史正文期间项目来源又变化了。请先核对最新来源，再恢复；原文字仍保留。');
  return basis;
}

export function reviewedEditingFingerprint(reviewed: string, latest: Pick<Workspace, 'input_fingerprint' | 'chapters'>, chapterId: string, revision: number) {
  if (!reviewed || reviewed !== latest.input_fingerprint) throw new Error('核对期间项目来源又变化了，请重新读取来源后确认；当前文字与原依据均已保留。');
  if (latest.chapters.find(chapter => chapter.id === chapterId)?.revision !== revision) throw new Error('核对期间正文版本变化了，请先查看最新版本；当前文字与原依据均已保留。');
  return reviewed;
}
