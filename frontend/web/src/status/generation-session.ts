// 为什么有这个文件：技术卷生成是服务端会话（type=technical_volume），顶栏与编辑台都要找到进行中的那一个。
// 它解决什么问题：进度不再只活在编辑台的本地状态里；任意页从任务列表里认出会话，订阅它的进度并可停止。

import type { Job } from '../shared/types.ts';
import { isJobTerminalStatus } from './job-progress-sse.ts';

export const VOLUME_SESSION_TYPE = 'technical_volume';

/** 最近开始、尚未结束的技术卷生成会话；可只看某个项目。 */
export function activeVolumeSession(jobs: readonly Job[] | null | undefined, projectId?: string): Job | null {
  const live = (jobs ?? []).filter(job => job.type === VOLUME_SESSION_TYPE && !isJobTerminalStatus(job.status)
    && (!projectId || job.project_id === projectId));
  if (live.length === 0) return null;
  return live.reduce((latest, job) => (job.created_at > latest.created_at ? job : latest));
}

export function volumeSessionLabel(description?: string | null): string {
  const detail = description?.trim();
  return detail ? `技术卷生成中 · ${detail}` : '技术卷生成中';
}
