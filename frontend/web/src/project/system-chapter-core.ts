// 为什么有这个文件：识别五类系统生成章节（APP-M2-T191～T195）并给出接口路径。
// 它解决什么问题：这些章节只能按数据源生成，编辑台必须只读，并提示去矩阵、事实或资料库修改。
const KINDS: [string, string, string[]][] = [
  ['point_to_point', '点对点应答', ['点对点应答', '逐条应答', '逐条响应']],
  ['review_index', '评审索引表', ['评审索引', '评分索引', '索引表']],
  ['deviation', '偏离表', ['偏离表']],
  ['service_plan', '年度服务计划表', ['年度服务计划', '服务计划表']],
  ['proof_list', '证明材料清单', ['证明材料清单']],
];

export function systemChapterKind(title?: string | null): { kind: string; label: string } | null {
  const match = KINDS.find(([, , words]) => words.some(word => (title ?? '').includes(word)));
  return match ? { kind: match[0], label: match[1] } : null;
}

export const SOURCE_TAB: Record<string, string> = {
  point_to_point: 'matrix', review_index: 'matrix', deviation: 'matrix', service_plan: 'facts', proof_list: 'matrix',
};

export const systemPaths = {
  preview: (projectId: string, chapterId: string) => `/api/v1/projects/${encodeURIComponent(projectId)}/chapters/${encodeURIComponent(chapterId)}/system`,
  generate: (projectId: string, chapterId: string) => `/api/v1/projects/${encodeURIComponent(projectId)}/chapters/${encodeURIComponent(chapterId)}/system/generate`,
};
