// 为什么有这个文件：知识库管理页的纯逻辑：角色判定、接口地址、设置表单与提示文案。
// 它解决什么问题：把“谁能看、谁能改、哪些操作危险”放在一处，页面与测试共用，避免界面和后端口径不一致。

export type KbKind = 'history' | 'materials';
export type KbSearchKind = 'history' | 'materials';

export const KB_KIND_LABEL: Record<KbKind, string> = {
  history: '历史标书',
  materials: '资料库',
};

export const KB_KIND_HINT: Record<KbKind, string> = {
  history: '上传历史投标/响应文件原件，按投标文件章节切块并抽取项目名称、投标日期等元数据。检索结果只作参考，不能挂为证据。',
  materials: '上传企业权威资料原件（产品说明书、技术参数、企业能力说明等），按章节切块并抽取文档类型与内容角色。作为事实依据，但不单独作为投标证据。',
};

export const HISTORY_UPLOAD_ACCEPT = '.pdf,.docx,.doc';

export const KB_UPLOAD_ACCEPT: Record<KbKind, string> = {
  history: HISTORY_UPLOAD_ACCEPT,
  materials: '.pdf,.docx,.doc,.xls,.xlsx,.ppt,.pptx',
};

const SECTION_TYPE_LABELS: Record<string, string> = {
  overall_design: '总体设计',
  technical_architecture: '技术架构',
  system_function: '系统功能',
  data_security: '数据安全',
  network_security: '网络安全',
  deployment: '部署',
  implementation: '实施',
  training: '培训',
  operation_maintenance: '运维',
  quality_assurance: '质量保证',
  emergency_plan: '应急预案',
  project_schedule: '项目进度',
  project_team: '项目团队',
  project_case: '项目案例',
  other: '其他',
};

const KNOWLEDGE_TYPE_LABELS: Record<string, string> = {
  technical_solution: '技术方案',
  technical_method: '技术方法',
  implementation_experience: '实施经验',
  service_process: '服务流程',
  standard_expression: '标准表述',
  enterprise_capability: '企业能力',
  project_case_evidence: '项目案例证据',
  other: '其他',
};

const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  technical_proposal: '技术方案',
  implementation_plan: '实施计划',
  service_plan: '服务计划',
  product_manual: '产品手册',
  technical_specification: '技术规格',
  enterprise_capability: '企业能力',
  project_case: '项目案例',
  technical_standard: '技术标准',
  other: '其他',
};

const CONTENT_ROLE_LABELS: Record<string, string> = {
  bidder_response: '投标响应',
  buyer_requirement: '招标方要求',
  enterprise_fact: '企业事实',
  project_specific_commitment: '项目特定承诺',
  general_description: '通用描述',
  irrelevant_content: '无关内容',
  project_case_evidence: '项目案例证据',
  unknown: '未知',
};

const REUSABILITY_LABELS: Record<string, string> = {
  high: '高',
  medium: '中',
  low: '低',
  not_reusable: '不可复用',
};

const METADATA_VALUE_LABELS: Record<string, Record<string, string>> = {
  section_type: SECTION_TYPE_LABELS,
  technical_domain: SECTION_TYPE_LABELS,
  knowledge_type: KNOWLEDGE_TYPE_LABELS,
  document_type: DOCUMENT_TYPE_LABELS,
  content_role: CONTENT_ROLE_LABELS,
  reusability: REUSABILITY_LABELS,
};

export function metadataValueLabel(key: string, value: string): string {
  const label = METADATA_VALUE_LABELS[key]?.[value];
  return label ?? value;
}

const READ = new Set(['company_admin', 'data_admin', 'manager', 'project_lead', 'platform_admin', 'super_admin']);
const WRITE = new Set(['company_admin', 'data_admin', 'platform_admin', 'super_admin']);
const CONNECTION = new Set(['company_admin', 'platform_admin', 'super_admin']);

export function kbPermissions(role?: string | null) {
  const r = role ?? '';
  return { read: READ.has(r), write: WRITE.has(r), connection: CONNECTION.has(r) };
}

export function canUploadHistory(role?: string | null) {
  const r = role ?? '';
  return WRITE.has(r) || r === 'manager' || r === 'project_lead';
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
  certificateDocuments: (page = 1) => `/api/v1/kb-admin/datasets/certificate/documents?page=${page}&page_size=30`,
};

export const CERTIFICATE_UPLOAD_ACCEPT = '.pdf,.png,.jpg,.jpeg,.docx';

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
  for (const key of ['embedding_model', 'rerank_id', 'llm_id', 'similarity_threshold', 'keywords_weight'] as const) {
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
