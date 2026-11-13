// 为什么有这个文件：编辑台按纸面排版读写，章节字段仍保存导出能识别的 Markdown。
// 它解决什么问题：模型输出的标题、加粗、列表和表格在编辑时是版式，保存后仍能被 docx 解析器还原。

export interface PaperMark {
  type: 'bold' | 'underline';
}

export interface PaperNode {
  type: string;
  attrs?: { level?: number };
  content?: PaperNode[];
  text?: string;
  marks?: PaperMark[];
}

const HEADING = /^(#{1,6})\s+(.+?)\s*#*\s*$/;
const TABLE_ROW = /^\s*\|.*\|\s*$/;
const TABLE_RULE = /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$/;
const BULLET = /^\s*[-*+]\s+(.+)$/;
const ORDERED = /^\s*(\d{1,3})[.)、]\s+(.+)$/;
const INLINE = /<u>([\s\S]*?)<\/u>|\*\*([\s\S]*?)\*\*/g;

function cells(line: string) {
  let inner = line.trim();
  if (inner.startsWith('|')) inner = inner.slice(1);
  if (inner.endsWith('|')) inner = inner.slice(0, -1);
  return inner.split('|').map(cell => cell.trim());
}

function inlines(source: string): PaperNode[] {
  const nodes: PaperNode[] = [];
  let last = 0;
  for (const match of source.matchAll(INLINE)) {
    const index = match.index ?? 0;
    if (index > last) nodes.push({ type: 'text', text: source.slice(last, index) });
    if (match[1] !== undefined) {
      const inner = inlines(match[1]);
      const underlined = (inner.length ? inner : [{ type: 'text', text: match[1] }]).map(node => ({
        ...node,
        marks: [...(node.marks ?? []), { type: 'underline' as const }],
      }));
      nodes.push(...underlined);
    } else if (match[2]) {
      nodes.push({ type: 'text', text: match[2], marks: [{ type: 'bold' }] });
    }
    last = index + match[0].length;
  }
  if (last < source.length) nodes.push({ type: 'text', text: source.slice(last) });
  return nodes.filter(node => node.text);
}

function paragraph(text: string): PaperNode {
  const content = inlines(text);
  return content.length ? { type: 'paragraph', content } : { type: 'paragraph' };
}

function listItem(text: string): PaperNode {
  return { type: 'listItem', content: [paragraph(text)] };
}

function tableNode(rows: string[][]): PaperNode {
  const width = Math.max(...rows.map(row => row.length), 1);
  return {
    type: 'table',
    content: rows.map((row, index) => ({
      type: 'tableRow',
      content: Array.from({ length: width }, (_, column) => ({
        type: index === 0 ? 'tableHeader' : 'tableCell',
        content: [paragraph(row[column] ?? '')],
      })),
    })),
  };
}

export function markdownToDoc(markdown: string): PaperNode {
  const lines = markdown ? markdown.split(/\r?\n/) : [];
  const content: PaperNode[] = [];
  let index = 0;
  while (index < lines.length) {
    const line = lines[index];
    const heading = line.match(HEADING);
    if (heading) {
      const body = inlines(heading[2]);
      content.push({
        type: 'heading',
        attrs: { level: heading[1].length },
        ...(body.length ? { content: body } : {}),
      });
      index += 1;
      continue;
    }
    if (TABLE_ROW.test(line) && index + 1 < lines.length && TABLE_RULE.test(lines[index + 1])) {
      const rows = [cells(line)];
      index += 2;
      while (index < lines.length && TABLE_ROW.test(lines[index])) {
        rows.push(cells(lines[index]));
        index += 1;
      }
      content.push(tableNode(rows));
      continue;
    }
    if (BULLET.test(line)) {
      const items: PaperNode[] = [];
      while (index < lines.length && BULLET.test(lines[index])) {
        items.push(listItem(lines[index].match(BULLET)?.[1] ?? ''));
        index += 1;
      }
      content.push({ type: 'bulletList', content: items });
      continue;
    }
    if (ORDERED.test(line)) {
      const items: PaperNode[] = [];
      while (index < lines.length && ORDERED.test(lines[index])) {
        items.push(listItem(lines[index].match(ORDERED)?.[2] ?? ''));
        index += 1;
      }
      content.push({ type: 'orderedList', content: items });
      continue;
    }
    if (!line.trim()) {
      const previous = content[content.length - 1];
      const previousEmpty = previous?.type === 'paragraph' && !(previous.content && previous.content.length);
      if (!previousEmpty) content.push({ type: 'paragraph' });
      index += 1;
      continue;
    }
    content.push(paragraph(line));
    index += 1;
  }
  return { type: 'doc', content: content.length ? content : [{ type: 'paragraph' }] };
}

function inlineText(nodes: PaperNode[] | undefined) {
  return (nodes ?? []).map(node => {
    if (node.type !== 'text') return '';
    let text = node.text ?? '';
    const marks = new Set((node.marks ?? []).map(mark => mark.type));
    if (marks.has('bold')) text = `**${text}**`;
    if (marks.has('underline')) text = `<u>${text}</u>`;
    return text;
  }).join('');
}

function blockText(node: PaperNode) {
  if (node.type === 'heading') return `${'#'.repeat(node.attrs?.level || 1)} ${inlineText(node.content)}`.trimEnd();
  if (node.type === 'paragraph') return inlineText(node.content);
  if (node.type === 'bulletList') {
    return (node.content ?? []).map(item => `- ${inlineText(item.content?.[0]?.content)}`).join('\n');
  }
  if (node.type === 'orderedList') {
    return (node.content ?? []).map((item, index) => `${index + 1}. ${inlineText(item.content?.[0]?.content)}`).join('\n');
  }
  if (node.type === 'table') {
    const rows = (node.content ?? []).map(row => (row.content ?? []).map(cell => inlineText(cell.content?.[0]?.content).replace(/\|/g, '｜')));
    if (!rows.length) return '';
    const width = Math.max(...rows.map(row => row.length));
    const normalized = rows.map(row => [...row, ...Array(Math.max(0, width - row.length)).fill('')]);
    const header = `| ${normalized[0].join(' | ')} |`;
    const rule = `| ${normalized[0].map(() => '---').join(' | ')} |`;
    const body = normalized.slice(1).map(row => `| ${row.join(' | ')} |`).join('\n');
    return body ? `${header}\n${rule}\n${body}` : `${header}\n${rule}`;
  }
  return '';
}

export function docToMarkdown(doc: PaperNode) {
  return (doc.content ?? []).map(blockText).join('\n');
}

export function sameMarkdown(left: string, right: string) {
  const normalize = (value: string) => value.replace(/\r\n/g, '\n').replace(/\s+$/, '');
  return normalize(left) === normalize(right);
}
