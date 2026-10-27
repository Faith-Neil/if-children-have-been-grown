// 为什么有这个文件：定义任务中心与顶栏角标的核心数据模型、归一化算法、四状态筛选与操作权限判定。
// 它解决什么问题：
// 1. 将业务端零散的 Job 与丰富流式 JobProgressData 统一归一化为标准的 TaskItem；
// 2. 准确统计公司维度内“运行中 + 排队中”的任务数，为顶栏 Badge 提供可信角标计数；
// 3. 实现全部、运行中、已完成、异常失败四分类筛选与计数；
// 4. 严格校验 allowedActions，确保仅在任务失败时允许重试（retry）、仅在进行中/排队时允许取消（cancel）；
// 5. 继承 JobProgress 的 AI 紫色色彩隔离与工单耗时/时间格式化规范。

import {
  isAiJob,
  getJobTypeLabel,
  formatDuration,
  resolveJobStatusMeta,
  resolveProgressStrokeColor,
  type JobProgressData,
  type JobStatus,
  type JobStep,
} from '../status/job-progress.ts';
import type { Job } from '../shared/types.ts';

export type TaskFilterKey = 'all' | 'running' | 'completed' | 'failed';

export type TaskStatus =
  | 'pending'
  | 'queued'
  | 'running'
  | 'completed'
  | 'succeeded'
  | 'failed'
  | 'cancelled';

/**
 * 任务中心统一展示项结构
 */
export interface TaskItem {
  id: string;
  jobId: string;
  type: string;
  title: string;
  projectId?: string;
  projectName?: string;
  status: TaskStatus;
  progress: number; // 0-100
  currentStepTitle?: string;
  message?: string;
  createdAt?: string;
  completedAt?: string;
  durationMs?: number;
  isAi: boolean;
  allowedActions: Array<'retry' | 'cancel'>;
  error?: { code?: string; message?: string } | null;
  errorCode?: string;
  errorMessage?: string;
  errorSummary?: string;
  traceId?: string;
  companyId?: string;
  steps?: JobStep[];
  queueReason?: string;
}

export interface TaskCounts {
  all: number;
  running: number;
  completed: number;
  failed: number;
}

/**
 * 宽松兼容的原始任务输入格式（支持 shared/Job、status/JobProgressData 及任意扩展字典）
 */
export interface RawTaskInput {
  id?: string;
  jobId?: string;
  type?: string;
  jobType?: string;
  title?: string;
  status?: string;
  progress?: number;
  percent?: number;
  message?: string;
  description?: string;
  projectId?: string;
  project_id?: string;
  projectName?: string;
  project_name?: string;
  createdAt?: string;
  created_at?: string;
  startedAt?: string;
  completedAt?: string;
  completed_at?: string;
  finishedAt?: string;
  durationMs?: number;
  isAi?: boolean;
  allowedActions?: Array<'retry' | 'cancel'>;
  error?: { code?: string; message?: string } | null;
  errorCode?: string;
  errorMessage?: string;
  errorSummary?: string;
  traceId?: string;
  companyId?: string;
  company_id?: string;
  steps?: JobStep[];
  queueReason?: string;
  currentStepKey?: string;
  currentStepTitle?: string;
  [key: string]: unknown;
}

/**
 * 判断任务是否属于“运行中 / 排队中”
 */
export function isTaskRunning(status: string): boolean {
  const s = (status || '').toLowerCase().trim();
  return s === 'running' || s === 'pending' || s === 'queued';
}

/**
 * 判断任务是否属于“已完成”
 */
export function isTaskCompleted(status: string): boolean {
  const s = (status || '').toLowerCase().trim();
  return s === 'completed' || s === 'succeeded';
}

/**
 * 判断任务是否属于“异常失败”
 */
export function isTaskFailed(status: string): boolean {
  const s = (status || '').toLowerCase().trim();
  return s === 'failed';
}

/**
 * 判断任务是否已取消
 */
export function isTaskCancelled(status: string): boolean {
  const s = (status || '').toLowerCase().trim();
  return s === 'cancelled';
}

/**
 * 格式化 ISO 字符串为简要可读时间 (MM-DD HH:mm:ss 或 HH:mm)
 */
export function formatTaskTime(timeStr?: string): string {
  if (!timeStr) return '-';
  try {
    const d = new Date(timeStr);
    if (Number.isNaN(d.getTime())) return timeStr;
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    const seconds = String(d.getSeconds()).padStart(2, '0');
    return `${month}-${day} ${hours}:${minutes}:${seconds}`;
  } catch {
    return timeStr;
  }
}

/**
 * 计算两个时间戳之间的毫秒差
 */
function deriveDurationBetween(startStr?: string, endStr?: string): number | undefined {
  if (!startStr) return undefined;
  try {
    const s = new Date(startStr).getTime();
    if (Number.isNaN(s)) return undefined;
    const e = endStr ? new Date(endStr).getTime() : Date.now();
    if (Number.isNaN(e) || e < s) return undefined;
    return e - s;
  } catch {
    return undefined;
  }
}

/**
 * 将任意原始任务对象（兼容 shared Job 与 status JobProgressData）归一化为标准的 TaskItem
 */
export function normalizeTask(
  raw: RawTaskInput
): TaskItem {
  const id = raw.id || raw.jobId || '';
  const type = raw.type || raw.jobType || 'generation';
  const explicitIsAi = raw.isAi;
  const isAi = isAiJob(type, explicitIsAi);

  // 原始状态提取与规范化
  let rawStatus = (raw.status || 'pending').toLowerCase();
  let status: TaskStatus = 'pending';
  if (rawStatus === 'running') status = 'running';
  else if (rawStatus === 'queued' || rawStatus === 'pending') status = 'pending';
  else if (rawStatus === 'completed' || rawStatus === 'succeeded') status = 'completed';
  else if (rawStatus === 'failed') status = 'failed';
  else if (rawStatus === 'cancelled') status = 'cancelled';

  // 进度百分比提取与 0-100 钳位
  const rawProgress = typeof raw.progress === 'number' ? raw.progress : raw.percent;
  let progress = 0;
  if (status === 'completed') {
    progress = 100;
  } else if (typeof rawProgress === 'number' && !Number.isNaN(rawProgress)) {
    progress = Math.min(100, Math.max(0, Math.round(rawProgress)));
  }

  // 标题推导
  const title = raw.title || getJobTypeLabel(type);

  // 项目信息
  const projectId = raw.projectId || raw.project_id || undefined;
  const projectName = raw.projectName || raw.project_name || undefined;

  // 时间与耗时
  const createdAt = raw.createdAt || raw.created_at || raw.startedAt;
  const completedAt = raw.completedAt || raw.completed_at || raw.finishedAt;
  let durationMs = raw.durationMs;
  if (typeof durationMs !== 'number' || durationMs < 0) {
    durationMs = deriveDurationBetween(createdAt, completedAt);
  }

  // 步骤推导
  const steps = raw.steps || [];
  let currentStepTitle = raw.currentStepTitle;
  if (!currentStepTitle) {
    if (raw.currentStepKey && steps.length > 0) {
      const found = steps.find(s => s.key === raw.currentStepKey);
      if (found) currentStepTitle = found.title;
    }
    if (!currentStepTitle && steps.length > 0) {
      const activeStep = steps.find(s => s.status === 'running') || steps.find(s => s.status === 'failed');
      if (activeStep) currentStepTitle = activeStep.title;
    }
  }

  // 错误信息与追踪号
  let errorCode = raw.errorCode;
  let errorMessage = raw.errorMessage;
  if (!errorCode && raw.error && typeof raw.error === 'object') {
    errorCode = raw.error.code;
  }
  if (!errorMessage && raw.error && typeof raw.error === 'object') {
    errorMessage = raw.error.message;
  }
  const errorSummary = raw.errorSummary;
  const traceId = raw.traceId;

  // 允许操作判定 (allowedActions)
  let allowedActions: Array<'retry' | 'cancel'> = [];
  if (Array.isArray(raw.allowedActions)) {
    allowedActions = raw.allowedActions.filter(
      act => act === 'retry' || act === 'cancel'
    );
  } else {
    // 默认行为：运行中/等待中可取消，失败时可重试
    if (isTaskRunning(status)) {
      allowedActions.push('cancel');
    }
    if (isTaskFailed(status)) {
      allowedActions.push('retry');
    }
  }

  const companyId = raw.companyId || raw.company_id || undefined;

  return {
    id,
    jobId: id,
    type,
    title,
    projectId,
    projectName,
    status,
    progress,
    currentStepTitle,
    message: raw.message || raw.description,
    createdAt,
    completedAt,
    durationMs,
    isAi,
    allowedActions,
    error: raw.error,
    errorCode,
    errorMessage,
    errorSummary,
    traceId,
    companyId,
    steps,
    queueReason: raw.queueReason,
  };
}

/**
 * 统计指定公司/全量任务列表中各分类的数量
 */
export function computeTaskCounts(tasks: TaskItem[], companyId?: string): TaskCounts {
  let list = tasks;
  if (companyId) {
    list = list.filter(t => !t.companyId || t.companyId === companyId);
  }

  let running = 0;
  let completed = 0;
  let failed = 0;

  for (const item of list) {
    if (isTaskRunning(item.status)) {
      running += 1;
    } else if (isTaskCompleted(item.status)) {
      completed += 1;
    } else if (isTaskFailed(item.status)) {
      failed += 1;
    }
  }

  return {
    all: list.length,
    running,
    completed,
    failed,
  };
}

/**
 * 计算顶栏任务角标计数：当前公司运行中 (running) + 排队中 (pending/queued) 的任务总数
 */
export function calculateActiveTaskCount(
  tasks: RawTaskInput[],
  companyId?: string
): number {
  if (!Array.isArray(tasks) || tasks.length === 0) {
    return 0;
  }

  let count = 0;
  for (const raw of tasks) {
    if (!raw) continue;
    const taskCompany = raw.companyId || raw.company_id;
    if (companyId && taskCompany && taskCompany !== companyId) {
      continue;
    }
    const rawStatus = (raw.status || '').toLowerCase().trim();
    if (isTaskRunning(rawStatus)) {
      count += 1;
    }
  }
  return count;
}

/**
 * 根据指定分类、公司范围与关键词多维筛选任务
 */
export function filterTasks(
  tasks: TaskItem[],
  filter: TaskFilterKey,
  options?: {
    companyId?: string;
    projectId?: string;
    searchQuery?: string;
  }
): TaskItem[] {
  if (!Array.isArray(tasks)) return [];

  return tasks.filter(task => {
    // 1. 公司隔离
    if (options?.companyId && task.companyId && task.companyId !== options.companyId) {
      return false;
    }

    // 2. 项目筛选
    if (options?.projectId && task.projectId && task.projectId !== options.projectId) {
      return false;
    }

    // 3. 四分类筛选
    if (filter === 'running') {
      if (!isTaskRunning(task.status)) return false;
    } else if (filter === 'completed') {
      if (!isTaskCompleted(task.status)) return false;
    } else if (filter === 'failed') {
      if (!isTaskFailed(task.status)) return false;
    }

    // 4. 关键词搜索
    if (options?.searchQuery) {
      const q = options.searchQuery.trim().toLowerCase();
      if (q) {
        const matchesTitle = task.title.toLowerCase().includes(q);
        const matchesType = (getJobTypeLabel(task.type) || task.type).toLowerCase().includes(q);
        const matchesMsg = (task.message || '').toLowerCase().includes(q);
        const matchesProj = (task.projectName || task.projectId || '').toLowerCase().includes(q);
        const matchesStep = (task.currentStepTitle || '').toLowerCase().includes(q);
        if (!matchesTitle && !matchesType && !matchesMsg && !matchesProj && !matchesStep) {
          return false;
        }
      }
    }

    return true;
  });
}

/**
 * 校验是否允许对任务执行特定操作（重试 retry 或 取消 cancel）
 */
export function canPerformTaskAction(
  task: TaskItem,
  action: 'retry' | 'cancel'
): boolean {
  if (!task.allowedActions || !task.allowedActions.includes(action)) {
    return false;
  }
  if (action === 'retry') {
    return isTaskFailed(task.status);
  }
  if (action === 'cancel') {
    return isTaskRunning(task.status);
  }
  return false;
}

export {
  isAiJob,
  getJobTypeLabel,
  formatDuration,
  resolveJobStatusMeta,
  resolveProgressStrokeColor,
};
