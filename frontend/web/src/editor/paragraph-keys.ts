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
};
export type LineParagraph = { key: string; first: boolean; source: ParagraphSource; label: string };

/** 行号 → 所属段落；只有段落首行 first 为真。 */
export function lineParagraphs(paragraphs: ParagraphKey[] | null | undefined): Map<number, LineParagraph> {
  const map = new Map<number, LineParagraph>();
  for (const p of paragraphs ?? []) {
    for (let line = p.line_start; line <= p.line_end; line += 1) {
      map.set(line, { key: p.key, first: line === p.line_start, source: p.source, label: p.source_label });
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
