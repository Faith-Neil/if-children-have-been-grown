// 为什么有这个文件：定义后台任务与进度条的核心状态机、AI 任务判定规则、进度自动推导算法与色彩规范。
// 它解决什么问题：让长任务的状态流转、子步骤聚合、AI 紫色彩隔离与耗时格式化可脱离 DOM 纯逻辑运行与全面单测。

export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
export type JobStepStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

/**
 * PRD v1.8 与 数据字典 4.16 约定的后台长任务类型
 */
export type JobType =
  // AI 模型与智能生成类任务
  | 'generate_chapter'
  | 'generate_outline'
  | 'chapter_summary'
  | 'model_review'
  | 'model_review_batch'
  | 'assistant_qa'
  | 'assistant_suggest'
  | 'ragflow_retrieval'
  | 'evidence_matching'
  | 'matrix_match'
  | 'attachment_recognize'
  | 'generation'
  | 'loop'
  // 普通业务类任务（严禁出现紫色）
  | 'export'
  | 'bid_export'
  | 'compliance'
  | 'compliance_check'
  | 'incremental_check'
  | 'dup_check'
  | 'kb_import'
  | 'kb_rebuild'
  | 'kb_reconcile'
  | 'fp_build'
  | 'lock_sweep'
  | 'cleanup'
  | 'audit_anchor'
  | 'tender_index_build'
  | 'archive_import'
  | 'kb_sync'
  | 'daily_expiry'
  | 'health_check'
  | (string & {});

/**
 * 严格锁定的色彩令牌，符合 WCAG AA 4.5:1 对比度标准
 */
export const JOB_PROGRESS_COLORS = {
  aiProgress: '#722ed1', // 专属 AI 紫色（严禁非 AI 业务使用）
  aiProgressLight: '#f9f0ff',
  aiBorder: '#d3adf7',
  defaultProgress: '#1e4db7', // 默认业务主蓝色
  success: '#52c41a', // 成功绿色
  error: '#ff4d4f', // 失败红色
  cancelled: '#8c8c8c', // 已取消灰色
  pending: '#faad14', // 排队等待橙黄色
  text: '#1d2129',
  muted: '#4e5969',
} as const;

/**
 * 内置 AI 任务类型集合
 */
export const AI_JOB_TYPES: ReadonlySet<string> = new Set([
  'generate_chapter',
  'generate_outline',
  'chapter_summary',
  'model_review',
  'model_review_batch',
  'assistant_qa',
  'assistant_suggest',
  'ragflow_retrieval',
  'evidence_matching',
  'matrix_match',
  'attachment_recognize',
  'generation',
  'loop',
]);

/**
 * 判断指定任务类型或显式标志是否属于 AI 任务
 * 规则：若传显式 isAi 则优先遵从；否则匹配 AI_JOB_TYPES 内置集合；非 AI 严禁返回 true。
 */
export function isAiJob(jobType?: string, explicitIsAi?: boolean): boolean {
  if (typeof explicitIsAi === 'boolean') {
    return explicitIsAi;
  }
  if (!jobType) {
    return false;
  }
  const normalized = jobType.trim().toLowerCase();
  if (AI_JOB_TYPES.has(normalized)) {
    return true;
  }
  // 识别 ai_ 或 model_ 前缀
  if (normalized.startsWith('ai_') || normalized.startsWith('model_')) {
    return true;
  }
  return false;
}

/**
 * 子步骤结构定义
 */
export interface JobStep {
  key: string;
  title: string;
  status: JobStepStatus;
  description?: string;
  durationMs?: number;
  percent?: number; // 0-100 子步骤百分比
  isAi?: boolean; // 步骤是否由 AI 模型执行
  errorCode?: string;
  errorMessage?: string;
}

/**
 * 后台长任务进度完整数据结构
 */
export interface JobProgressData {
  jobId: string;
  jobType: JobType;
  status: JobStatus;
  percent?: number; // 若缺省则通过 steps 派生
  steps?: JobStep[];
  currentStepKey?: string;
  title?: string;
  description?: string;
  queueReason?: string;
  errorCode?: string;
  errorMessage?: string;
  errorSummary?: string;
  traceId?: string;
  durationMs?: number;
  isAi?: boolean; // 显式声明是否为 AI 任务
  allowedActions?: Array<'retry' | 'cancel'>;
  createdAt?: string;
  startedAt?: string;
  finishedAt?: string;
}

/**
 * 进度条色彩判定函数：严格根据任务状态与 AI 属性分配色值
 */
export function resolveProgressStrokeColor(
  status: JobStatus,
  isAi: boolean
): string {
  switch (status) {
    case 'failed':
      return JOB_PROGRESS_COLORS.error;
    case 'completed':
      return JOB_PROGRESS_COLORS.success;
    case 'cancelled':
      return JOB_PROGRESS_COLORS.cancelled;
    case 'pending':
    case 'running':
    default:
      return isAi ? JOB_PROGRESS_COLORS.aiProgress : JOB_PROGRESS_COLORS.defaultProgress;
  }
}

/**
 * 自动计算推导长任务总体进度（0-100 整数）
 * 1. 若任务已完成 (completed)，直接返回 100；
 * 2. 若传入显式 explicitPercent，限制在 0-100 整数区间；
 * 3. 若未传显式 percent，则基于 steps 列表加权/平均计算；
 * 4. 若无 steps，则根据当前状态返回基准进度。
 */
export function deriveJobProgress(params: {
  status: JobStatus;
  explicitPercent?: number;
  steps?: JobStep[];
}): number {
  const { status, explicitPercent, steps } = params;

  if (status === 'completed') {
    return 100;
  }

  if (typeof explicitPercent === 'number' && !Number.isNaN(explicitPercent)) {
    return Math.min(100, Math.max(0, Math.round(explicitPercent)));
  }

  if (!steps || steps.length === 0) {
    switch (status) {
      case 'pending':
      case 'cancelled':
      case 'failed':
        return 0;
      case 'running':
        return 0;
      default:
        return 0;
    }
  }

  const totalSteps = steps.length;
  let totalScore = 0;

  for (const step of steps) {
    if (step.status === 'completed') {
      totalScore += 100;
    } else if (step.status === 'running') {
      if (typeof step.percent === 'number' && !Number.isNaN(step.percent)) {
        totalScore += Math.min(100, Math.max(0, step.percent));
      } else {
        totalScore += 50; // 执行中默认给 50% 单步进度
      }
    } else if (typeof step.percent === 'number' && !Number.isNaN(step.percent)) {
      totalScore += Math.min(100, Math.max(0, step.percent));
    }
  }

  const derived = Math.round(totalScore / totalSteps);
  return Math.min(100, Math.max(0, derived));
}

export interface JobStatusMeta {
  status: JobStatus;
  text: string;
  badgeStatus: 'default' | 'processing' | 'success' | 'error' | 'warning';
  progressStatus: 'normal' | 'active' | 'success' | 'exception';
  color: string;
}

/**
 * 状态元信息解析纯函数
 */
export function resolveJobStatusMeta(status: JobStatus): JobStatusMeta {
  switch (status) {
    case 'pending':
      return {
        status: 'pending',
        text: '等待中',
        badgeStatus: 'warning',
        progressStatus: 'normal',
        color: JOB_PROGRESS_COLORS.pending,
      };
    case 'running':
      return {
        status: 'running',
        text: '执行中',
        badgeStatus: 'processing',
        progressStatus: 'active',
        color: JOB_PROGRESS_COLORS.defaultProgress,
      };
    case 'completed':
      return {
        status: 'completed',
        text: '已完成',
        badgeStatus: 'success',
        progressStatus: 'success',
        color: JOB_PROGRESS_COLORS.success,
      };
    case 'failed':
      return {
        status: 'failed',
        text: '执行失败',
        badgeStatus: 'error',
        progressStatus: 'exception',
        color: JOB_PROGRESS_COLORS.error,
      };
    case 'cancelled':
      return {
        status: 'cancelled',
        text: '已取消',
        badgeStatus: 'default',
        progressStatus: 'normal',
        color: JOB_PROGRESS_COLORS.cancelled,
      };
    default:
      return {
        status: 'pending',
        text: '未知状态',
        badgeStatus: 'default',
        progressStatus: 'normal',
        color: JOB_PROGRESS_COLORS.muted,
      };
  }
}

/**
 * 耗时毫秒数格式化友好字符串
 */
export function formatDuration(durationMs?: number): string {
  if (typeof durationMs !== 'number' || Number.isNaN(durationMs) || durationMs < 0) {
    return '-';
  }
  if (durationMs < 1000) {
    return `${Math.round(durationMs)}ms`;
  }
  if (durationMs < 60000) {
    return `${(durationMs / 1000).toFixed(1)}s`;
  }
  const totalSeconds = Math.floor(durationMs / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const remainingSeconds = totalSeconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}

/**
 * 任务类型中文名称与标签字典
 */
export const JOB_TYPE_LABELS: Record<string, string> = {
  generate_chapter: '章节生成',
  generate_outline: '方案大纲生成',
  chapter_summary: '章节摘要抽取',
  model_review: '模型评审',
  model_review_batch: '模型批量评审',
  assistant_qa: '智能对话问答',
  assistant_suggest: 'AI 写作建议',
  ragflow_retrieval: '知识库检索',
  evidence_matching: '证据材料匹配',
  matrix_match: '响应矩阵匹配',
  attachment_recognize: '附件智能识别',
  generation: '智能生成',
  loop: '章节循环生成',
  export: '文档导出',
  bid_export: '标书整本导出',
  compliance: '合规检查',
  compliance_check: '标书合规审查',
  incremental_check: '增量变更复查',
  dup_check: '查重与相似度',
  kb_import: '知识库批量导入',
  kb_rebuild: '检索索引重建',
  kb_reconcile: '检索库对账',
  fp_build: '文本指纹构建',
  lock_sweep: '编辑锁清理',
  cleanup: '过期数据清理',
  audit_anchor: '审计锚点导出',
  tender_index_build: '招标文件索引构建',
  archive_import: '历史标书归档导入',
  kb_sync: '检索库增量同步',
  daily_expiry: '每日到期计算',
  health_check: '服务健康检测',
};

export function getJobTypeLabel(jobType: string): string {
  if (!jobType) return '后台任务';
  return JOB_TYPE_LABELS[jobType] || jobType;
}
