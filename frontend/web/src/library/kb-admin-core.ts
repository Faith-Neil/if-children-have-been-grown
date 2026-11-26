// 为什么有这个文件：知识库管理页的纯逻辑：角色判定、接口地址、设置表单与提示文案。
// 它解决什么问题：把“谁能看、谁能改、哪些操作危险”放在一处，页面与测试共用，避免界面和后端口径不一致。

import { normalizeSystemRole } from '../shared/roles.ts';

export type KbKind = 'history' | 'materials';
export type MaterialSubKind = 'manuals' | 'fault_cases' | 'products' | 'materials';
export type KbPhysicalKind = KbKind | 'manuals' | 'fault_cases' | 'products';
export type KbSearchKind = KbPhysicalKind;

export const KB_KIND_LABEL: Record<KbKind, string> = {
  history: '历史标书',
  materials: '资料库',
};

export const MATERIAL_SUBKIND_LABEL: Record<MaterialSubKind, string> = {
  manuals: '文档/运维手册',
  fault_cases: '故障案例',
  products: '产品手册/参数',
  materials: '综合资料（兼容库）',
};

export const FOUR_KB_DEPLOY_KINDS: KbPhysicalKind[] = ['history', 'manuals', 'fault_cases', 'products'];

export const KB_KIND_HINT: Record<KbPhysicalKind, string> = {
  history: '上传历史投标/响应文件原件（入库前自动去实体化脱敏旧甲方、旧项目名、编号与金额）。检索结果仅作行文结构参考，严禁照抄实体数据。',
  materials: '兼容历史已上传的综合企业资料库，建议新资料按「文档/运维手册、故障案例、产品手册/参数」分库投递。',
  manuals: '上传运维手册、操作指南与标准 SOP（pdf/docx/doc/md），按章节层级切块并保留面包屑路径。',
  fault_cases: '上传故障案例文档或 Excel/CSV 台账（自动带表头逐行切块并衍生招标式应急问法）。',
  products: '上传产品白皮书、规格书或多型号对比参数表（对比表自动带表头按型号拆块，杜绝跨型号参数混用）。',
};

export const HISTORY_UPLOAD_ACCEPT = '.pdf,.docx,.doc';

export const KB_UPLOAD_ACCEPT: Record<KbKind, string> = {
  history: HISTORY_UPLOAD_ACCEPT,
  materials: '.pdf,.docx,.doc,.xls,.xlsx,.ppt,.pptx',
};

export const PHYSICAL_UPLOAD_ACCEPT: Record<KbPhysicalKind, string> = {
  history: HISTORY_UPLOAD_ACCEPT,
  materials: '.pdf,.docx,.doc,.xls,.xlsx,.csv,.ppt,.pptx,.md,.txt',
  manuals: '.pdf,.docx,.doc,.md,.txt',
  fault_cases: '.pdf,.docx,.doc,.xls,.xlsx,.csv,.md,.txt',
  products: '.pdf,.docx,.doc,.xls,.xlsx,.csv,.ppt,.pptx,.md,.txt',
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

const WRITE = new Set(['company_admin', 'platform_admin']);
const CONNECTION = new Set(['company_admin', 'platform_admin']);

export function kbPermissions(role?: string | null) {
  if (!role) return { read: false, write: false, connection: false };
  const normalized = normalizeSystemRole(role);
  return {
    read: normalized === 'member' || normalized === 'company_admin' || normalized === 'platform_admin',
    write: WRITE.has(normalized),
    connection: CONNECTION.has(normalized),
  };
}

/** 历史标书：公司管理员或任一项目负责人可追加；资料库只给公司管理员。 */
export function canUploadHistory(role?: string | null, leadsProject = false, kind: KbPhysicalKind = 'history') {
  return kbPermissions(role).write || (kind === 'history' && leadsProject);
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
  documents: (kind: KbPhysicalKind, page = 1) => `/api/v1/kb-admin/datasets/${kind}/documents?page=${page}&page_size=30`,
  document: (kind: KbPhysicalKind, id: string) => `/api/v1/kb-admin/datasets/${kind}/documents/${encodeURIComponent(id)}`,
  chunks: (kind: KbPhysicalKind, id: string) => `/api/v1/kb-admin/datasets/${kind}/documents/${encodeURIComponent(id)}/chunks?page_size=50`,
  chunk: (kind: KbPhysicalKind, id: string, chunk: string) =>
    `/api/v1/kb-admin/datasets/${kind}/documents/${encodeURIComponent(id)}/chunks/${encodeURIComponent(chunk)}`,
  datasetAction: (kind: KbPhysicalKind, action: 'ensure' | 'reparse' | 'rebuild') => `/api/v1/kb-admin/datasets/${kind}/${action}`,
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
