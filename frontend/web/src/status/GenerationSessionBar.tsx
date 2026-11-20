// 为什么有这个文件：顶栏显示进行中的技术卷生成会话：「技术卷生成中 · 已完成 x/y 节 · 停止」。
// 它解决什么问题：离开编辑台后仍能看到生成在跑、能停；点文字回到编辑台继续看流。会话结束即隐藏并通知外层刷新。

import { useState } from 'react';
import { Button, Space } from 'antd';
import type { Job } from '../shared/types';
import { jobFromStatus, isJobTerminalStatus } from './job-progress-sse';
import { useJobProgressSse } from './useJobProgressSse';
import { volumeSessionLabel } from './generation-session';

export interface GenerationSessionBarProps {
  session: Job;
  token: string | null;
  onOpen: (session: Job) => void;
  onStop: (jobId: string) => Promise<void> | void;
  onSettled: () => void;
}

export function GenerationSessionBar({ session, token, onOpen, onStop, onSettled }: GenerationSessionBarProps) {
  const [stopping, setStopping] = useState(false);
  const { job } = useJobProgressSse({
    jobId: session.id,
    token,
    initialJob: jobFromStatus(session),
    onTerminal: onSettled,
  });
  if (job && isJobTerminalStatus(job.status)) return null;
  return (
    <Space size={4} className="generation-session-bar" data-testid="generation-session-bar">
      <Button type="link" size="small" onClick={() => onOpen(session)} data-testid="generation-session-open">
        {volumeSessionLabel(job?.description ?? session.message)}
      </Button>
      <Button
        danger
        size="small"
        loading={stopping}
        data-testid="generation-session-stop"
        onClick={async () => {
          setStopping(true);
          try { await onStop(session.id); } finally { setStopping(false); }
        }}
      >停止</Button>
    </Space>
  );
}
