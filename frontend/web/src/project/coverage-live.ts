// 为什么有这个文件：覆盖视图在技术卷生成会话中按 task.patched 实时更新行状态。
// 它解决什么问题：行状态不必等整卷写完再刷新；同一补丁重放多次结果不变，已结束的节不会被迟到的「生成中」改回去。

import type { CoverageRow } from '../shared/types.ts';

export type GenerationStatus = 'pending' | 'generating' | 'generated' | 'failed';
export type ResponseType = NonNullable<CoverageRow['response_type']>;
export type CoverageState = 'pending' | 'generating' | 'responded' | 'failed';

export type TaskPatch = {
  generation_status?: GenerationStatus;
  response_status?: string;
  response_types?: Record<string, ResponseType>;
};
export type TaskPatched = TaskPatch & { task_id: string; generation_status: GenerationStatus };
export type CoveragePatches = Readonly<Record<string, TaskPatch>>;

const DEVIATION_LABEL: Record<ResponseType, string> = {
  comply: '无偏离',
  exceed: '正偏离',
  deviate: '负偏离',
  not_applicable: '',
};

const STATE_LABEL: Record<CoverageState, string> = {
  pending: '未响应',
  generating: '生成中',
  responded: '已响应',
  failed: '生成失败',
};

/** 同一会话里生成状态只前进不后退：重放的「生成中」不会盖掉已写完或失败的节。 */
const RANK: Record<GenerationStatus, number> = { pending: 0, generating: 1, generated: 2, failed: 2 };
const RESPONDED: ReadonlySet<string> = new Set(['generated', 'needs_confirm', 'confirmed']);

function isGenerationStatus(value: unknown): value is GenerationStatus {
  return typeof value === 'string' && value in RANK;
}

function isResponseType(value: unknown): value is ResponseType {
  return typeof value === 'string' && value in DEVIATION_LABEL;
}

export function coverageState(row: Pick<CoverageRow, 'generation_status' | 'response_status'>): CoverageState {
  if (row.generation_status === 'failed') return 'failed';
  if (row.generation_status === 'generating') return 'generating';
  if (row.generation_status === 'generated' || RESPONDED.has(row.response_status)) return 'responded';
  return 'pending';
}

export function coverageLabel(row: Pick<CoverageRow, 'generation_status' | 'response_status' | 'response_type'>): string {
  const state = coverageState(row);
  const deviation = row.response_type ? DEVIATION_LABEL[row.response_type] : '';
  return state === 'responded' && deviation ? `已响应(${deviation})` : STATE_LABEL[state];
}

/** 事件 JSON 在边界收成任务补丁；不是 task.patched 或缺字段时丢弃。 */
export function parseTaskPatched(raw: unknown): TaskPatched | null {
  if (typeof raw !== 'object' || raw === null) return null;
  const record = raw as Record<string, unknown>;
  if (record.event !== 'task.patched' || typeof record.task_id !== 'string' || !record.task_id) return null;
  if (!isGenerationStatus(record.generation_status)) return null;
  const patch: TaskPatched = { task_id: record.task_id, generation_status: record.generation_status };
  if (typeof record.response_status === 'string') patch.response_status = record.response_status;
  if (typeof record.response_types === 'object' && record.response_types !== null) {
    const types: Record<string, ResponseType> = {};
    for (const [id, value] of Object.entries(record.response_types)) {
      if (isResponseType(value)) types[id] = value;
    }
    patch.response_types = types;
  }
  return patch;
}

/** 合并一条任务补丁。结果与已有状态相同时返回原对象。 */
export function mergeTaskPatch(patches: CoveragePatches, event: TaskPatched): CoveragePatches {
  const previous = patches[event.task_id] ?? {};
  const current = previous.generation_status;
  if (current && RANK[event.generation_status] < RANK[current]) return patches;
  const next: TaskPatch = {
    ...previous,
    generation_status: event.generation_status,
    ...(event.response_status !== undefined ? { response_status: event.response_status } : {}),
    ...(event.response_types ? { response_types: { ...previous.response_types, ...event.response_types } } : {}),
  };
  const same = next.generation_status === previous.generation_status
    && next.response_status === previous.response_status
    && JSON.stringify(next.response_types) === JSON.stringify(previous.response_types);
  return same ? patches : { ...patches, [event.task_id]: next };
}

/** 把会话补丁叠到工作区行上。没有补丁的行原样返回。 */
export function patchRows(rows: CoverageRow[], patches: CoveragePatches): CoverageRow[] {
  if (Object.keys(patches).length === 0) return rows;
  return rows.map(row => {
    const patch = patches[row.task_id];
    if (!patch) return row;
    return {
      ...row,
      generation_status: patch.generation_status ?? row.generation_status,
      response_status: patch.response_status ?? row.response_status,
      response_type: patch.response_types?.[row.requirement_id] ?? row.response_type,
    };
  });
}

export function coverageStats(rows: CoverageRow[]) {
  const stats = { total: rows.length, rejection: 0, responded: 0, generating: 0, failed: 0 };
  for (const row of rows) {
    if (row.is_rejection_criterion) stats.rejection += 1;
    const state = coverageState(row);
    if (state !== 'pending') stats[state] += 1;
  }
  return stats;
}
