// 为什么有这个文件：编辑台读取后台给出的段落键与逐段来源（APP-M2-T161）。
// 它解决什么问题：正文按行显示时，每一行要知道自己属于哪个段落键、这段是谁写的；
// 只读与未持锁视图据此给非人工写的段落标来源（对话助手写入、粘贴自对话助手、章节循环修正、系统生成），并在元素上留段落键供定位。

export type ParagraphSource = 'manual' | 'assistant' | 'assistant_pasted' | 'chapter_loop' | 'system';
export type ParagraphKey = {
  key: string;
  kind: 'heading' | 'para' | 'bullet' | 'ordered' | 'table';
  level: number;
  line_start: number;
  line_end: number;
  hash: string;
  source: ParagraphSource;
  source_label: string;
  /** 段落已锁定（APP-M2-T163） */
  locked?: boolean;
  locked_by_name?: string | null;
};
export type LineParagraph = { key: string; first: boolean; source: ParagraphSource; label: string; locked: boolean; lockedBy: string | null };

/** 行号 → 所属段落；只有段落首行 first 为真。 */
export function lineParagraphs(paragraphs: ParagraphKey[] | null | undefined): Map<number, LineParagraph> {
  const map = new Map<number, LineParagraph>();
  for (const p of paragraphs ?? []) {
    for (let line = p.line_start; line <= p.line_end; line += 1) {
      map.set(line, { key: p.key, first: line === p.line_start, source: p.source, label: p.source_label, locked: !!p.locked, lockedBy: p.locked_by_name ?? null });
    }
  }
  return map;
}

/** 需要标出来源的段落：人工编写的不标。 */
export function showsSource(item: LineParagraph | undefined): boolean {
  return !!item && item.first && item.source !== 'manual';
}

/** 段落键与当前文字是否还对得上（本地改过之后行号会错位，此时不显示来源）。 */
export function paragraphsMatch(paragraphs: ParagraphKey[] | null | undefined, content: string, committed: string): boolean {
  return !!paragraphs?.length && content === committed;
}

/** 光标（字符位置）所在的段落；空行或越界时为 undefined。 */
export function paragraphAtOffset(content: string, offset: number, paragraphs: ParagraphKey[] | null | undefined): ParagraphKey | undefined {
  if (offset < 0 || offset > content.length) return undefined;
  const line = content.slice(0, offset).split('\n').length - 1;
  return (paragraphs ?? []).find(p => p.line_start <= line && line <= p.line_end);
}

export type ParagraphLock = {
  paragraph_key: string; hash: string; excerpt: string; reason: string;
  locked_by: string; locked_by_name: string; locked_at: string; revision: number;
  line_start: number | null; line_end: number | null; present: boolean; can_unlock: boolean;
};

/** 锁定按钮的状态：本地有未提交修改时行号对不上，须先提交。 */
export function lockAction(params: { canEdit: boolean; dirtyAgainstCommitted: boolean; paragraph?: ParagraphKey }): { enabled: boolean; label: string; reason?: string } {
  if (!params.canEdit) return { enabled: false, label: '锁定段落', reason: '没有本节编辑权' };
  if (params.dirtyAgainstCommitted) return { enabled: false, label: '锁定段落', reason: '有未提交的修改，先提交本节再锁定' };
  if (!params.paragraph) return { enabled: false, label: '锁定段落', reason: '把光标放在要锁定的段落里' };
  if (params.paragraph.locked) return { enabled: false, label: '本段已锁定', reason: `锁定人：${params.paragraph.locked_by_name ?? '—'}` };
  return { enabled: true, label: '锁定光标所在段落' };
}
