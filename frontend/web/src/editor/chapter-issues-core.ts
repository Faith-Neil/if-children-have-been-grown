// 为什么有这个文件：编辑台“问题”页签与正文段落联动的纯逻辑（APP-M2-T166 / PRD v1.8 §5.11.2 问题侧栏）。
// 它解决什么问题：本章问题来自检查批次、章节循环与编辑后复查三处，后台已折算到当前段落键；
// 页面按状态、处理路径、规则筛选，给正文段落标问题数，点问题把光标或视图带到对应段落。

import { request } from '../shared/api.ts';

export type IssueOrigin = 'check' | 'loop' | 'edit_recheck';
export type IssueSeverity = 'blocker' | 'warning' | 'info';
export type ChapterIssue = {
  id: string;
  origin: IssueOrigin;
  origin_label: string;
  rule_id: string;
  code: string;
  severity: IssueSeverity;
  message: string;
  quote: string;
  route: string;
  route_label: string;
  status: string;
  status_label: string;
  open: boolean;
  stale: boolean;
  paragraph_key: string | null;
  line_start: number | null;
  line_end: number | null;
  located_by: 'key' | 'quote' | 'line' | 'none' | 'chapter';
  locate_note: string;
  created_at?: string | null;
  suggestion?: string | null;
  human_reason_label?: string | null;
  edit_mode_label?: string | null;
  number?: string | null;
};
export type ChapterIssueList = {
  project_id: string;
  chapter_id: string;
  revision: number;
  check: { id: string; volume: string; created_at: string; stale: boolean; passed: boolean } | null;
  loop: { loop_no: number; status: string; result_revision: number; started_at: string } | null;
  items: ChapterIssue[];
  counts: { open: number; blocker: number; unlocated: number };
};

export function fetchChapterIssues(projectId: string, chapterId: string, token: string | null, requestFn: typeof request = request) {
  return requestFn<ChapterIssueList>(`/api/v1/projects/${encodeURIComponent(projectId)}/chapters/${encodeURIComponent(chapterId)}/issues`, token);
}

export type IssueFilter = { status: 'open' | 'all'; route: string; rule: string; paragraphKey: string | null };
export const DEFAULT_FILTER: IssueFilter = { status: 'open', route: 'all', rule: 'all', paragraphKey: null };

export function filterIssues(items: ChapterIssue[], filter: IssueFilter): ChapterIssue[] {
  return items.filter(item => (filter.status === 'all' || item.open)
    && (filter.route === 'all' || item.route === filter.route)
    && (filter.rule === 'all' || (item.rule_id || item.code) === filter.rule)
    && (!filter.paragraphKey || item.paragraph_key === filter.paragraphKey));
}

/** 筛选下拉的选项，只列本章实际出现过的处理路径与规则。 */
export function issueOptions(items: ChapterIssue[]) {
  const routes = new Map<string, string>();
  const rules = new Set<string>();
  for (const item of items) {
    routes.set(item.route, item.route_label);
    rules.add(item.rule_id || item.code);
  }
  return {
    routes: [...routes].map(([value, label]) => ({ value, label })),
    rules: [...rules].filter(Boolean).sort().map(value => ({ value, label: value })),
  };
}

export type ParagraphMarker = { count: number; severity: IssueSeverity };
const RANK: Record<IssueSeverity, number> = { blocker: 0, warning: 1, info: 2 };

/** 段落键 → 待处理问题数与最重等级；正文段落据此标出。 */
export function paragraphMarkers(items: ChapterIssue[]): Map<string, ParagraphMarker> {
  const map = new Map<string, ParagraphMarker>();
  for (const item of items) {
    if (!item.open || !item.paragraph_key) continue;
    const current = map.get(item.paragraph_key);
    if (!current) map.set(item.paragraph_key, { count: 1, severity: item.severity });
    else map.set(item.paragraph_key, { count: current.count + 1, severity: RANK[item.severity] < RANK[current.severity] ? item.severity : current.severity });
  }
  return map;
}

/** 行号区间 → 字符区间（含末行，不含末尾换行），用于在编辑框中选中整段。 */
export function lineRangeOffsets(content: string, lineStart: number, lineEnd: number): { start: number; end: number } | null {
  const lines = content.split('\n');
  if (lineStart < 0 || lineEnd < lineStart || lineEnd >= lines.length) return null;
  let start = 0;
  for (let i = 0; i < lineStart; i += 1) start += lines[i].length + 1;
  let end = start;
  for (let i = lineStart; i <= lineEnd; i += 1) end += lines[i].length + (i < lineEnd ? 1 : 0);
  return { start, end };
}

/** 编辑中的文字与已提交正文不同，行号可能已错位：此时只能看问题，不能按行号选中。 */
export function canSelectInEditor(issue: ChapterIssue, content: string, committed: string): boolean {
  return issue.line_start !== null && issue.line_end !== null && content === committed;
}

export function severityColor(severity: IssueSeverity): string {
  return severity === 'blocker' ? 'red' : severity === 'warning' ? 'orange' : 'default';
}
