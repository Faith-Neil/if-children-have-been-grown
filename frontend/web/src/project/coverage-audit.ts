// 为什么有这个文件：把检索审计行收成覆盖视图可读短句。
// 它解决什么问题：界面只展示查询、库别命中与跳过原因，不堆说明书式标签。

import type { TechnicalRagAuditRow, TenderIndexStatus, WriterModelStatus } from '../shared/types.ts';

export function auditSearchLine(row: TechnicalRagAuditRow): string {
  const parts: string[] = [];
  if (row.tender_searched) parts.push(`本标 ${row.tender_hits ?? 0}`);
  if (row.history_searched) parts.push(`历史 ${row.history_hits ?? 0}`);
  if (row.material_searched) parts.push(`材料 ${row.material_hits ?? 0}`);
  if (row.skip_reason) parts.push(row.skip_reason);
  return parts.join(' · ') || '未检索';
}

export function auditTopKinds(row: TechnicalRagAuditRow): string {
  const kinds = [...new Set((row.top || []).map(item => item.dataset_kind).filter(Boolean))];
  return kinds.join(' / ');
}

export function tenderIndexLine(index: TenderIndexStatus | null | undefined): string {
  if (!index) return '';
  const name = index.dataset_name || index.backend || '本标索引';
  const count = typeof index.chunk_count === 'number' ? `${index.chunk_count} 片` : '';
  const skip = index.skip_reason || '';
  return [name, count, skip].filter(Boolean).join(' · ');
}

export function writerModelLine(model: WriterModelStatus | null | undefined): string {
  if (!model?.name) return '';
  const mode = model.is_real ? (model.is_local ? '本地真实' : '真实') : '替身';
  return `${model.name}（${mode}）`;
}
