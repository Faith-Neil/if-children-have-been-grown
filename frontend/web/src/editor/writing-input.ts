// 为什么有这个文件：把本章方案和候选是否可采用的判断集中到实际页面使用的函数。
// 它解决什么问题：保留选中的事实，防止旧输入候选或不完整变量覆盖当前正文。
import type { Candidate, Chapter, ChapterWritingInput, Evidence, Fact, SlaTemplate, Volume, Workspace } from '../shared/types';

export type WritingPlanRow = ChapterWritingInput & { id?: string; title: string; volume: Volume; assignee_id?: string | null };

export function writingPlanRows(workspace: Workspace): WritingPlanRow[] {
  return workspace.chapters.map(chapter => {
    const saved = workspace.writing_plan?.chapters.find(item => item.id === chapter.id) ?? chapter.writing_input;
    return { id: chapter.id, title: chapter.title, volume: chapter.volume, ...(chapter.assignee_id !== undefined ? { assignee_id: chapter.assignee_id } : {}), fact_ids: [...(saved?.fact_ids ?? [])], writing_points: saved?.writing_points ?? '', target_length: saved?.target_length ?? null };
  });
}

export function writingPlanPayload(rows: WritingPlanRow[]) {
  return rows.map(row => {
    const target = row.target_length;
    if (target !== null && target !== undefined && (!Number.isInteger(target) || target < 1 || target > 100_000)) throw new Error('字数目标须是 1 至 100000 的整数；不设目标时留空。');
    return { ...(row.id ? { id: row.id } : {}), title: row.title.trim(), volume: row.volume, ...(row.assignee_id !== undefined ? { assignee_id: row.assignee_id } : {}), fact_ids: [...new Set(row.fact_ids ?? [])], writing_points: (row.writing_points ?? '').trim(), target_length: target ?? null };
  });
}

export function chapterPlanPayload(row: WritingPlanRow) {
  const normalized = writingPlanPayload([row])[0];
  return { fact_ids: normalized.fact_ids, writing_points: normalized.writing_points, target_length: normalized.target_length };
}

export function chapterPlanChanged(row: WritingPlanRow, input: ChapterWritingInput | undefined) {
  const existing = { fact_ids: input?.fact_ids ?? [], writing_points: input?.writing_points ?? '', target_length: input?.target_length ?? null };
  return JSON.stringify(chapterPlanPayload(row)) !== JSON.stringify(existing);
}

export function chapterStructureChanged(row: WritingPlanRow, chapter: { title: string; volume: Volume; assignee_id?: string | null }) {
  return row.title.trim() !== chapter.title || row.volume !== chapter.volume || (row.assignee_id ?? null) !== (chapter.assignee_id ?? null);
}

export type WritingPlanScope = Volume | 'all' | 'chapter';
export type WritingPlanResources = { library?: Evidence[]; slaTemplates?: SlaTemplate[] };
export type WritingPlanReviewBasis = { scope: WritingPlanScope; chapter_id?: string; order: string[]; rows: Record<string, string> };

// 不把项目最新 revision 当成用户已经核对过的方案；每一节保留各自的已读取内容。
function canonical(value: unknown): string {
  const stable = (item: unknown): unknown => {
    if (Array.isArray(item)) return item.map(stable);
    if (item && typeof item === 'object') return Object.fromEntries(Object.entries(item).filter(([, entry]) => entry !== undefined).sort(([left], [right]) => left.localeCompare(right)).map(([key, entry]) => [key, stable(entry)]));
    return item;
  };
  return JSON.stringify(stable(value));
}

export function planScopeChapters(workspace: Pick<Workspace, 'chapters'>, scope: WritingPlanScope, chapterId?: string) {
  return workspace.chapters.filter(chapter => scope === 'all' || (scope === 'chapter' ? chapter.id === chapterId : chapter.volume === scope));
}

export function writingPlanRowBasis(workspace: Workspace, chapter: Chapter, resources: WritingPlanResources = {}): string {
  const plan = chapter.writing_input ?? { fact_ids: [], writing_points: '', target_length: null };
  const facts = workspace.facts.filter(fact => fact.required || plan.fact_ids.includes(fact.id));
  const requirements = workspace.requirements.filter(requirement => requirement.chapter_id === chapter.id || chapter.requirement_ids?.includes(requirement.id));
  const evidenceIds = new Set(requirements.flatMap(requirement => requirement.evidence_ids));
  const fileIds = new Set([...facts.map(fact => fact.source?.file_id), ...requirements.map(requirement => requirement.source?.file_id)].filter(Boolean));
  const ownerId = workspace.team?.volumes.find(volume => volume.volume === chapter.volume)?.owner_id ?? null;
  const assignedPeople = new Set([ownerId, chapter.assignee_id, plan.confirmed_by]);
  return canonical({
    chapter: { id: chapter.id, title: chapter.title, volume: chapter.volume, assignee_id: chapter.assignee_id ?? null },
    plan,
    project: { id: workspace.project.id, name: workspace.project.name, tender_number: workspace.project.tender_number ?? '', deadline: workspace.project.deadline ?? null, sensitive: !!workspace.project.sensitive },
    owner_id: ownerId,
    members: (workspace.team?.members ?? []).filter(member => assignedPeople.has(member.user_id)).map(member => ({ user_id: member.user_id, company_role: member.company_role, project_role: member.project_role, volumes: member.volumes })).sort((left, right) => left.user_id.localeCompare(right.user_id)),
    facts: facts.slice().sort((left, right) => left.id.localeCompare(right.id)),
    requirements: requirements.map(({ permissions: _permissions, ...requirement }) => requirement).sort((left, right) => left.id.localeCompare(right.id)),
    conflicts: workspace.conflicts.filter(conflict => conflict.fact_ids.some(id => facts.some(fact => fact.id === id))).slice().sort((left, right) => left.id.localeCompare(right.id)),
    files: workspace.files.filter(file => fileIds.has(file.id)).map(file => ({ id: file.id, filename: file.filename, sha256: file.sha256, status: file.status, page_count: file.page_count, pagination: file.pagination, warnings: file.warnings })).sort((left, right) => left.id.localeCompare(right.id)),
    evidence: (resources.library ?? []).filter(evidence => evidenceIds.has(evidence.id)).slice().sort((left, right) => left.id.localeCompare(right.id)),
    sla: workspace.sla ? { template_id: workspace.sla.template_id, template_name: workspace.sla.template_name, template_revision: workspace.sla.template_revision, template_stale: workspace.sla.template_stale, rows: workspace.sla.rows } : null,
    templates: (resources.slaTemplates ?? []).filter(template => template.id === workspace.sla?.template_id),
  });
}

export function capturePlanReviewBasis(workspace: Workspace, scope: WritingPlanScope, chapterId?: string, resources: WritingPlanResources = {}): WritingPlanReviewBasis {
  const chapters = planScopeChapters(workspace, scope, chapterId);
  return { scope, chapter_id: chapterId, order: chapters.map(chapter => chapter.id), rows: Object.fromEntries(chapters.map(chapter => [chapter.id, writingPlanRowBasis(workspace, chapter, resources)])) };
}

export function planReviewRowProblem(basis: WritingPlanReviewBasis | null, chapterId: string, workspace: Workspace, resources: WritingPlanResources = {}): string | null {
  const chapter = workspace.chapters.find(item => item.id === chapterId);
  if (!basis?.rows[chapterId] || !chapter) return '本节已被移除、移册或尚未核对，请先核对并载入最新方案。当前填写内容仍保留。';
  if (basis.rows[chapterId] !== writingPlanRowBasis(workspace, chapter, resources)) return '后台本节的结构、人员、写作方案或相关来源已经变化。当前填写内容保留，保存和确认暂停；请先核对并载入最新本节方案。';
  return null;
}

export function planReviewScopeProblem(basis: WritingPlanReviewBasis | null, workspace: Workspace, resources: WritingPlanResources = {}): string | null {
  if (!basis) return '尚未读取这个范围的方案，请先核对并载入。';
  const order = planScopeChapters(workspace, basis.scope, basis.chapter_id).map(chapter => chapter.id);
  if (canonical(order) !== canonical(basis.order)) return '后台这个范围的章节顺序或章节清单已经变化。当前表单保留，批量确认暂停；请先核对并载入最新范围方案。';
  for (const chapterId of basis.order) {
    const problem = planReviewRowProblem(basis, chapterId, workspace, resources);
    if (problem) return problem;
  }
  return null;
}

export function advancePlanReviewRow(basis: WritingPlanReviewBasis, workspace: Workspace, savedChapter: Chapter, resources: WritingPlanResources = {}): WritingPlanReviewBasis {
  if (!basis.rows[savedChapter.id]) throw new Error('保存结果不属于本次已核对的章节，请重新核对方案。');
  return { ...basis, rows: { ...basis.rows, [savedChapter.id]: writingPlanRowBasis(workspace, savedChapter, resources) } };
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
