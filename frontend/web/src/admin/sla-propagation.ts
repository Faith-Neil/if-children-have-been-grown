// 为什么有这个文件：服务承诺“需复核”传播提示与判定汇总的接口调用和纯函数（APP-M2-T122 / T119）。
// 它解决什么问题：把后台给出的复核原因、受影响章节转成页面文案；是否需要复核只以后台返回为准，前端不自行判断。

import { request } from '../shared/api.ts';
import type { SlaPropagation, SlaReasonCode } from '../shared/types.ts';

export function fetchSlaPropagation(projectId: string, token: string | null) {
  return request<SlaPropagation>(`/api/v1/projects/${encodeURIComponent(projectId)}/sla/propagation`, token);
}

const REASON_COLORS: Record<SlaReasonCode, string> = {
  TEMPLATE_STALE: 'orange', SOURCE_STALE: 'orange', NEEDS_REVIEW: 'orange', UNCONFIRMED: 'default', VALUE_INVALID: 'red', RISK_UNREVIEWED: 'purple',
};
export const reasonColor = (code: SlaReasonCode): string => REASON_COLORS[code] ?? 'default';

/** 面板标题行：没有待处理时明确说明，不用“全部通过”之类的措辞替后台下结论。 */
export function propagationHeadline(data: Pick<SlaPropagation, 'selected' | 'summary'> | null | undefined): string {
  if (!data) return '正在读取服务承诺复核状态';
  if (!data.selected) return '尚未选用服务模板';
  const s = data.summary;
  const parts: string[] = [];
  if (s.needs_review) parts.push(`${s.needs_review} 项需重新核对`);
  if (s.invalid) parts.push(`${s.invalid} 项未填写或不满足招标`);
  if (s.unconfirmed) parts.push(`${s.unconfirmed} 项尚未确认`);
  if (s.risk_unreviewed) parts.push(`${s.risk_unreviewed} 项风险未说明`);
  if (s.stale_commitments) parts.push(`${s.stale_commitments} 份承诺函已过期`);
  if (s.affected_chapters) parts.push(`涉及 ${s.affected_chapters} 个章节`);
  return parts.length ? parts.join('，') : '没有待处理的复核项';
}

/** 面板是否需要提醒色：有需重新核对、无效或过期承诺函时为警告。 */
export function propagationSeverity(data: Pick<SlaPropagation, 'selected' | 'summary'> | null | undefined): 'warning' | 'info' | 'success' {
  if (!data || !data.selected) return 'info';
  const s = data.summary;
  return s.needs_review || s.invalid || s.stale_commitments ? 'warning' : s.unconfirmed || s.risk_unreviewed ? 'info' : 'success';
}
