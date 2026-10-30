// 为什么有这个文件：编辑台变量节点（APP-M2-T164，PRD v1.8 §5.11.2“变量带底色”）。
// 它解决什么问题：正文里的 {{fact:…}} / {{sla:…}} 按后台解析结果显示当前已确认取值（敏感号码为掩码），
// 失效变量标红并指明去哪个数据源改；把一行文字切成“普通文字 / 变量”片段，供只读视图渲染。
// 取值以后台 POST /api/v1/projects/{p}/chapters/{c}/variables 为准，页面不自行判断变量是否有效。

import { request } from '../shared/api.ts';

export type VariableStatus = 'valid' | 'unknown' | 'invalid';
export type VariableNode = {
  token: string; kind: 'fact' | 'sla'; ref: string; label: string;
  start: number; end: number; line: number;
  display: string; masked: boolean; status: VariableStatus; code: string | null; message: string;
  source: 'facts' | 'matrix';
};
export type VariableNodeList = { chapter_id: string; revision: number; variables: VariableNode[]; invalid: number };

export const VARIABLE_ERROR_CODES = new Set([
  'FACT_VARIABLE_INVALID', 'FACT_VARIABLE_UNIT_MISMATCH', 'FACT_VARIABLE_UNIT_DUPLICATED', 'FACT_VARIABLE_LOST',
  'SLA_VARIABLE_UNKNOWN', 'SLA_VARIABLE_UNCONFIRMED', 'SLA_VARIABLE_UNIT_MISMATCH', 'SLA_VARIABLE_UNIT_UNRESOLVED', 'SLA_VARIABLE_REMOVED',
]);

export function resolveVariables(projectId: string, chapterId: string, token: string | null, content: string) {
  return request<VariableNodeList>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/chapters/${encodeURIComponent(chapterId)}/variables`, token, 'POST', { content });
}

/** 正文里有没有可能是变量的写法；没有就不必请求后台。 */
export function mayHaveVariables(content: string): boolean {
  return /\{\{\s*(fact|sla)\s*:/.test(content);
}

export type VariableSegment = { type: 'text'; text: string } | { type: 'variable'; node: VariableNode };

/** 把第 line 行（行首在正文中的位置为 lineStart）切成文字与变量片段。变量位置以后台返回为准。 */
export function lineSegments(text: string, lineStart: number, nodes: VariableNode[]): VariableSegment[] {
  const mine = nodes.filter(n => n.start >= lineStart && n.end <= lineStart + text.length).sort((a, b) => a.start - b.start);
  const out: VariableSegment[] = [];
  let cursor = 0;
  for (const node of mine) {
    const from = node.start - lineStart;
    if (from < cursor) continue;
    if (from > cursor) out.push({ type: 'text', text: text.slice(cursor, from) });
    out.push({ type: 'variable', node });
    cursor = node.end - lineStart;
  }
  if (cursor < text.length) out.push({ type: 'text', text: text.slice(cursor) });
  return out;
}

/** 每一行的行首字符位置。 */
export function lineStarts(content: string): number[] {
  const starts = [0];
  for (let i = 0; i < content.length; i += 1) if (content[i] === '\n') starts.push(i + 1);
  return starts;
}

/** 变量胶囊上显示的文字。 */
export function variableText(node: VariableNode): string {
  if (node.status === 'valid') return node.display || '（空）';
  return node.status === 'unknown' ? `${node.label} · 不存在` : `${node.label} · 已失效`;
}

/** 后台结果与当前文字是否对得上（文字改过、结果还没回来时不显示，避免标错位置）。 */
export function nodesMatch(nodes: VariableNode[], content: string): boolean {
  return nodes.every(n => content.slice(n.start, n.end) === n.token);
}

export function sourceLabel(source: VariableNode['source']): string {
  return source === 'facts' ? '去项目事实表' : '去服务承诺矩阵';
}
