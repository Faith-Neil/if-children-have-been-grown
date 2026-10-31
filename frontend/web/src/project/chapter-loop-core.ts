// 为什么有这个文件：章节循环进度页与轮次时间线（APP-M2-T130 / T131）的接口调用与文案映射。
// 它解决什么问题：把“每章停在哪、每轮查出什么、谁修的、依据是什么、前章摘要是否缺失”整理成可单测的纯函数；
// 页面只做布局，能否重新检查仍以后台返回的 can_recheck 为准。

import { request } from '../shared/api.ts';
import type {
  ChapterLoopDetail, ChapterLoopHistoryEntry, ChapterLoopList, ChapterLoopMeta, ChapterLoopRow, ChapterLoopState, LoopRound, Volume,
} from '../shared/types.ts';

const base = (projectId: string) => `/api/v1/projects/${encodeURIComponent(projectId)}`;

export function fetchChapterLoops(projectId: string, token: string | null, volume: Volume | 'all' = 'all') {
  return request<ChapterLoopList>(`${base(projectId)}/chapter-loops?volume=${volume}`, token);
}

export function fetchChapterLoop(projectId: string, token: string | null, chapterId: string) {
  return request<ChapterLoopDetail>(`${base(projectId)}/chapters/${encodeURIComponent(chapterId)}/loop`, token);
}

export const KIND_LABELS: Record<string, string> = {
  generation_candidate: '生成后循环', generation: '生成后循环', recheck: '重新检查',
};

export function loopStatus(row: Pick<ChapterLoopRow, 'loop' | 'has_content'>): { color: string; label: string } {
  if (!row.loop) return row.has_content ? { color: 'default', label: '未检查' } : { color: 'default', label: '未生成' };
  if (row.loop.status === 'interrupted') return { color: 'red', label: '异常中断' };
  if (row.loop.stale) return { color: 'gold', label: '正文已改动，待复查' };
  if (row.loop.status === 'completed') return { color: 'green', label: '已完成' };
  if (row.loop.status === 'pending_human') return { color: 'orange', label: '待人工处理' };
  return { color: 'blue', label: '人工已处理' };
}

// 中断的章节按钮写“重试”，其余仍是“重新检查”；两者调用同一个重新检查接口。
export function retryLabel(loop: Pick<ChapterLoopState, 'status'> | null | undefined): string {
  return loop?.status === 'interrupted' ? '重试' : '重新检查';
}

export function interruptionText(loop: Pick<ChapterLoopState, 'status' | 'meta'> | null | undefined): string | null {
  if (loop?.status !== 'interrupted') return null;
  const error = loop.meta?.error;
  const retries = loop.meta?.retry_count ?? 0;
  const reason = error?.message || error?.type || '未记录原因';
  return `循环异常中断：${reason}。正文未改动，已有问题保持原样${retries ? `，已重试 ${retries} 次仍未成功` : ''}，请点击“重试”。`;
}

export function roundSummary(round: LoopRound): string {
  const parts = [`查出 ${round.found} 项`];
  if (round.resolved) parts.push(`解决 ${round.resolved} 项`);
  if (round.new) parts.push(`新出现 ${round.new} 项`);
  const fixes = round.fixes ?? [];
  if (fixes.length) {
    const byModel = fixes.filter(fix => fix.by === 'model').length;
    const byRule = fixes.length - byModel;
    const who = [byModel ? `模型修正 ${byModel} 段` : '', byRule ? `规则修正 ${byRule} 段` : ''].filter(Boolean).join('、');
    parts.push(`${who}（第 ${fixes.map(fix => fix.paragraph_index + 1).join('、')} 段）`);
  } else if (round.modified_paragraphs.length) {
    parts.push(`修改第 ${round.modified_paragraphs.map(index => index + 1).join('、')} 段`);
  }
  return parts.join(' · ');
}

export function roundColor(round: LoopRound, last: boolean, loop: Pick<ChapterLoopState, 'stop_reason' | 'rolled_back'>): string {
  if (!last) return 'blue';
  if (loop.rolled_back || loop.stop_reason === 'FIX_REGRESSION') return 'red';
  return loop.stop_reason === 'ALL_RESOLVED' ? 'green' : 'orange';
}

const INPUT_LABELS: [keyof NonNullable<ChapterLoopMeta['inputs']>, string][] = [
  ['requirements', '条款'], ['evidence', '已挂证据'], ['snippets', '知识库切片'], ['facts', '已确认事实'], ['omitted', '未纳入'], ['truncated', '预算裁剪'],
];

export function metaLines(meta: ChapterLoopMeta | undefined, loop: { checked_revision?: number | null; result_revision?: number | null }): { label: string; value: string }[] {
  if (!meta || !Object.keys(meta).length) return [{ label: '依据', value: '本次循环早于依据记录功能，未记录模型与输入' }];
  const lines: { label: string; value: string }[] = [];
  lines.push({ label: '任务', value: meta.task_label || meta.task || '未记录' });
  if (meta.model) {
    const config = meta.model_name ? `${meta.model_name}` : meta.model_config_id ? `配置 ${meta.model_config_id}` : '未绑定配置';
    lines.push({ label: '模型', value: `${meta.model}（${config}${meta.is_real_model ? '' : '，非真实模型'}）` });
  } else {
    lines.push({ label: '模型', value: '未调用模型' });
  }
  if (meta.error) lines.push({ label: '中断原因', value: `${meta.error.type ? meta.error.type + '：' : ''}${meta.error.message ?? meta.error.code}` });
  if (meta.fixer) lines.push({ label: '修正方式', value: meta.fixer });
  const inputs = meta.inputs ?? {};
  const counts = INPUT_LABELS.filter(([key]) => typeof inputs[key] === 'number').map(([key, label]) => `${label} ${inputs[key]}`);
  if (counts.length) lines.push({ label: '实际输入', value: counts.join(' · ') + (inputs.critical ? ' · 含★/废标条款' : '') });
  const from = meta.base_revision ?? null;
  const to = loop.result_revision ?? loop.checked_revision ?? null;
  if (from !== null || to !== null) {
    lines.push({ label: '版本', value: from !== null && to !== null && from !== to ? `v${from} → v${to}` : `v${to ?? from}（正文未改）` });
  }
  if (meta.context_fingerprint) lines.push({ label: '输入指纹', value: String(meta.context_fingerprint).slice(0, 12) });
  return lines;
}

export function relayNotice(meta: ChapterLoopMeta | undefined): { type: 'success' | 'warning' | 'info'; text: string } | null {
  const relay = meta?.summary_relay;
  if (!relay) return null;
  if (relay.status === 'used') return { type: 'success', text: `已接力前章《${relay.title ?? ''}》摘要：${relay.summary ?? ''}` };
  if (relay.status === 'missing') return { type: 'warning', text: relay.message || `前章《${relay.title ?? ''}》还没有正文，未使用前章摘要，章节衔接须人工核对。` };
  if (relay.status === 'not_applicable') return { type: 'info', text: relay.message || '本章是本册第一章，没有前章摘要。' };
  return { type: 'info', text: relay.message || '未记录前章摘要。' };
}

export type TimelineLoop = {
  loop_no: number; kind: string; kind_label: string; started_at: string; stop_reason: string; stop_reason_label: string;
  rolled_back: boolean; rounds: LoopRound[]; meta?: ChapterLoopMeta; checked_revision?: number | null; result_revision?: number | null;
  current: boolean;
};

// 最近一次在前；历史条目按 loop_no 倒序。
export function timelineLoops(detail: Pick<ChapterLoopDetail, 'loop' | 'history'>): TimelineLoop[] {
  const toItem = (entry: ChapterLoopState | ChapterLoopHistoryEntry, current: boolean): TimelineLoop => ({
    loop_no: entry.loop_no, kind: entry.kind, kind_label: KIND_LABELS[entry.kind] ?? entry.kind,
    started_at: entry.started_at, stop_reason: entry.stop_reason,
    stop_reason_label: entry.stop_reason_label || entry.stop_reason, rolled_back: entry.rolled_back,
    rounds: entry.rounds ?? [], meta: entry.meta, checked_revision: entry.checked_revision, result_revision: entry.result_revision, current,
  });
  const items = (detail.history ?? []).map(entry => toItem(entry, false));
  if (detail.loop) items.push(toItem(detail.loop, true));
  return items.sort((a, b) => b.loop_no - a.loop_no);
}

export function progressPercent(totals: ChapterLoopList['totals'] | undefined): number {
  if (!totals || !totals.chapters) return 0;
  const settled = (totals.completed ?? 0) + (totals.human_handled ?? 0);
  return Math.round((settled / totals.chapters) * 100);
}
