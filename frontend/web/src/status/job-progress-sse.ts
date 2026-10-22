// 为什么有这个文件：落实 PRD v1.8 §5.12.4 与 §5.7.6，实现后台任务进度实时 SSE 订阅流、指数退避断线重连与平滑轮询降级机制。
// 它解决什么问题：
// 1. 通过 SSE (/api/v1/jobs/{id}/events) 获得实时进度推流，杜绝全量高频轮询对服务端的压力；
// 2. 网络抖动或代理断开时，自动进行 3 次阶梯指数退避重试 (1s -> 2s -> 4s)；
// 3. 超过 3 次重试仍未恢复时，无缝平滑回退至 2 秒间隔的轮询 (GET /api/v1/jobs/{id})，并呈现降级警示；
// 4. 任务到达 succeeded/completed/failed/cancelled 终态时自动切断连接并清除所有定时器，彻底杜绝内存与资源泄漏。

import { useEffect, useRef, useState, useCallback } from 'react';
import type { JobProgressData, JobStatus } from './job-progress.ts';

/**
 * 流连接状态机枚举
 */
export type StreamConnectionStatus =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'polling'
  | 'closed'
  | 'error';

/**
 * 终态任务集合：一旦进入终态，必须立即关闭连接与定时器
 */
export const TERMINAL_JOB_STATUSES: ReadonlySet<string> = new Set([
  'completed',
  'succeeded',
  'failed',
  'cancelled',
]);

/**
 * 判断任务状态是否为终态
 */
export function isJobTerminalStatus(status?: string | null): boolean {
  if (!status) return false;
  return TERMINAL_JOB_STATUSES.has(status.trim().toLowerCase());
}

/**
 * 计算指数退避重试延迟 (ms)
 * 规则：第 1 次 1000ms，第 2 次 2000ms，第 3 次 4000ms，上限 maxMs
 */
export function calculateBackoffDelay(
  retryCount: number,
  baseMs = 1000,
  maxMs = 8000
): number {
  if (retryCount <= 0) return 0;
  const factor = Math.pow(2, retryCount - 1);
  return Math.min(maxMs, baseMs * factor);
}

/**
 * 单行 SSE 文本解析函数
 */
export function parseSseLine(line: string): { field: string; value: string } | null {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith(':')) {
    // 忽略空行或注释行 (如心跳 ping)
    return null;
  }
  const colonIdx = trimmed.indexOf(':');
  if (colonIdx === -1) {
    return { field: trimmed, value: '' };
  }
  const field = trimmed.slice(0, colonIdx).trim();
  const rawValue = trimmed.slice(colonIdx + 1);
  // SSE 规范：冒号后若紧跟一个空格则去除首空格
  const value = rawValue.startsWith(' ') ? rawValue.slice(1) : rawValue;
  return { field, value };
}

/**
 * 块状 SSE 消息解析（可解析包含 event 与 data 的消息包）
 */
export interface ParsedSseEvent {
  event: string;
  data: any;
  id?: string;
  retry?: number;
}

export function parseSseMessage(rawText: string): ParsedSseEvent[] {
  const events: ParsedSseEvent[] = [];
  // 按照 SSE 规范以空行分割消息块
  const blocks = rawText.split(/\r?\n\r?\n/);

  for (const block of blocks) {
    if (!block.trim()) continue;

    let eventType = 'message';
    let dataBuffer = '';
    let id: string | undefined;
    let retry: number | undefined;

    const lines = block.split(/\r?\n/);
    for (const line of lines) {
      const parsed = parseSseLine(line);
      if (!parsed) continue;

      if (parsed.field === 'event') {
        eventType = parsed.value;
      } else if (parsed.field === 'data') {
        dataBuffer += (dataBuffer ? '\n' : '') + parsed.value;
      } else if (parsed.field === 'id') {
        id = parsed.value;
      } else if (parsed.field === 'retry') {
        const r = parseInt(parsed.value, 10);
        if (!isNaN(r)) retry = r;
      }
    }

    if (dataBuffer) {
      let parsedData: any = dataBuffer;
      try {
        parsedData = JSON.parse(dataBuffer);
      } catch {
        // 保持原始字符串
      }
      events.push({ event: eventType, data: parsedData, id, retry });
    }
  }

  return events;
}

/**
 * 抽象事件源接口（方便单测与 Mock 注入）
 */
export interface IEventSourceLike {
  onopen: ((ev: any) => void) | null;
  onmessage: ((ev: any) => void) | null;
  onerror: ((ev: any) => void) | null;
  close: () => void;
  readyState?: number;
  addEventListener?: (type: string, listener: (ev: any) => void) => void;
  removeEventListener?: (type: string, listener: (ev: any) => void) => void;
}

/**
 * SSE 订阅与轮询回退配置项
 */
export interface JobStreamSubscriptionOptions {
  jobId: string;
  baseUrl?: string;
  maxRetries?: number; // 默认 3 次
  baseBackoffMs?: number; // 默认 1000ms
  pollingIntervalMs?: number; // 默认 2000ms
  onJobUpdate?: (job: Partial<JobProgressData>) => void;
  onError?: (error: unknown) => void;
  onStatusChange?: (
    status: StreamConnectionStatus,
    meta: { retryCount: number; isFallback: boolean }
  ) => void;
  /** 可注入自定义 EventSource 构造工厂（用于 Node 单测与模拟） */
  eventSourceFactory?: (url: string) => IEventSourceLike;
  /** 可注入自定义 fetch 函数 */
  fetchFn?: typeof fetch;
}

/**
 * 核心订阅控制器类：处理连接、阶梯重试、轮询降级与终态释放
 */
export class JobStreamSubscriptionManager {
  private jobId: string;
  private baseUrl: string;
  private maxRetries: number;
  private baseBackoffMs: number;
  private pollingIntervalMs: number;

  private onJobUpdate?: (job: Partial<JobProgressData>) => void;
  private onError?: (error: unknown) => void;
  private onStatusChange?: (
    status: StreamConnectionStatus,
    meta: { retryCount: number; isFallback: boolean }
  ) => void;

  private eventSourceFactory?: (url: string) => IEventSourceLike;
  private fetchFn: typeof fetch;

  private status: StreamConnectionStatus = 'idle';
  private retryCount = 0;
  private isFallback = false;
  private isDestroyed = false;

  private activeEventSource: IEventSourceLike | null = null;
  private reconnectTimer: any = null;
  private pollingTimer: any = null;

  constructor(options: JobStreamSubscriptionOptions) {
    this.jobId = options.jobId;
    this.baseUrl = (options.baseUrl || '').replace(/\/$/, '');
    this.maxRetries = options.maxRetries ?? 3;
    this.baseBackoffMs = options.baseBackoffMs ?? 1000;
    this.pollingIntervalMs = options.pollingIntervalMs ?? 2000;

    this.onJobUpdate = options.onJobUpdate;
    this.onError = options.onError;
    this.onStatusChange = options.onStatusChange;

    this.eventSourceFactory = options.eventSourceFactory;
    this.fetchFn = options.fetchFn || (typeof fetch !== 'undefined' ? fetch : (() => Promise.reject(new Error('fetch unavailable'))) as any);
  }

  public getStatus(): StreamConnectionStatus {
    return this.status;
  }

  public getRetryCount(): number {
    return this.retryCount;
  }

  public getIsFallback(): boolean {
    return this.isFallback;
  }

  private setStatus(newStatus: StreamConnectionStatus) {
    this.status = newStatus;
    if (this.onStatusChange) {
      this.onStatusChange(newStatus, {
        retryCount: this.retryCount,
        isFallback: this.isFallback,
      });
    }
  }

  /**
   * 启动连接
   */
  public connect() {
    if (this.isDestroyed) return;
    this.clearAllTimers();
    this.closeEventSource();

    this.isFallback = false;
    this.retryCount = 0;
    this.establishSse();
  }

  /**
   * 建立 SSE 订阅连接
   */
  private establishSse() {
    if (this.isDestroyed) return;

    this.setStatus(this.retryCount > 0 ? 'reconnecting' : 'connecting');
    const sseUrl = `${this.baseUrl}/api/v1/jobs/${encodeURIComponent(this.jobId)}/events`;

    try {
      let es: IEventSourceLike;
      if (this.eventSourceFactory) {
        es = this.eventSourceFactory(sseUrl);
      } else if (typeof EventSource !== 'undefined') {
        es = new EventSource(sseUrl);
      } else {
        // 环境不支持 EventSource，直接降级轮询
        this.fallbackToPolling();
        return;
      }

      this.activeEventSource = es;

      es.onopen = () => {
        if (this.isDestroyed) return;
        this.retryCount = 0;
        this.setStatus('connected');
      };

      es.onmessage = (ev: MessageEvent | { data: any }) => {
        if (this.isDestroyed) return;
        this.handleMessageData(ev.data);
      };

      // 监听专用事件名（如 progress, done, failed）
      if (es.addEventListener) {
        const eventNames = ['job_progress', 'progress', 'step_update', 'done', 'terminal'];
        for (const name of eventNames) {
          es.addEventListener(name, (ev: any) => {
            if (this.isDestroyed) return;
            this.handleMessageData(ev.data);
          });
        }
      }

      es.onerror = (err: any) => {
        if (this.isDestroyed) return;
        this.closeEventSource();

        if (this.onError) {
          this.onError(err);
        }

        // 尝试指数退避重试
        if (this.retryCount < this.maxRetries) {
          this.retryCount++;
          const delay = calculateBackoffDelay(this.retryCount, this.baseBackoffMs);
          this.setStatus('reconnecting');

          this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            this.establishSse();
          }, delay);
        } else {
          // 超过 3 次重试，平滑回退为定时轮询
          this.fallbackToPolling();
        }
      };
    } catch (error) {
      if (this.onError) this.onError(error);
      this.fallbackToPolling();
    }
  }

  /**
   * 处理 SSE 接收到的数据体
   */
  private handleMessageData(rawData: any) {
    let payload: any = rawData;
    if (typeof rawData === 'string') {
      try {
        payload = JSON.parse(rawData);
      } catch {
        payload = { message: rawData };
      }
    }

    if (payload && typeof payload === 'object') {
      // 提取 job 数据
      const jobUpdate: Partial<JobProgressData> = payload.job || payload;
      if (this.onJobUpdate) {
        this.onJobUpdate(jobUpdate);
      }

      // 终态检查：若达到 completed/succeeded/failed/cancelled，切断连接
      if (jobUpdate.status && isJobTerminalStatus(jobUpdate.status)) {
        this.disconnect();
      }
    }
  }

  /**
   * 平滑降级至定时轮询模式
   */
  public fallbackToPolling() {
    if (this.isDestroyed) return;
    this.closeEventSource();
    this.clearAllTimers();

    this.isFallback = true;
    this.setStatus('polling');

    // 立即执行第一次轮询
    this.executePoll();

    // 启动 2 秒定时轮询
    this.pollingTimer = setInterval(() => {
      this.executePoll();
    }, this.pollingIntervalMs);
  }

  /**
   * 执行单次 HTTP 轮询
   */
  private async executePoll() {
    if (this.isDestroyed || this.status === 'closed') return;

    const pollUrl = `${this.baseUrl}/api/v1/jobs/${encodeURIComponent(this.jobId)}`;
    try {
      const resp = await this.fetchFn(pollUrl, {
        method: 'GET',
        headers: { Accept: 'application/json' },
      });

      if (!resp.ok) {
        if (resp.status === 404 || resp.status === 403) {
          // 权限撤销或资源不存在，停止轮询
          this.disconnect();
          return;
        }
        throw new Error(`Poll failed with HTTP status ${resp.status}`);
      }

      const data = await resp.json();
      const jobUpdate: Partial<JobProgressData> = data.job || data;

      if (this.onJobUpdate) {
        this.onJobUpdate(jobUpdate);
      }

      // 终态检查
      if (jobUpdate.status && isJobTerminalStatus(jobUpdate.status)) {
        this.disconnect();
      }
    } catch (err) {
      if (this.onError) {
        this.onError(err);
      }
    }
  }

  /**
   * 关闭 EventSource 实例
   */
  private closeEventSource() {
    if (this.activeEventSource) {
      try {
        this.activeEventSource.close();
      } catch {
        // 忽略已关闭异常
      }
      this.activeEventSource = null;
    }
  }

  /**
   * 清除所有待执行的定时器
   */
  private clearAllTimers() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.pollingTimer) {
      clearInterval(this.pollingTimer);
      this.pollingTimer = null;
    }
  }

  /**
   * 手动触发从当前状态重新连接流
   */
  public reconnect() {
    this.connect();
  }

  /**
   * 彻底断开连接并销毁资源（终态或组件卸载时调用）
   */
  public disconnect() {
    this.isDestroyed = true;
    this.clearAllTimers();
    this.closeEventSource();
    this.setStatus('closed');
  }
}

/**
 * 便捷工厂函数：创建长任务实时进度订阅管理器
 */
export function createJobStreamSubscription(
  options: JobStreamSubscriptionOptions
): JobStreamSubscriptionManager {
  const manager = new JobStreamSubscriptionManager(options);
  return manager;
}

/**
 * React Hook：用于在组件中无缝挂接任务 SSE 流与轮询回退
 */
export interface UseJobProgressSseOptions {
  jobId?: string;
  initialJob?: JobProgressData;
  autoConnect?: boolean;
  baseUrl?: string;
  onTerminal?: (job: JobProgressData) => void;
}

export function useJobProgressSse({
  jobId,
  initialJob,
  autoConnect = true,
  baseUrl,
  onTerminal,
}: UseJobProgressSseOptions) {
  const [job, setJob] = useState<JobProgressData | undefined>(initialJob);
  const [connectionStatus, setConnectionStatus] = useState<StreamConnectionStatus>('idle');
  const [retryCount, setRetryCount] = useState(0);
  const [isFallback, setIsFallback] = useState(false);

  const managerRef = useRef<JobStreamSubscriptionManager | null>(null);

  const handleUpdate = useCallback(
    (update: Partial<JobProgressData>) => {
      setJob(prev => {
        const next: JobProgressData = prev ? { ...prev, ...update } : (update as JobProgressData);
        if (next.status && isJobTerminalStatus(next.status) && onTerminal) {
          onTerminal(next);
        }
        return next;
      });
    },
    [onTerminal]
  );

  useEffect(() => {
    if (initialJob) {
      setJob(initialJob);
    }
  }, [initialJob]);

  useEffect(() => {
    if (!jobId || !autoConnect) {
      return;
    }

    const manager = new JobStreamSubscriptionManager({
      jobId,
      baseUrl,
      onJobUpdate: handleUpdate,
      onStatusChange: (status, meta) => {
        setConnectionStatus(status);
        setRetryCount(meta.retryCount);
        setIsFallback(meta.isFallback);
      },
    });

    managerRef.current = manager;
    manager.connect();

    return () => {
      manager.disconnect();
      managerRef.current = null;
    };
  }, [jobId, autoConnect, baseUrl, handleUpdate]);

  const reconnect = useCallback(() => {
    if (managerRef.current) {
      managerRef.current.reconnect();
    }
  }, []);

  const disconnect = useCallback(() => {
    if (managerRef.current) {
      managerRef.current.disconnect();
    }
  }, []);

  return {
    job,
    connectionStatus,
    retryCount,
    isFallback,
    isPolling: connectionStatus === 'polling',
    reconnect,
    disconnect,
  };
}
