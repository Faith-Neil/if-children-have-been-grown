// 为什么有这个文件：编辑台选区改写（对话助手样例，APP-M2-T178/T180/T185/T187）的纯计算部分。
// 它解决什么问题：选区要对应到已提交正文的字符位置；写入预览与后端规则一致（替换选区 / 插在选区后，选区在段末或样例多段时另起一段）；
// 差异视图按字比较，删除标红、增加标绿；【待补】另行计数；后端返回“原文位置已变化”时取出新位置让用户再确认。

import { ApiError } from '../shared/api.ts';

export type RewriteMode = 'rewrite' | 'expand' | 'shorten' | 'instruction' | 'rephrase';
export type RewriteAction = 'replace' | 'insert_after';

export const REWRITE_MODES: { value: RewriteMode; label: string }[] = [
  { value: 'rewrite', label: '改写' },
  { value: 'expand', label: '扩写' },
  { value: 'shorten', label: '缩写' },
  { value: 'instruction', label: '按指令修改' },
  { value: 'rephrase', label: '换一种说法' },
];
export const MAX_SELECTION = 2000;

export type RewriteSample = {
  id: string; style: string; style_label: string; text: string; warnings: string[]; chars: number;
  sources: unknown[]; status: 'proposed' | 'adopted' | 'not_adopted' | 'invalidated';
};
export type RewriteBatch = {
  id: string; chapter_id: string; base_revision: number; start: number; end: number; selected_text: string;
  selection_hash: string; mode: RewriteMode; mode_label: string; instruction: string; samples: RewriteSample[];
  dropped: { style: string; reason: string }[]; knowledge_base_enabled: boolean; source_note: string;
  provider: string; model: string; is_local_model: boolean; status: 'proposed' | 'adopted' | 'invalidated'; created_at: string;
};
export type EditOperation = {
  id: string; edit_mode: string; edit_mode_label: string; base_revision: number; result_revision: number;
  style: string; source_note: string; recheck: { issues: { rule_id: string; severity: string; message: string }[] };
};
export type ApplyResult = { revision: number; content: string; operation: EditOperation; batch: RewriteBatch };
export type Selection = { start: number; end: number; text: string };

/** 选区对应到已提交正文：位置一致直接用；只读视图拿不到位置时，原文在正文中唯一出现才可用。 */
export function locateSelection(committed: string, text: string, start?: number, end?: number): Selection | null {
  if (!text.trim() || text.length > MAX_SELECTION) return null;
  if (start !== undefined && end !== undefined && committed.slice(start, end) === text) return { start, end, text };
  const first = committed.indexOf(text);
  if (first < 0 || committed.indexOf(text, first + 1) >= 0) return null;
  return { start: first, end: first + text.length, text };
}

export function selectionProblem(committed: string, current: string, text: string, start?: number, end?: number): string | null {
  if (!text.trim()) return '请先在正文中选中要修改的文字';
  if (text.length > MAX_SELECTION) return `一次最多选 ${MAX_SELECTION} 字，请缩小选区`;
  if (current !== committed) return '正文有未提交的修改：先提交本节，再请对话助手改写选区';
  if (!locateSelection(committed, text, start, end)) return '选中的文字在本节出现多处或跨越了引用标记，请在编辑框中取得编辑权后重新选择';
  return null;
}

function paragraphEnd(content: string, end: number): number {
  const stop = content.indexOf('\n', end);
  return stop < 0 ? content.length : stop;
}

/** 与后端 selection_rewrite.apply 相同的写入结果，用于差异确认。 */
export function previewWrite(content: string, start: number, end: number, text: string, action: RewriteAction): string {
  if (action === 'replace') return content.slice(0, start) + text + content.slice(end);
  const stop = paragraphEnd(content, end);
  if (text.includes('\n') || end >= stop) return content.slice(0, stop) + '\n' + text + content.slice(stop);
  return content.slice(0, end) + text + content.slice(end);
}

export type DiffPart = { kind: 'same' | 'added' | 'removed'; text: string };

/** 按字比较两段文字（先去掉相同的头尾，再对中间做最长公共子序列；过长时整段标为删除+增加）。 */
export function diffText(before: string, after: string): DiffPart[] {
  let head = 0;
  while (head < before.length && head < after.length && before[head] === after[head]) head += 1;
  let tail = 0;
  while (tail < before.length - head && tail < after.length - head
    && before[before.length - 1 - tail] === after[after.length - 1 - tail]) tail += 1;
  const a = before.slice(head, before.length - tail);
  const b = after.slice(head, after.length - tail);
  const parts: DiffPart[] = [];
  const push = (kind: DiffPart['kind'], text: string) => {
    if (!text) return;
    const last = parts[parts.length - 1];
    if (last && last.kind === kind) last.text += text; else parts.push({ kind, text });
  };
  push('same', before.slice(0, head));
  if (a.length * b.length > 250_000) {
    push('removed', a); push('added', b);
  } else {
    const rows = a.length + 1, cols = b.length + 1;
    const table = new Uint16Array(rows * cols);
    for (let i = a.length - 1; i >= 0; i -= 1) {
      for (let j = b.length - 1; j >= 0; j -= 1) {
        table[i * cols + j] = a[i] === b[j] ? table[(i + 1) * cols + j + 1] + 1 : Math.max(table[(i + 1) * cols + j], table[i * cols + j + 1]);
      }
    }
    let i = 0, j = 0;
    while (i < a.length && j < b.length) {
      if (a[i] === b[j]) { push('same', a[i]); i += 1; j += 1; }
      else if (table[(i + 1) * cols + j] >= table[i * cols + j + 1]) { push('removed', a[i]); i += 1; }
      else { push('added', b[j]); j += 1; }
    }
    push('removed', a.slice(i)); push('added', b.slice(j));
  }
  push('same', before.slice(before.length - tail));
  return parts;
}

export function pendingCount(text: string): number {
  return (text.match(/【待补[^】]*】/g) ?? []).length;
}

/** 后端 409：原文位置变化但能唯一找到时给出新位置；找不到时样例已失效。 */
export function relocation(error: unknown): { relocated: true; start: number; end: number } | { relocated: false } | null {
  if (!(error instanceof ApiError) || error.code !== 'REVISION_CONFLICT' || !error.details) return null;
  const details = error.details as { relocated?: boolean; start?: number; end?: number };
  if (details.relocated === true && typeof details.start === 'number' && typeof details.end === 'number') {
    return { relocated: true, start: details.start, end: details.end };
  }
  return details.relocated === false ? { relocated: false } : null;
}

export const ACTION_LABEL: Record<RewriteAction, string> = { replace: '替换选中内容', insert_after: '插在选中内容后' };

export function rewritePath(projectId: string, chapterId: string, batchId?: string): string {
  const base = `/api/v1/projects/${projectId}/chapters/${chapterId}/selection-rewrites`;
  return batchId ? `${base}/${batchId}/apply` : base;
}
