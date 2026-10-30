// 为什么有这个文件：后台任务进度的实时订阅、断线重连与轮询回退（APP-M2-T020 / PRD v1.8 §5.12.4、§5.7.6）。
// 它解决什么问题：
// 1. 原实现用浏览器 EventSource，不能带登录令牌（后台只认 Authorization 头），连上即 401；
//    监听的事件名（job_progress、done…）与后台实际发出的 job.progress、job.completed 等对不上，事件全部被丢弃；
//    回退轮询不带令牌、401 时无限轮询，从任务状态取的字段（progress、queued、error）也没有换成页面用的形状。
// 2. 现在用 fetch 读事件流（带 Authorization 与 Last-Event-ID），按后台事件名更新；后台对进行中的任务保持连接最多约 25 秒后关闭，
//    这属于正常结束，带上最后的事件编号立即重连；网络出错时按 1s→2s→4s 退避重试 3 次，仍不行就改为每 2 秒查询任务状态，
//    并在页面提示“实时流已断开，已切换为定时刷新”；轮询期间每隔几次再试一次实时流，连上即恢复；任务结束即全部停止。
// 本文件不依赖 React，订阅钩子在 useJobProgressSse.ts。

import type { JobProgressData, JobStatus } from './job-progress.ts';

export type StreamConnectionStatus =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'polling'
  | 'closed'
  | 'error';

export const TERMINAL_JOB_STATUSES: ReadonlySet<string> = new Set(['completed', 'succeeded', 'failed', 'cancelled']);

export function isJobTerminalStatus(status?: string | null): boolean {
  if (!status) return false;
  return TERMINAL_JOB_STATUSES.has(status.trim().toLowerCase());
}

/** 第 1 次 1000ms、第 2 次 2000ms、第 3 次 4000ms，上限 maxMs。 */
export function calculateBackoffDelay(retryCount: number, baseMs = 1000, maxMs = 8000): number {
  if (retryCount <= 0) return 0;
  return Math.min(maxMs, baseMs * Math.pow(2, retryCount - 1));
}

export function parseSseLine(line: string): { field: string; value: string } | null {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith(':')) return null;  // 空行或注释（保活）
  const colon = trimmed.indexOf(':');
  if (colon === -1) return { field: trimmed, value: '' };
  const raw = trimmed.slice(colon + 1);
  return { field: trimmed.slice(0, colon).trim(), value: raw.startsWith(' ') ? raw.slice(1) : raw };
}

export interface ParsedSseEvent {
  event: string;
  data: any;
  id?: string;
  retry?: number;
}

/** 解析完整的事件块（以空行分隔）；不完整的末尾块请留在缓冲里，用 splitSseBuffer。 */
export function parseSseMessage(rawText: string): ParsedSseEvent[] {
  const events: ParsedSseEvent[] = [];
  for (const block of rawText.split(/\r?\n\r?\n/)) {
    if (!block.trim()) continue;
    let event = 'message';
    let data = '';
    let id: string | undefined;
    let retry: number | undefined;
    for (const line of block.split(/\r?\n/)) {
      const parsed = parseSseLine(line);
      if (!parsed) continue;
      if (parsed.field === 'event') event = parsed.value;
      else if (parsed.field === 'data') data += (data ? '\n' : '') + parsed.value;
      else if (parsed.field === 'id') id = parsed.value;
      else if (parsed.field === 'retry') { const value = parseInt(parsed.value, 10); if (!isNaN(value)) retry = value; }
    }
    if (!data) continue;
    let value: any = data;
    try { value = JSON.parse(data); } catch { /* 保留原文 */ }
    events.push({ event, data: value, id, retry });
  }
  return events;
}

/** 把缓冲切成已完整的事件块与剩余部分。 */
export function splitSseBuffer(buffer: string): { complete: string; rest: string } {
  const normalized = buffer.replace(/\r\n/g, '\n');
  const end = normalized.lastIndexOf('\n\n');
  if (end === -1) return { complete: '', rest: normalized };
  return { complete: normalized.slice(0, end + 2), rest: normalized.slice(end + 2) };
}

/** 后台任务状态（GET /api/v1/jobs/{id}，JobStatus）。 */
export interface BackendJobStatus {
  id: string;
  project_id?: string;
  type: string;
  status: string;
  progress?: number;
  message?: string;
  created_at?: string;
  completed_at?: string | null;
  error?: { code: string; message: string } | null;
  events?: BackendJobEvent[];
  allowed_actions?: string[] | null;
  allowedActions?: string[] | null;
}

export interface BackendJobEvent {
  seq: number;
  id: string;
  type: string;
  occurred_at?: string;
  payload?: Record<string, any>;
}

export function normalizeRunStatus(status: string | undefined | null): JobStatus {
  switch ((status || '').toLowerCase()) {
    case 'queued':
    case 'pending':
      return 'pending';
    case 'running':
      return 'running';
    case 'completed':
    case 'succeeded':
      return 'completed';
    case 'failed':
      return 'failed';
    case 'cancelled':
      return 'cancelled';
    default:
      return 'pending';
  }
}

function actions(list: string[] | null | undefined): Array<'retry' | 'cancel'> {
  return (list ?? []).filter((item): item is 'retry' | 'cancel' => item === 'retry' || item === 'cancel');
}

/** 后台任务状态 → 页面进度数据。 */
export function jobFromStatus(raw: BackendJobStatus): JobProgressData {
  return {
    jobId: raw.id,
    jobType: raw.type as JobProgressData['jobType'],
    status: normalizeRunStatus(raw.status),
    percent: typeof raw.progress === 'number' ? raw.progress : undefined,
    description: raw.message || undefined,
    errorCode: raw.error?.code,
    errorMessage: raw.error?.message,
    allowedActions: actions(raw.allowedActions ?? raw.allowed_actions),
    createdAt: raw.created_at,
    finishedAt: raw.completed_at ?? undefined,
  };
}

/** 按一条后台事件（job.status_changed / job.progress / job.completed / job.failed / job.cancelled）更新进度数据。 */
export function applyJobEvent(job: JobProgressData, event: BackendJobEvent): JobProgressData {
  const payload = event.payload ?? {};
  switch (event.type) {
    case 'job.status_changed': {
      const status = normalizeRunStatus(payload.to);
      return { ...job, status, allowedActions: status === 'pending' || status === 'running' ? ['cancel'] : job.allowedActions };
    }
    case 'job.progress':
      return { ...job, percent: typeof payload.progress === 'number' ? payload.progress : job.percent, description: payload.message ?? job.description };
    case 'job.completed':
      return { ...job, status: 'completed', percent: 100, finishedAt: payload.completed_at ?? job.finishedAt, allowedActions: [] };
    case 'job.failed':
      return { ...job, status: 'failed', percent: 100, errorCode: typeof payload.error === 'string' ? payload.error : job.errorCode,
        errorMessage: job.errorMessage ?? job.description, finishedAt: payload.completed_at ?? job.finishedAt, allowedActions: ['retry'] };
    case 'job.cancelled':
      return { ...job, status: 'cancelled', finishedAt: payload.completed_at ?? job.finishedAt, allowedActions: ['retry'] };
    default:
      return job;
  }
}

export interface JobStreamSubscriptionOptions {
  jobId: string;
  token?: string | null;
  baseUrl?: string;
  initialJob?: JobProgressData | null;
  maxRetries?: number;
  baseBackoffMs?: number;
  pollingIntervalMs?: number;
  /** 轮询多少次后再试一次实时流 */
  resumeEveryPolls?: number;
  /** 正常结束（后台到时关闭）后多久重连 */
  reconnectDelayMs?: number;
  fetchFn?: typeof fetch;
  onJobUpdate?: (job: JobProgressData) => void;
  onStatusChange?: (status: StreamConnectionStatus, meta: { retryCount: number; isFallback: boolean; reason?: string }) => void;
  onTerminal?: (job: JobProgressData) => void;
}

class StreamHttpError extends Error {
  status: number;
  constructor(status: number) { super(`HTTP ${status}`); this.status = status; }
}

/** 一个任务一个订阅：实时流优先，出错退避重试，耗尽后轮询，轮询中定期尝试恢复实时流。 */
export class JobStreamSubscriptionManager {
  private options: Required<Pick<JobStreamSubscriptionOptions, 'maxRetries' | 'baseBackoffMs' | 'pollingIntervalMs' | 'resumeEveryPolls' | 'reconnectDelayMs'>> & JobStreamSubscriptionOptions;
  private status: StreamConnectionStatus = 'idle';
  private job: JobProgressData | null;
  private retryCount = 0;
  private fallback = false;
  private lastEventId: string | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private abort: AbortController | null = null;
  private polls = 0;
  private stopped = false;

  constructor(options: JobStreamSubscriptionOptions) {
    this.options = { maxRetries: 3, baseBackoffMs: 1000, pollingIntervalMs: 2000, resumeEveryPolls: 5, reconnectDelayMs: 300, ...options };
    this.job = options.initialJob ?? null;
  }

  getStatus() { return this.status; }
  getRetryCount() { return this.retryCount; }
  getIsFallback() { return this.fallback; }
  getJob() { return this.job; }

  connect() {
    this.stopped = false;
    if (this.job && isJobTerminalStatus(this.job.status)) { this.setStatus('closed'); return; }
    void this.openStream();
  }

  disconnect() {
    this.stopped = true;
    this.clearTimer();
    this.abort?.abort();
    this.abort = null;
    this.setStatus('closed');
  }

  private get fetchFn(): typeof fetch {
    return this.options.fetchFn ?? ((...args: Parameters<typeof fetch>) => fetch(...args));
  }

  private url(suffix = '') {
    return `${this.options.baseUrl ?? ''}/api/v1/jobs/${encodeURIComponent(this.options.jobId)}${suffix}`;
  }

  private headers(accept: string): Record<string, string> {
    const headers: Record<string, string> = { Accept: accept };
    if (this.options.token) headers.Authorization = `Bearer ${this.options.token}`;
    return headers;
  }

  private setStatus(status: StreamConnectionStatus, reason?: string) {
    this.status = status;
    this.options.onStatusChange?.(status, { retryCount: this.retryCount, isFallback: this.fallback, reason });
  }

  private clearTimer() {
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
  }

  private later(ms: number, action: () => void) {
    this.clearTimer();
    this.timer = setTimeout(() => { this.timer = null; if (!this.stopped) action(); }, ms);
  }

  private update(next: JobProgressData) {
    this.job = next;
    this.options.onJobUpdate?.(next);
    if (isJobTerminalStatus(next.status)) {
      this.stopped = true;
      this.clearTimer();
      this.abort?.abort();
      this.abort = null;
      this.setStatus('closed');
      this.options.onTerminal?.(next);
    }
  }

  private seed(): JobProgressData {
    return this.job ?? { jobId: this.options.jobId, jobType: 'parse' as JobProgressData['jobType'], status: 'pending' };
  }

  /** 处理一批完整事件；返回是否已到终态。 */
  private handleFrames(text: string): boolean {
    for (const frame of parseSseMessage(text)) {
      if (frame.id) this.lastEventId = frame.id;
      const data = frame.data && typeof frame.data === 'object' ? frame.data as BackendJobEvent : null;
      if (!data) continue;
      const event: BackendJobEvent = { ...data, type: data.type || frame.event };
      this.update(applyJobEvent(this.seed(), event));
      if (this.stopped) return true;
    }
    return false;
  }

  private async openStream() {
    if (this.stopped) return;
    this.setStatus(this.retryCount ? 'reconnecting' : 'connecting');
    const controller = new AbortController();
    this.abort = controller;
    try {
      const headers = this.headers('text/event-stream');
      if (this.lastEventId) headers['Last-Event-ID'] = this.lastEventId;
      const response = await this.fetchFn(this.url('/events'), { headers, signal: controller.signal, cache: 'no-store' });
      if (!response.ok) throw new StreamHttpError(response.status);
      // 连上即恢复实时流
      this.retryCount = 0;
      if (this.fallback) { this.fallback = false; this.polls = 0; }
      this.setStatus('connected');
      const reader = response.body?.getReader?.();
      if (reader) {
        const decoder = new TextDecoder();
        let buffer = '';
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const { complete, rest } = splitSseBuffer(buffer);
          buffer = rest;
          if (complete && this.handleFrames(complete)) return;
        }
        if (buffer.trim() && this.handleFrames(buffer + '\n\n')) return;
      } else if (this.handleFrames(await response.text())) {
        return;
      }
      if (this.stopped) return;
      // 后台到时关闭：任务未结束，带上最后的事件编号重连
      this.later(this.options.reconnectDelayMs, () => { void this.openStream(); });
    } catch (error) {
      if (this.stopped || controller.signal.aborted) return;
      if (error instanceof StreamHttpError && [401, 403, 404].includes(error.status)) {
        this.stopped = true;
        this.setStatus('error', error.status === 401 ? '登录已失效' : '任务不存在或无权查看');
        return;
      }
      this.retryCount += 1;
      if (this.retryCount <= this.options.maxRetries) {
        this.setStatus('reconnecting');
        this.later(calculateBackoffDelay(this.retryCount, this.options.baseBackoffMs), () => { void this.openStream(); });
      } else {
        this.fallback = true;
        this.polls = 0;
        this.setStatus('polling');
        void this.poll();
      }
    } finally {
      if (this.abort === controller) this.abort = null;
    }
  }

  private async poll() {
    if (this.stopped) return;
    try {
      const response = await this.fetchFn(this.url(), { headers: this.headers('application/json'), cache: 'no-store' });
      if ([401, 403, 404].includes(response.status)) {
        this.stopped = true;
        this.setStatus('error', response.status === 401 ? '登录已失效' : '任务不存在或无权查看');
        return;
      }
      if (response.ok) {
        const raw = await response.json() as BackendJobStatus;
        const events = raw.events ?? [];
        if (events.length) this.lastEventId = events[events.length - 1].id;
        this.update(jobFromStatus(raw));
        if (this.stopped) return;
      }
    } catch {
      /* 网络仍不通：继续按间隔查询 */
    }
    this.polls += 1;
    if (this.polls % this.options.resumeEveryPolls === 0) {
      // 定期试一次实时流；失败时直接回到轮询，不再重新计退避
      this.retryCount = this.options.maxRetries;
      this.later(0, () => { void this.openStream(); });
      return;
    }
    this.later(this.options.pollingIntervalMs, () => { void this.poll(); });
  }
}

export function createJobStreamSubscription(options: JobStreamSubscriptionOptions): JobStreamSubscriptionManager {
  const manager = new JobStreamSubscriptionManager(options);
  manager.connect();
  return manager;
}
