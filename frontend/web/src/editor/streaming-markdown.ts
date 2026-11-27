// 为什么有这个文件：流式生成时的 Markdown 经常只到半个标记或半张表。
// 它解决什么问题：把中间态安全渲染成块结构，不裸露 `**`、`<u>`、孤立井号或未完成表格。

export type StreamInlineNode = {
  text: string;
  bold?: boolean;
  underline?: boolean;
};

export type StreamBlock =
  | { id: string; type: 'heading'; level: number; nodes: StreamInlineNode[] }
  | { id: string; type: 'paragraph'; nodes: StreamInlineNode[] }
  | { id: string; type: 'list'; ordered: boolean; items: StreamInlineNode[][] }
  | { id: string; type: 'table'; header: string[]; rows: string[][] }
  | { id: string; type: 'table-placeholder' }
  | { id: string; type: 'blank' };

type StreamBlockSeed =
  | { type: 'heading'; level: number; nodes: StreamInlineNode[] }
  | { type: 'paragraph'; nodes: StreamInlineNode[] }
  | { type: 'list'; ordered: boolean; items: StreamInlineNode[][] }
  | { type: 'table'; header: string[]; rows: string[][] }
  | { type: 'table-placeholder' }
  | { type: 'blank' };

function flush(nodes: StreamInlineNode[], buffer: string, bold: boolean, underline: boolean) {
  if (!buffer) return '';
  nodes.push({ text: buffer, ...(bold ? { bold: true } : {}), ...(underline ? { underline: true } : {}) });
  return '';
}

function trailingPartialLength(source: string): number {
  const partials = ['</u', '</', '<u', '<', '*'];
  for (const part of partials) {
    if (source.endsWith(part)) return part.length;
  }
  return 0;
}

/** 解析行内 Markdown。尾部未闭合标记按“已安全闭合”处理，半截标记直接隐藏。 */
export function parseStreamingInline(source: string): StreamInlineNode[] {
  const nodes: StreamInlineNode[] = [];
  let buffer = '';
  let bold = false;
  let underline = false;
  const end = source.length - trailingPartialLength(source);
  let index = 0;
  while (index < end) {
    if (source.startsWith('**', index)) {
      buffer = flush(nodes, buffer, bold, underline);
      bold = !bold;
      index += 2;
      continue;
    }
    if (source.startsWith('<u>', index)) {
      buffer = flush(nodes, buffer, bold, underline);
      underline = true;
      index += 3;
      continue;
    }
    if (source.startsWith('</u>', index)) {
      buffer = flush(nodes, buffer, bold, underline);
      underline = false;
      index += 4;
      continue;
    }
    buffer += source[index];
    index += 1;
  }
  flush(nodes, buffer, bold, underline);
  return nodes;
}

function tableCells(line: string): string[] {
  const trimmed = line.trim();
  const body = trimmed.startsWith('|') ? trimmed.slice(1) : trimmed;
  const withoutEnd = body.endsWith('|') ? body.slice(0, -1) : body;
  return withoutEnd.split('|').map(cell => cell.trim());
}

function isTableRule(line: string): boolean {
  // 流式中间态宽松判定：整行只含管道/短横/冒号/空白、至少一个管道且有一段 3 个以上短横。
  // 规则行只会越打越长，单调有效不回头，表格不会因第二列短横打到一半而在「表格/占位」间震荡；
  // 列数始终由表头决定，提前成型不产生结构跳动。单列 `| --- |` 与最终 paper-markdown 口径一致。
  const trimmed = line.trim();
  if (!trimmed.includes('|')) return false;
  if (!/^[\s|:-]+$/.test(trimmed)) return false;
  return /-{3,}/.test(trimmed);
}

function isTableLine(line: string): boolean {
  // 流式期间凡以 `|` 开头的行都按表格中间态对待：单列表格、尚未打出收尾管道的
  // 半截行都先进入占位，不把原始管道符号裸露给用户。中文正文极少以管道开头。
  return line.trim().startsWith('|');
}

function isPartialTableRule(line: string): boolean {
  return /^\|[\s:|-]*$/.test(line.trim());
}

function blockText(nodes: StreamInlineNode[]): string {
  return nodes.map(node => node.text).join('');
}

export type TrackedStreamingParse = {
  blocks: StreamBlock[];
  /** 每个块对应的源文起始行号，与 blocks 平行；用于把字符偏移映射回所属块。 */
  blockLines: number[];
};

/** 把完整但可能未收尾的流式 Markdown 分成稳定块；已稳定块和活跃尾部由调用方按数组末尾判断。 */
export function parseStreamingMarkdownTracked(markdown: string): TrackedStreamingParse {
  const lines = markdown.replace(/\r\n/g, '\n').split('\n');
  const blocks: StreamBlock[] = [];
  const blockLines: number[] = [];
  let startLine = 0;
  const push = (block: StreamBlockSeed) => {
    blocks.push({ ...block, id: `stream-block-${blocks.length}` } as StreamBlock);
    blockLines.push(startLine);
  };
  let index = 0;
  let pendingTableRule = false;
  while (index < lines.length) {
    startLine = index;
    const raw = lines[index];
    const line = raw.trim();
    if (pendingTableRule && line && isPartialTableRule(line)) {
      index += 1;
      continue;
    }
    if (line) pendingTableRule = false;
    if (!line) {
      if ((blocks.length === 0 || blocks[blocks.length - 1].type !== 'blank')) push({ type: 'blank' });
      index += 1;
      continue;
    }
    if (/^(#{1,6})\s*$/.test(line)) {
      index += 1;
      continue;
    }
    const heading = /^(#{1,6})\s+(.+)$/.exec(line);
    if (heading) {
      push({ type: 'heading', level: heading[1].length, nodes: parseStreamingInline(heading[2].trim()) });
      index += 1;
      continue;
    }
    if (isTableLine(line)) {
      if (index + 1 < lines.length && isTableRule(lines[index + 1])) {
        const header = tableCells(line);
        const rows: string[][] = [];
        index += 2;
        while (index < lines.length && isTableLine(lines[index])) {
          const cells = tableCells(lines[index]);
          rows.push(Array.from({ length: header.length }, (_, cellIndex) => cells[cellIndex] ?? ''));
          index += 1;
        }
        push({ type: 'table', header, rows });
      } else {
        push({ type: 'table-placeholder' });
        pendingTableRule = true;
        index += 1;
      }
      continue;
    }
    const unordered = /^[-*+]\s+/.test(line);
    const ordered = /^\d{1,3}[.、)]\s+/.test(line);
    if (unordered || ordered) {
      const items: StreamInlineNode[][] = [];
      while (index < lines.length) {
        const itemLine = lines[index].trim();
        const match = ordered ? /^\d{1,3}[.、)]\s+(.*)$/.exec(itemLine) : /^[-*+]\s+(.*)$/.exec(itemLine);
        if (!match) break;
        items.push(parseStreamingInline(match[1]));
        index += 1;
      }
      push({ type: 'list', ordered, items });
      continue;
    }
    push({ type: 'paragraph', nodes: parseStreamingInline(raw.trim()) });
    index += 1;
  }
  return { blocks, blockLines };
}

/** 把完整但可能未收尾的流式 Markdown 分成稳定块；已稳定块和活跃尾部由调用方按数组末尾判断。 */
export function parseStreamingMarkdown(markdown: string): StreamBlock[] {
  return parseStreamingMarkdownTracked(markdown).blocks;
}

/** 源文字符偏移所属的行号（0 起）。 */
export function lineIndexAtOffset(markdown: string, offset: number): number {
  let line = 0;
  const end = Math.min(offset, markdown.length);
  for (let position = 0; position < end; position += 1) {
    if (markdown[position] === '\n') line += 1;
  }
  return line;
}

/** 起始行号不超过给定行的最后一个块；用于把文本增长位置映射回渲染块。 */
export function blockIndexAtLine(blockLines: number[], line: number): number {
  let found = -1;
  for (let index = 0; index < blockLines.length; index += 1) {
    if (blockLines[index] <= line) found = index;
    else break;
  }
  return found;
}

/** 文本增长前沿的行号：最长公共前后缀夹出变化区，取变化区末尾字符所在行。
 * 多节并发时变化区横跨多节，前沿落在较靠下的写作位置；纯收缩（回滚/交接）不算增长。 */
export function growthFrontierLine(prev: string, next: string): number | null {
  if (prev === next) return null;
  const minLength = Math.min(prev.length, next.length);
  let prefix = 0;
  while (prefix < minLength && prev[prefix] === next[prefix]) prefix += 1;
  let suffix = 0;
  while (suffix < minLength - prefix && prev[prev.length - 1 - suffix] === next[next.length - 1 - suffix]) suffix += 1;
  const end = next.length - suffix;
  if (end <= prefix) return null;
  return lineIndexAtOffset(next, end - 1);
}

/** 活跃尾部行内片段按固定窗口切片；key 只依赖起点，追加文本时旧 key 不变。 */
export function stableInlineChunks(nodes: StreamInlineNode[], blockId: string, size = 8): Array<StreamInlineNode & { key: string }> {
  const chunks: Array<StreamInlineNode & { key: string }> = [];
  nodes.forEach((node, nodeIndex) => {
    if (!node.text) return;
    for (let start = 0; start < node.text.length; start += size) {
      chunks.push({
        ...node,
        text: node.text.slice(start, start + size),
        key: `${blockId}:n${nodeIndex}:o${start}`,
      });
    }
  });
  return chunks;
}

export function streamBlockHasText(block: StreamBlock): boolean {
  if (block.type === 'paragraph' || block.type === 'heading') return Boolean(blockText(block.nodes).trim());
  if (block.type === 'list') return block.items.some(item => Boolean(blockText(item).trim()));
  if (block.type === 'table') return block.header.some(Boolean) || block.rows.some(row => row.some(Boolean));
  return false;
}

export function parseHasVisibleText(blocks: StreamBlock[]): boolean {
  return blocks.some(streamBlockHasText);
}
