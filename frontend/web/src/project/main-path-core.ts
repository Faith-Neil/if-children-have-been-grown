// 为什么有这个文件：人工处理队列、分册交叉复核与疑似遗漏三处页面共用的纯函数与接口调用（Wave 11）。
// 它解决什么问题：把“谁能做什么、按钮是否出现、文案如何映射”集中成可单测的逻辑；页面只做布局，权限仍以后台返回为准。

import { request } from '../shared/api.ts';
import type {
  CrossReview, HumanIssue, HumanQueue, HumanQueueChapter, ProjectTeam, ScanHit, ScanHitList, Volume, VolumeStatus, Workspace,
} from '../shared/types.ts';

const base = (projectId: string) => `/api/v1/projects/${encodeURIComponent(projectId)}`;

export function fetchHumanQueue(projectId: string, token: string | null, volume: Volume | 'all' = 'all') {
  return request<HumanQueue>(`${base(projectId)}/human-queue?volume=${volume}`, token);
}

export function fetchScanHits(projectId: string, token: string | null) {
  return request<ScanHitList>(`${base(projectId)}/parse/omissions`, token);
}

export const queuePaths = {
  resolve: (projectId: string, issueId: string) => `${base(projectId)}/human-queue/issues/${encodeURIComponent(issueId)}/resolve`,
  reject: (projectId: string, issueId: string) => `${base(projectId)}/human-queue/issues/${encodeURIComponent(issueId)}/reject`,
  recheck: (projectId: string, chapterId: string) => `${base(projectId)}/chapters/${encodeURIComponent(chapterId)}/loop/recheck`,
  assignReviewer: (projectId: string, volume: Volume) => `${base(projectId)}/volumes/${volume}/cross-review`,
  confirmReview: (projectId: string, volume: Volume) => `${base(projectId)}/volumes/${volume}/cross-review/confirm`,
  finalize: (projectId: string, volume: Volume) => `${base(projectId)}/volumes/${volume}/finalize`,
  unlock: (projectId: string, volume: Volume) => `${base(projectId)}/volumes/${volume}/unlock`,
  addHit: (projectId: string, hitId: string) => `${base(projectId)}/parse/omissions/${encodeURIComponent(hitId)}/add`,
  excludeHit: (projectId: string, hitId: string) => `${base(projectId)}/parse/omissions/${encodeURIComponent(hitId)}/exclude`,
};

/** 处理方式（PRD v1.8 §5.7.7 操作 1）。缺证据类默认“保留【待补】等资料补齐”。 */
export const RESOLVE_METHODS = [
  { value: 'edited', label: '已修改正文' },
  { value: 'keep_placeholder', label: '保留【待补】等资料补齐' },
  { value: 'replaced_variable', label: '已替换为变量' },
] as const;

export function defaultResolveMethod(issue: Pick<HumanIssue, 'code' | 'human_reason'>): string {
  if (issue.code === 'PLACEHOLDER_RESIDUAL' && ['MISSING_EVIDENCE', 'PERSONNEL_IDENTITY'].includes(issue.human_reason ?? '')) {
    return 'keep_placeholder';
  }
  return 'edited';
}

/** 缺证据、证据引用问题提供“去补资料”入口，直达响应矩阵。 */
export function needsMaterial(issue: Pick<HumanIssue, 'human_reason'>): boolean {
  return ['MISSING_EVIDENCE', 'EVIDENCE_CITATION', 'PERSONNEL_IDENTITY'].includes(issue.human_reason ?? '');
}

/** 同一段落的其他待处理问题，可以一次合并标为已处理（§5.7.7 异常与边界）。 */
export function sameParagraphIssues(group: HumanQueueChapter, issue: HumanIssue): HumanIssue[] {
  return group.issues.filter(item => item.id !== issue.id && item.paragraph_index === issue.paragraph_index && item.permissions.resolve);
}

export function severityTag(issue: Pick<HumanIssue, 'level'>): { color: string; label: string } {
  return issue.level === 'blocker' ? { color: 'red', label: '阻断' } : issue.level === 'warning' ? { color: 'orange', label: '警告' } : { color: 'default', label: '提示' };
}

export function loopLine(group: HumanQueueChapter): string {
  const loop = group.loop;
  if (!loop) return '尚未运行章节循环';
  const parts = [`第 ${loop.loop_count} 次循环`, loop.stop_reason_label];
  if (loop.rolled_back) parts.push('已回退');
  if (loop.stale) parts.push('之后正文有改动');
  return parts.join(' · ');
}

export function daysUntil(deadline: string | null | undefined, now: number = Date.now()): number | null {
  if (!deadline) return null;
  const at = Date.parse(deadline);
  if (Number.isNaN(at)) return null;
  return Math.ceil((at - now) / 86_400_000);
}

// ---------------------------------------------------------------- 交叉复核与定稿

export const REVIEW_LABELS: Record<CrossReview['status'], { label: string; color: string }> = {
  none: { label: '未指定复核人', color: 'default' },
  pending: { label: '待复核', color: 'orange' },
  approved: { label: '复核通过', color: 'green' },
  returned: { label: '已退回', color: 'red' },
};

export function reviewTag(review?: CrossReview | null): { label: string; color: string } {
  if (!review) return REVIEW_LABELS.none;
  if (review.status === 'approved' && review.stale) return { label: '复核后正文有改动', color: 'orange' };
  return REVIEW_LABELS[review.status] ?? REVIEW_LABELS.none;
}

export function isVolumeManager(workspace: Pick<Workspace, 'permissions' | 'team'>, userId: string, volume: Volume): boolean {
  if (workspace.permissions?.manage_project === true) return true;
  return workspace.team?.volumes.some(item => item.volume === volume && item.owner_id === userId) ?? false;
}

/** 可选复核人：本项目可编辑成员，排除本册负责人。是否参与过编写由后台最终判定。 */
export function reviewerCandidates(team: ProjectTeam | undefined, volume: Volume): { value: string; label: string }[] {
  if (!team) return [];
  const owner = team.volumes.find(item => item.volume === volume)?.owner_id;
  return team.members
    .filter(member => member.project_role !== 'readonly' && member.user_id !== owner)
    .map(member => ({ value: member.user_id, label: member.name || member.user_id }));
}

export type VolumeActionState = {
  canAssign: boolean; canConfirm: boolean; canFinalize: boolean; canUnlock: boolean; finalizeBlockers: string[];
};

export function volumeActions(status: VolumeStatus | undefined, workspace: Pick<Workspace, 'permissions' | 'team'>, userId: string, volume: Volume): VolumeActionState {
  const manager = isVolumeManager(workspace, userId, volume);
  const finalized = Boolean(status?.is_finalized);
  const review = status?.cross_review;
  const blockers: string[] = [];
  if ((status?.pending_human_issues ?? 0) > 0) blockers.push(`人工处理队列还有 ${status?.pending_human_issues} 个问题`);
  if (!review || review.status !== 'approved') blockers.push('尚未完成交叉复核');
  else if (review.stale) blockers.push('复核后正文有改动，须重新复核');
  return {
    canAssign: manager && !finalized,
    canConfirm: !finalized && review?.status === 'pending' && review.reviewer_id === userId,
    canFinalize: manager && !finalized && blockers.length === 0,
    canUnlock: manager && finalized,
    finalizeBlockers: finalized ? [] : blockers,
  };
}

// ---------------------------------------------------------------- 疑似遗漏

export const SCAN_STATE_LABELS: Record<ScanHit['state'], { label: string; color: string }> = {
  suspected: { label: '疑似遗漏', color: 'red' },
  covered: { label: '已覆盖', color: 'green' },
  added: { label: '已新增为条目', color: 'blue' },
  excluded: { label: '已排除', color: 'default' },
};

export function defaultHitCategory(hit: Pick<ScanHit, 'terms'>): 'star' | 'disqualification' {
  return hit.terms.some(term => term === '★' || term.includes('*')) ? 'star' : 'disqualification';
}
