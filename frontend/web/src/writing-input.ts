// 为什么有这个文件：把本章方案和候选是否可采用的判断集中到实际页面使用的函数。
// 它解决什么问题：保留选中的事实，防止旧输入候选或不完整变量覆盖当前正文。
import type { Candidate, ChapterWritingInput, Fact, Volume, Workspace } from './types';

export type WritingPlanRow = ChapterWritingInput & { id?: string; title: string; volume: Volume };

export function writingPlanRows(workspace: Workspace): WritingPlanRow[] {
  return workspace.chapters.map(chapter => {
    const saved = workspace.writing_plan?.chapters.find(item => item.id === chapter.id) ?? chapter.writing_input;
    return { id: chapter.id, title: chapter.title, volume: chapter.volume, fact_ids: [...(saved?.fact_ids ?? [])], writing_points: saved?.writing_points ?? '', target_length: saved?.target_length ?? null };
  });
}

export function writingPlanPayload(rows: WritingPlanRow[]) {
  return rows.map(row => {
    const target = row.target_length;
    if (target !== null && target !== undefined && (!Number.isInteger(target) || target < 1 || target > 100_000)) throw new Error('字数目标须是 1 至 100000 的整数；不设目标时留空。');
    return { ...(row.id ? { id: row.id } : {}), title: row.title.trim(), volume: row.volume, fact_ids: [...new Set(row.fact_ids ?? [])], writing_points: (row.writing_points ?? '').trim(), target_length: target ?? null };
  });
}

export function candidateProblem(candidate: Candidate, fingerprint: string, revision: number | undefined) {
  if (!candidate.input_fingerprint || candidate.input_fingerprint !== fingerprint || candidate.status === 'stale') return '条款、事实、证据、方案或正文已变化，这份候选已过期。请重新生成后核对。';
  if (revision === undefined || candidate.base_revision !== revision) return '候选所依据的正文版本与当前版本不同，请重新生成。';
  return null;
}

export function insertFactToken(content: string, start: number, end: number, fact: Pick<Fact, 'id' | 'status' | 'source_type' | 'value'>) {
  if (fact.source_type === 'sla') throw new Error('服务承诺请使用服务变量入口，保持与矩阵取值一致。');
  if (fact.status !== 'confirmed' || !fact.value.trim()) throw new Error('只能插入已经确认且有取值的项目事实。');
  if (!/^[^{}\s]{1,200}$/.test(fact.id)) throw new Error('事实标识不完整，请重新读取项目事实。');
  if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || end < start || end > content.length) throw new Error('正文位置已变化，请重新选择插入位置。');
  const token = `{{fact:${fact.id}}}`;
  return { content: content.slice(0, start) + token + content.slice(end), cursor: start + token.length };
}
