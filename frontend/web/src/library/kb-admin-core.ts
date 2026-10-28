// 为什么有这个文件：知识库管理页的纯逻辑：角色判定、接口地址、设置表单与提示文案。
// 它解决什么问题：把“谁能看、谁能改、哪些操作危险”放在一处，页面与测试共用，避免界面和后端口径不一致。

export type KbKind = 'library' | 'history' | 'certificate';
export type KbSearchKind = 'evidence' | 'snippet' | 'history';

export const KB_KIND_LABEL: Record<KbKind, string> = {
  library: '资料与方案片段',
  history: '历史投标文件（仅参考）',
  certificate: '资质证书附件（抽取后人工核对）',
};

export const KB_KIND_HINT: Record<KbKind, string> = {
  library: '由资料库与片段发布自动同步；在此只能查看、调整分块关键词/问题或停用错误分块。',
  history: '上传历史投标/响应文件原件，按投标文件章节切块并抽取项目名称、采购人、行业等元数据。检索结果只作参考，不能挂为证据。',
  certificate: '上传证书、合同等扫描件，抽取证书名称、编号、发证机构、有效期，可一键生成“待核验”资料草稿。',
};

export const KB_UPLOAD_ACCEPT: Record<'history' | 'certificate', string> = {
  history: '.pdf,.docx,.doc,.xlsx,.xls,.csv,.md,.txt,.pptx',
  certificate: '.pdf,.png,.jpg,.jpeg,.docx',
};

const READ = new Set(['company_admin', 'data_admin', 'manager', 'project_lead', 'platform_admin', 'super_admin']);
const WRITE = new Set(['company_admin', 'data_admin', 'platform_admin', 'super_admin']);
const CONNECTION = new Set(['company_admin', 'platform_admin', 'super_admin']);

export function kbPermissions(role?: string | null) {
  const r = role ?? '';
  return { read: READ.has(r), write: WRITE.has(r), connection: CONNECTION.has(r) };
}

export const kbApi = {
  overview: '/api/v1/kb-admin/overview',
  models: '/api/v1/kb-admin/models',
  settings: '/api/v1/kb-admin/settings',
  pipelines: '/api/v1/kb-admin/pipelines',
  deploy: '/api/v1/kb-admin/pipelines/deploy',
  datasets: '/api/v1/kb-admin/datasets',
  retrieval: '/api/v1/kb-admin/retrieval-test',
  audit: '/api/v1/kb-admin/audit?limit=100',
  documents: (kind: KbKind, page = 1) => `/api/v1/kb-admin/datasets/${kind}/documents?page=${page}&page_size=30`,
  document: (kind: KbKind, id: string) => `/api/v1/kb-admin/datasets/${kind}/documents/${encodeURIComponent(id)}`,
  chunks: (kind: KbKind, id: string) => `/api/v1/kb-admin/datasets/${kind}/documents/${encodeURIComponent(id)}/chunks?page_size=50`,
  chunk: (kind: KbKind, id: string, chunk: string) =>
    `/api/v1/kb-admin/datasets/${kind}/documents/${encodeURIComponent(id)}/chunks/${encodeURIComponent(chunk)}`,
  datasetAction: (kind: KbKind, action: 'ensure' | 'reparse' | 'rebuild') => `/api/v1/kb-admin/datasets/${kind}/${action}`,
  certificateDraft: (id: string) => `/api/v1/kb-admin/certificates/${encodeURIComponent(id)}/library-draft`,
};

export interface KbSettings {
  revision: number;
  embedding_model: string;
  rerank_id: string;
  llm_id: string;
  similarity_threshold: number;
  keywords_weight: number;
  use_pipelines: boolean;
  language: string;
  profiles: Record<string, Record<string, unknown>>;
}

/** 只提交改动过的字段，避免把别人刚改的值覆盖回去。 */
export function settingsDiff(before: KbSettings, after: Partial<KbSettings>): Partial<KbSettings> {
  const diff: Partial<KbSettings> = {};
  for (const key of ['embedding_model', 'rerank_id', 'llm_id', 'similarity_threshold', 'keywords_weight', 'use_pipelines'] as const) {
    if (after[key] !== undefined && after[key] !== before[key]) (diff as Record<string, unknown>)[key] = after[key];
  }
  return diff;
}

export function embeddingChangeWarning(before: KbSettings, diff: Partial<KbSettings>): string {
  return diff.embedding_model !== undefined && before.embedding_model !== diff.embedding_model
    ? '更换嵌入模型后，已有数据集的向量不能再用，需要在“数据集与文档”中逐类执行“重建”。'
    : '';
}

export function datasetWarnings(info: { reparse_required?: boolean; rebuild_required?: boolean; warning?: string; mode?: string } | null | undefined): string[] {
  if (!info) return ['尚未建立'];
  const rows: string[] = [];
  if (info.rebuild_required) rows.push('嵌入模型已更换，需要重建');
  if (info.reparse_required) rows.push('摄入流程已更新，已有文档需重新解析');
  if (info.mode === 'builtin') rows.push('未使用 ICG 摄入流程（内置解析器）');
  if (info.warning) rows.push(info.warning);
  return rows;
}
