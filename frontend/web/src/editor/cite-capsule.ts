// 为什么有这个文件：提取证据节点（.cite）识别、胶囊元数据匹配与文本段落分词的纯逻辑。
// 它解决什么问题：
// 1. 在正文段落中快速识别 [证:ID] 与 [片:ID] 格式并拆分为结构化文本片段；
// 2. 将引用 ID 与知识库证据、要求条款或方案片段元数据（标题、资料编号、核验状态、有效期等）精确关联；
// 3. 统计和汇总正文中引用的证据清单，供界面胶囊渲染与悬浮 Popover 消费。

export type CiteKind = 'evidence' | 'snippet';

export interface CitationMeta {
  id: string;
  kind: CiteKind;
  title: string;
  code: string;
  status: 'confirmed' | 'valid' | 'pending' | 'needs_review' | string;
  validUntil?: string | null;
  quote?: string | null;
  sourceName?: string | null;
  page?: number | null;
}

export interface TextSegment {
  type: 'text' | 'cite';
  content: string;
  citeMeta?: CitationMeta;
}

/**
 * 正则表达式：匹配 [证:ID] 和 [片:ID]
 */
export const CITE_REGEX = /\[(证|片):([a-zA-Z0-9_\-.:#]+)\]/g;

/**
 * 从 ID 和类别推导标准 CitationMeta
 */
export function resolveCitationMeta(
  id: string,
  kind: CiteKind,
  known?: Partial<CitationMeta>
): CitationMeta {
  const defaultTitle = kind === 'evidence' ? `资料证据 #${id}` : `方案片段 #${id}`;
  return {
    id,
    kind,
    title: known?.title || defaultTitle,
    code: known?.code || id,
    status: known?.status || 'confirmed',
    validUntil: known?.validUntil ?? null,
    quote: known?.quote ?? null,
    sourceName: known?.sourceName ?? null,
    page: known?.page ?? null,
  };
}

/**
 * 解析文本中的引用标记为结构化 TextSegment 数组
 */
export function parseCitations(
  text: string,
  knownCitations?: Record<string, Partial<CitationMeta>>
): TextSegment[] {
  if (!text || typeof text !== 'string') return [];

  const segments: TextSegment[] = [];
  let lastIndex = 0;

  // 重置正则 index
  const regex = new RegExp(CITE_REGEX.source, 'g');
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    const matchStart = match.index;
    const matchEnd = regex.lastIndex;

    // 前置普通文本
    if (matchStart > lastIndex) {
      segments.push({
        type: 'text',
        content: text.slice(lastIndex, matchStart),
      });
    }

    const tagKindStr = match[1];
    const id = match[2];
    const kind: CiteKind = tagKindStr === '证' ? 'evidence' : 'snippet';
    const known = knownCitations?.[id];
    const citeMeta = resolveCitationMeta(id, kind, known);

    segments.push({
      type: 'cite',
      content: match[0],
      citeMeta,
    });

    lastIndex = matchEnd;
  }

  // 剩余普通文本
  if (lastIndex < text.length) {
    segments.push({
      type: 'text',
      content: text.slice(lastIndex),
    });
  }

  return segments;
}

/**
 * 提取文本中所有引用的证据 ID 与片段 ID
 */
export function extractCitationIds(text: string): {
  evidenceIds: string[];
  snippetIds: string[];
  allIds: string[];
} {
  if (!text || typeof text !== 'string') {
    return { evidenceIds: [], snippetIds: [], allIds: [] };
  }

  const evidenceSet = new Set<string>();
  const snippetSet = new Set<string>();

  const regex = new RegExp(CITE_REGEX.source, 'g');
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    const kind = match[1];
    const id = match[2];
    if (kind === '证') {
      evidenceSet.add(id);
    } else if (kind === '片') {
      snippetSet.add(id);
    }
  }

  const evidenceIds = Array.from(evidenceSet);
  const snippetIds = Array.from(snippetSet);
  return {
    evidenceIds,
    snippetIds,
    allIds: [...evidenceIds, ...snippetIds],
  };
}

/**
 * 胶囊标签呈现文案
 */
export function formatCiteLabel(kind: CiteKind, id: string): string {
  const prefix = kind === 'evidence' ? '证' : '片';
  return `${prefix}:${id}`;
}
