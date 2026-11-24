// 为什么有这个文件：技术服务方案写作助手的按节作用域、快捷指令与覆盖视图「去修改」预填。

import type { TechnicalOutline } from '../shared/types.ts';

export const TECH_CHIPS: { label: string; instruction: string }[] = [
  { label: '补齐未覆盖要点', instruction: '逐条补齐本节挂载要点中尚未写到的内容，每条写清做法与交付物。' },
  { label: '按五步结构重写', instruction: '按「服务目标、服务内容、实施步骤、保障措施、交付成果」五步重写本节。' },
  { label: '扩写措施', instruction: '扩写本节的具体措施：人员、工具、频次、记录与验收方式，不新增未经证实的承诺。' },
  { label: '统一承诺数字', instruction: '核对本节的时限、频次、人数等承诺数字，与招标要求和其他章节保持一致；无依据的数字标【待确认】。' },
  { label: '重新检索后重写', instruction: '结合最新检索到的历史标书与资料库内容重写本节，引用可追溯的依据。' },
];

export const sectionRewritePath = (projectId: string) =>
  `/api/v1/projects/${encodeURIComponent(projectId)}/technical-sections/rewrite`;

export type SectionOption = { key: string; label: string };

/** key 与后端节键一致（任务编号优先），同名小节各占一项。 */
export function sectionsOf(outline: TechnicalOutline | null | undefined): SectionOption[] {
  const seen = new Set<string>();
  const out: SectionOption[] = [];
  for (const item of outline?.headings ?? []) {
    const key = item.task_id || item.requirement_id;
    if (!key || seen.has(key)) continue;
    seen.add(key);
    out.push({ key, label: [item.number, item.title].filter(Boolean).join(' ') });
  }
  return out;
}

export type AssistantPrefill = { section: string; instruction: string };
const prefillKey = (projectId: string) => `icg.assistant.prefill.${projectId}`;

export function storePrefill(projectId: string, value: AssistantPrefill, store: Pick<Storage, 'setItem'> = sessionStorage) {
  store.setItem(prefillKey(projectId), JSON.stringify(value));
}

export function takePrefill(projectId: string, store: Pick<Storage, 'getItem' | 'removeItem'> = sessionStorage): AssistantPrefill | null {
  const raw = store.getItem(prefillKey(projectId));
  if (!raw) return null;
  store.removeItem(prefillKey(projectId));
  try {
    const value = JSON.parse(raw) as Partial<AssistantPrefill>;
    return typeof value.section === 'string' && typeof value.instruction === 'string' ? { section: value.section, instruction: value.instruction } : null;
  } catch {
    return null;
  }
}

export function coverageInstruction(row: { text: string; generation_status?: string | null }): string {
  if (row.generation_status === 'failed') return '本节生成失败，请按挂载要点补写本节正文。';
  return `补齐要点：「${row.text.slice(0, 80)}」，写清做法与交付物，不新增未经证实的承诺。`;
}
