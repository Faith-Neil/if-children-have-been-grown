// 为什么有这个文件：按 PRD v1.8 的挂证据规则判断一条资料能不能勾选。
// 它解决什么问题：避免历史标书、未确认、过期、缺协议或受限资料被当成可挂证据。
import type { Evidence } from './types';

export type EvidenceGroupId = 'structured' | 'snippet' | 'history';

export type EvidenceDecision = {
  group: EvidenceGroupId;
  selectable: boolean;
  reason: string;
};

export function evidenceGroup(item: Pick<Evidence, 'type'>): EvidenceGroupId {
  if (item.type === 'history') return 'history';
  if (item.type === 'snippet') return 'snippet';
  return 'structured';
}

export function evidenceDecision(item: Evidence, deadline?: string | null): EvidenceDecision {
  const group = evidenceGroup(item);
  if (group === 'history') return { group, selectable: false, reason: '历史标书只能参考，不能挂为证据' };
  if (item.restricted) return { group, selectable: false, reason: '受限无权' };
  if (item.status !== 'confirmed') return { group, selectable: false, reason: '未确认' };
  if (item.source_tier === 'partner' && item.agreement_present !== true) return { group, selectable: false, reason: '缺协议' };
  const end = (deadline || '').slice(0, 10);
  if (item.valid_until && end && item.valid_until < end) return { group, selectable: false, reason: '过期' };
  if (item.usable_as_evidence === false) return { group, selectable: false, reason: '不能引用' };
  return { group, selectable: true, reason: '' };
}

export function evidenceInvalid(item: Evidence | undefined, deadline?: string | null): boolean {
  if (!item) return true;
  return !evidenceDecision(item, deadline).selectable;
}

export function attachedEvidenceLabel(item: Evidence | null | undefined, deadline?: string | null): string {
  if (!item) return '资料已不可见';
  const decision = evidenceDecision(item, deadline);
  if (decision.selectable) return '当前合格';
  if (decision.reason === '过期') return '证据失效';
  return decision.reason;
}

export function applyRefreshedAttachment(requirement: { evidence_ids: string[] }, revision: number) {
  const ids = requirement.evidence_ids.slice();
  return { ids, opened: { revision, ids: ids.slice() } };
}

export function groupEvidence(items: Evidence[], deadline?: string | null) {
  const decided = items.map(item => ({ item, decision: evidenceDecision(item, deadline) }));
  const structured = decided.filter(row => row.decision.group === 'structured');
  const snippets = decided.filter(row => row.decision.group === 'snippet').slice().sort((left, right) =>
    (right.item.match_score ?? 0) - (left.item.match_score ?? 0) || left.item.name.localeCompare(right.item.name, 'zh'));
  const history = decided.filter(row => row.decision.group === 'history');
  const citable = [...structured, ...snippets].filter(row => row.decision.selectable);
  return { structured, snippets, history, citableEmpty: citable.length === 0 };
}

export function toggleSelection(current: string[], id: string, selected: boolean, allowed: boolean): string[] {
  if (!allowed) return current.slice();
  if (selected) return current.includes(id) ? current.slice() : [...current, id];
  return current.filter(value => value !== id);
}

export function attachmentDiff(opened: string[], next: string[]) {
  const openedSet = new Set(opened);
  const nextSet = new Set(next);
  return {
    added: next.filter(id => !openedSet.has(id)),
    removed: opened.filter(id => !nextSet.has(id)),
  };
}

export function attachmentStale(openedRevision: number, openedIds: string[], currentRevision: number, currentIds: string[]): boolean {
  if (currentRevision !== openedRevision) return true;
  return openedIds.join('\u0000') !== currentIds.join('\u0000');
}
