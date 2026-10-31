// 为什么有这个文件：响应矩阵（APP-M2-T112～T117）的接口调用与纯函数。
// 它解决什么问题：响应方式与偏离口径、风险标记、批量匹配候选、分流确认的判断集中在这里便于单测；
// 星号/废标条款不能选“偏离/不适用”，候选只有勾选后才挂接，且只追加不替换已挂证据。
import { request } from '../shared/api.ts';

export type ResponseType = 'comply' | 'exceed' | 'deviate' | 'not_applicable';
export type MatrixItem = {
  id: string; critical: boolean; response_type: ResponseType | null; response_label: string; deviation_label: string;
  deviation_reason: string; assignee_id?: string | null; assignee_name?: string | null; suggested_volume: string; volume: string;
  volume_confirmed_at?: string | null; is_cross_volume: boolean; risk_flags: string[]; risk_labels: string[];
  evidence: { id: string; name: string; revision?: number; usable: boolean; reason: string }[];
};
export type MatrixData = { revision: number; volumes: string[]; items: MatrixItem[];
  stats: { total: number; confirmed: number; critical_unconfirmed: number; evidence_missing: number; evidence_invalid: number; placeholder: number; routing_pending: number; coverage: number; out_of_scope: number } };
export type MatchCandidate = { id?: string; source_id?: string; name: string; type?: string; revision?: number; score: number; attachable: boolean; reason?: string; already_attached?: boolean; basis: string; unavailable?: boolean };
export type MatchResult = { requirement_id: string; structured: MatchCandidate[]; snippets: MatchCandidate[]; history_reference: MatchCandidate[] };

export type CandidateRoute = 'structured' | 'snippet' | 'history';
export type EvidenceCandidate = {
  route: CandidateRoute; route_label: string; id?: string | null; name?: string | null; version?: number | string | null; source: string;
  score?: number | null; valid_until?: string | null; cite_reason: string; blocked_reason?: string | null; attachable: boolean;
  already_attached?: boolean; content_preview?: string | null;
};
export type EvidenceCandidates = {
  project_id: string; requirement_id: string; revision: number; kb_status: 'available' | 'unavailable' | 'disabled';
  can_attach: boolean; candidates: EvidenceCandidate[]; notice: string;
};

export const ROUTE_GROUPS: { route: CandidateRoute; title: string }[] = [
  { route: 'structured', title: '资料库规则匹配' },
  { route: 'snippet', title: '知识库片段' },
  { route: 'history', title: '历史标书仅参考' },
];

// 固定按三路顺序分组，空组也保留，页面才能明确告诉用户“这一路没有候选”。
export function groupCandidates(candidates: EvidenceCandidate[]): { route: CandidateRoute; title: string; items: EvidenceCandidate[] }[] {
  return ROUTE_GROUPS.map(group => ({ ...group, items: candidates.filter(candidate => candidate.route === group.route) }));
}

// 只有资料库规则匹配、后台判定可挂接、调用人有权限且尚未挂接的候选可选；片段与历史标书永远不可选。
export function candidateSelectable(candidate: EvidenceCandidate, canAttach: boolean): boolean {
  return canAttach && candidate.route === 'structured' && candidate.attachable && !candidate.already_attached && !!candidate.id;
}

export function kbStatusText(status: EvidenceCandidates['kb_status']): string | null {
  if (status === 'unavailable') return '知识库暂不可用，只给出资料库规则匹配结果。';
  if (status === 'disabled') return '本环境未启用知识库，只给出资料库规则匹配结果。';
  return null;
}

export function candidateMeta(candidate: EvidenceCandidate): string {
  const parts = [candidate.version != null && candidate.version !== '' ? `v${candidate.version}` : '', candidate.source,
    candidate.valid_until ? `有效至 ${candidate.valid_until}` : ''].filter(Boolean);
  return parts.join(' · ');
}

const base = (projectId: string) => `/api/v1/projects/${encodeURIComponent(projectId)}`;

export const RESPONSE_OPTIONS: { value: ResponseType; label: string }[] = [
  { value: 'comply', label: '满足（无偏离）' }, { value: 'exceed', label: '优于（正偏离）' },
  { value: 'deviate', label: '偏离（负偏离）' }, { value: 'not_applicable', label: '不适用' },
];

export const RISK_COLORS: Record<string, string> = {
  star_deviation: 'red', evidence_invalid: 'red', evidence_missing: 'orange', placeholder: 'orange',
  response_missing: 'orange', unmapped: 'gold', routing_pending: 'default',
};

export function fetchMatrix(projectId: string, token: string | null) {
  return request<MatrixData>(`${base(projectId)}/matrix`, token);
}

export function matchEvidence(projectId: string, token: string | null, ids: string[]) {
  return request<{ results: MatchResult[]; notice: string }>(`${base(projectId)}/matrix/match`, token, 'POST', { requirement_ids: ids });
}

export function fetchEvidenceCandidates(projectId: string, token: string | null, requirementId: string) {
  return request<EvidenceCandidates>(`${base(projectId)}/requirements/${encodeURIComponent(requirementId)}/evidence-candidates`, token);
}

export const matrixPaths = {
  routing: (projectId: string) => `${base(projectId)}/matrix/routing`,
  excel: (projectId: string) => `${base(projectId)}/matrix.xlsx`,
};

export function responseOptions(critical: boolean) {
  // 星号/废标条款不能“不适用”；如实选“偏离”会成为阻断项（PRD §5.3.1 规则 5）
  return RESPONSE_OPTIONS.map(option => ({
    ...option,
    disabled: critical && option.value === 'not_applicable',
    label: critical && option.value === 'deviate' ? '偏离（负偏离 · 星号条款将阻断导出）' : option.label,
  }));
}

export function needsReason(type?: ResponseType | null): boolean {
  return type === 'deviate' || type === 'not_applicable';
}

// 挂接只追加：已挂证据保留，重复的不加
export function appendEvidence(current: string[], chosen: string[]): string[] {
  return [...current, ...chosen.filter(id => !current.includes(id))];
}

export function selectable(candidate: MatchCandidate): boolean {
  return candidate.attachable && !candidate.already_attached && !!candidate.id;
}

export function routingRows(items: Pick<MatrixItem, 'id' | 'volume' | 'suggested_volume' | 'is_cross_volume'>[], useSuggested: boolean) {
  return items.map(item => ({ id: item.id, volume: useSuggested ? item.suggested_volume : item.volume, is_cross_volume: item.is_cross_volume }));
}
