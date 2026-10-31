// 为什么有这个文件：解析结果页分类树、确认前提与批量确认的纯计算部分（PRD v1.8 §5.2.2；APP-M2-T104）。
// 它解决什么问题：按后台给出的 10 类和评分项分组筛选条目卡片；列出“确认解析结果”还差什么；
// 只对允许批量确认的类别给出待确认条目（星号、废标、资格三类须逐条确认，后台同样拒绝）；
// 置信度低于公司阈值的条目高亮，“原文不可读”的条目须补录后逐条确认（§5.2.2 规则 2、异常与边界）。

export type ParseGate = { code: string; label: string; count: number; blocking: boolean; ok: boolean };
export type ScoringGroup = { name: string; score: number | null; ids: string[]; pending: number };
export type ParseCategory = {
  no: number; key: string; label: string; requirements: number; facts: number; total: number; pending: number;
  batch_allowed: boolean; groups?: ScoringGroup[] | null;
};
export type ParseReview = {
  categories: ParseCategory[]; requirement_categories: Record<string, string>; fact_categories: Record<string, string>;
  gates: ParseGate[]; can_confirm: boolean; parse_confirmed: boolean; confidence_threshold?: number;
};
export type TreeNode = { kind: 'all' } | { kind: 'category'; key: string } | { kind: 'group'; key: string; name: string }
  | { kind: 'quality'; which: 'unreadable' | 'low' };
type Row = {
  id: string; status: string; reference_status?: string; out_of_scope?: boolean;
  confidence?: number | null; unreadable?: boolean; manually_edited?: boolean;
};

export function threshold(review: ParseReview | null): number {
  return review?.confidence_threshold ?? 0.8;
}

/** 原文不可读且还没补录、没删除。 */
export function needsReentry(row: Row): boolean {
  return !!row.unreadable && !row.manually_edited && row.status !== 'rejected';
}

export function lowConfidence(row: Row, limit: number): boolean {
  return typeof row.confidence === 'number' && row.confidence < limit && row.status !== 'rejected';
}

export function confidenceLabel(row: Row): string {
  return typeof row.confidence === 'number' ? `置信度 ${row.confidence.toFixed(2)}` : '';
}

export function nodeRows<T extends Row>(rows: T[], review: ParseReview | null, node: TreeNode): T[] {
  if (node.kind === 'quality') {
    const limit = threshold(review);
    return rows.filter(row => node.which === 'unreadable' ? needsReentry(row) : lowConfidence(row, limit));
  }
  if (node.kind === 'all' || !review) return rows;
  if (node.kind === 'group') {
    const group = review.categories.find(c => c.key === node.key)?.groups?.find(g => g.name === node.name);
    const ids = new Set(group?.ids ?? []);
    return rows.filter(row => ids.has(row.id));
  }
  return rows.filter(row => review.requirement_categories[row.id] === node.key);
}

export function nodeCategory(review: ParseReview | null, node: TreeNode): ParseCategory | null {
  if (!review || node.kind === 'all' || node.kind === 'quality') return null;
  return review.categories.find(c => c.key === node.key) ?? null;
}

/** 可以批量确认的条目：允许批量的类别中待确认、且没有未解析引用的条目。 */
export function batchCandidates<T extends Row>(rows: T[], review: ParseReview | null, node: TreeNode): T[] {
  const category = nodeCategory(review, node);
  if (!category || !category.batch_allowed) return [];
  return nodeRows(rows, review, node).filter(row => row.status === 'pending' && row.reference_status !== 'unresolved' && !needsReentry(row));
}

export function unmetGates(review: ParseReview | null): ParseGate[] {
  return (review?.gates ?? []).filter(gate => gate.blocking && !gate.ok);
}

/** “确认解析结果”旁的提示：还剩几条、各是什么（验收⑤）。 */
export function gateSummary(review: ParseReview | null): string {
  const unmet = unmetGates(review);
  if (!review) return '';
  if (!unmet.length) {
    const refs = review.gates.find(g => g.code === 'REFERENCES_UNRESOLVED');
    return refs && refs.count ? `可以确认；另有 ${refs.count} 条引用未解析，确认时会提示` : '前提已满足，可以确认';
  }
  return `还差 ${unmet.reduce((n, g) => n + g.count, 0)} 项：` + unmet.map(g => `${g.label} ${g.count}`).join('、');
}

export function gateCount(review: ParseReview | null, code: string): number {
  return review?.gates.find(gate => gate.code === code)?.count ?? 0;
}

export function nodeTitle(review: ParseReview | null, node: TreeNode): string {
  if (node.kind === 'all') return '全部要求';
  if (node.kind === 'quality') return node.which === 'unreadable' ? '原文不可读（对照原页补录）' : `置信度低于 ${threshold(review)}`;
  const category = nodeCategory(review, node);
  if (node.kind === 'group') return `${category?.label ?? ''} › ${node.name}`;
  return category ? `${category.no} ${category.label}` : '';
}
