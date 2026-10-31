// 为什么有这个文件：集中“冲突处理、合并/拆分、文件版本链”的纯逻辑（PRD v1.8 §5.1.1-5.1.5、§5.2.1-5.2.4）。
// 它解决什么问题：让页面组件只负责展示，规则（理由必填、补遗处理不阻断、多位置切换等）可脱离浏览器验证。

import type { ConflictDecisionBody, ConflictView, FileRole, Requirement, RequirementSource, TenderFile } from '../shared/types.ts';

export const FILE_ROLE_OPTIONS: { value: FileRole; label: string }[] = [
  { value: 'tender', label: '招标文件' },
  { value: 'clarification', label: '澄清' },
  { value: 'addendum', label: '补遗' },
  { value: 'tech_spec', label: '技术规范书' },
  { value: 'contract', label: '合同条款' },
  { value: 'attachment', label: '附件' },
];

export const PARSE_SERVICE_OPTIONS = [
  { value: 'auto', label: '自动（先本地，取不出再交 RAGFlow）' },
  { value: 'local', label: '只用本地文字提取' },
  { value: 'ragflow', label: 'RAGFlow DeepDOC' },
] as const;
export type ParseServiceChoice = (typeof PARSE_SERVICE_OPTIONS)[number]['value'];

/** 提交处理冲突的请求体；理由必填（确认“已按补遗处理”除外），缺失时返回错误文字。 */
export function buildDecision(action: ConflictDecisionBody['action'], reason: string,
  target: { factId?: string; requirementId?: string } = {}): { body?: ConflictDecisionBody; error?: string } {
  const text = reason.trim();
  if (action !== 'confirm' && !text) return { error: '请写明处理理由' };
  if (action === 'choose' && !target.factId && !target.requirementId) return { error: '请先选定一方的取值' };
  if (action === 'assign_target' && !target.requirementId) return { error: '请先选择被替代的原条款' };
  const body: ConflictDecisionBody = { action, reason: text };
  if (target.factId) body.selected_fact_id = target.factId;
  if (target.requirementId) body.requirement_id = target.requirementId;
  return { body };
}

export function decisionPath(projectId: string, conflictId: string): string {
  return `/api/v1/projects/${projectId}/parse/conflicts/${encodeURIComponent(conflictId)}/decision`;
}

/** 阻断“确认解析结果”的冲突数：已按补遗处理、历史记录都不阻断。 */
export function blockingCount(conflicts: ConflictView[]): number {
  return conflicts.filter(item => item.current && item.blocking && item.status === 'pending').length;
}

export function conflictTone(item: Pick<ConflictView, 'status'>): 'red' | 'green' | 'blue' | 'default' {
  return item.status === 'pending' ? 'red' : item.status === 'by_addendum' ? 'blue' : item.status === 'resolved' ? 'green' : 'default';
}

/** 主条目卡片上的“已合并 N 条”；没有合并时返回空串。 */
export function mergedLabel(item: Pick<Requirement, 'merge_status' | 'merged_ids'>): string {
  const n = item.merged_ids?.length ?? 0;
  return item.merge_status === 'primary' && n > 0 ? `已合并 ${n} 条` : '';
}

/** 被并入的条目不单列；已被替代的条目仍显示（状态为已忽略）。 */
export function visibleRequirements<T extends Pick<Requirement, 'merge_status'>>(rows: T[]): T[] {
  return rows.filter(item => item.merge_status !== 'merged');
}

/** 多位置切换：循环取下一个来源，越界回到第一个。 */
export function nextSourceIndex(current: number, total: number): number {
  return total <= 0 ? 0 : (current + 1) % total;
}

export function sourceLabel(source: RequirementSource, index: number, total: number): string {
  const page = source.page ? `第 ${source.page} 页` : '页码未知';
  return `${index + 1}/${total} · ${source.filename ?? ''}${source.filename ? ' ' : ''}${page}`;
}

export function durationLabel(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return '—';
  return ms < 1000 ? `${ms} 毫秒` : `${Math.round(ms / 100) / 10} 秒`;
}

/** 可作为“被替代”的旧版：未被替代，且存在同类型、更晚上传的文件。 */
export function replacementOptions(file: TenderFile, files: TenderFile[]): TenderFile[] {
  if (file.superseded_by) return [];
  return files.filter(other => other.id !== file.id && other.file_role === file.file_role && !other.superseded_by
    && (other.uploaded_at ?? '') > (file.uploaded_at ?? ''));
}

/** 已解析的文件不能在补遗/澄清与其他类型之间切换（后台同样拒绝）。 */
export function roleChangeAllowed(file: TenderFile, next: FileRole): boolean {
  if (file.status !== 'parsed') return true;
  const amending = (role?: FileRole) => role === 'addendum' || role === 'clarification';
  return amending(file.file_role) === amending(next);
}

/** 补遗/澄清文件才有差异视图。 */
export function hasAddendumDiff(file: TenderFile): boolean {
  return (file.file_role === 'addendum' || file.file_role === 'clarification') && file.status === 'parsed';
}

export function retryBody(service: ParseServiceChoice, fileId: string): { file_ids: string[]; service: ParseServiceChoice } {
  return { file_ids: [fileId], service };
}
