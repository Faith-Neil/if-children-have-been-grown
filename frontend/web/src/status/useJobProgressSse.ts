// 为什么有这个文件：在页面里订阅一个后台任务的进度（APP-M2-T020）。
// 它解决什么问题：组件只给任务编号与令牌，拿到实时进度、连接状态与是否已降级为轮询；卸载或任务结束即停止订阅。

import { useEffect, useRef, useState } from 'react';
import type { JobProgressData } from './job-progress.ts';
import { JobStreamSubscriptionManager, type StreamConnectionStatus } from './job-progress-sse.ts';

export interface UseJobProgressSseOptions {
  jobId: string | null | undefined;
  token?: string | null;
  initialJob?: JobProgressData | null;
  baseUrl?: string;
  autoConnect?: boolean;
  onTerminal?: (job: JobProgressData) => void;
  fetchFn?: typeof fetch;
}

export function useJobProgressSse({ jobId, token, initialJob, baseUrl, autoConnect = true, onTerminal, fetchFn }: UseJobProgressSseOptions) {
  const [job, setJob] = useState<JobProgressData | null>(initialJob ?? null);
  const [connectionStatus, setConnectionStatus] = useState<StreamConnectionStatus>('idle');
  const [isPolling, setIsPolling] = useState(false);
  const [reason, setReason] = useState<string | undefined>(undefined);
  const terminal = useRef(onTerminal);
  terminal.current = onTerminal;

  useEffect(() => {
    if (!jobId || !autoConnect) return;
    setJob(initialJob ?? null);
    const manager = new JobStreamSubscriptionManager({
      jobId, token, baseUrl, initialJob, fetchFn,
      onJobUpdate: next => setJob(next),
      onStatusChange: (status, meta) => { setConnectionStatus(status); setIsPolling(meta.isFallback); setReason(meta.reason); },
      onTerminal: done => terminal.current?.(done),
    });
    manager.connect();
    return () => manager.disconnect();
    // initialJob 只用作起始显示，变化时不重新订阅
  }, [jobId, token, baseUrl, autoConnect]);

  return { job, connectionStatus, isPolling, reason };
}
