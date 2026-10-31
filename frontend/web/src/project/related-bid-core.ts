// 为什么有这个文件：R19 关联投标冲突的前端规则（APP-M2-T096 / PRD v1.8 §5.1.2 业务规则 2）。
// 它解决什么问题：保存招标编号或项目名称时后台返回 409 RELATED_BID_CONFLICT，页面弹出提示并要求填写说明；
// 说明不少于 5 个字，与后台一致；提示只用后台给的对方公司名称。

import { ApiError } from '../shared/api.ts';

export const MIN_REASON = 5;

export type RelatedBidDetails = { match: 'exact' | 'approximate' | null; companies: string[]; message: string; statute: string };
export type RelatedBidStatus = RelatedBidDetails & {
  needs_ack: boolean;
  acknowledged: { company_names: string[]; match: string; reason: string; by_name: string; at: string } | null;
};

/** 是否为关联投标冲突；是则返回后台给的提示与对方公司。 */
export function relatedBidConflict(error: unknown): RelatedBidDetails | null {
  if (!(error instanceof ApiError) || error.code !== 'RELATED_BID_CONFLICT') return null;
  const details = (error.details ?? {}) as Partial<RelatedBidDetails>;
  return {
    match: details.match ?? null,
    companies: Array.isArray(details.companies) ? details.companies.map(String) : [],
    message: details.message || error.message,
    statute: details.statute || '',
  };
}

export function reasonProblem(reason: string): string | null {
  return reason.trim().length >= MIN_REASON ? null : `请写明与上述公司无控股、管理关系或单位负责人相同的情况（至少 ${MIN_REASON} 个字）`;
}

export function matchLabel(match: RelatedBidDetails['match']): string {
  return match === 'exact' ? '同一招标编号与标段' : match === 'approximate' ? '可能是同一项目' : '';
}

export function relatedBidPath(projectId: string, suffix = ''): string {
  return `/api/v1/projects/${encodeURIComponent(projectId)}/related-bids${suffix}`;
}
