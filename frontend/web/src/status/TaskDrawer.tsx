// 为什么有这个文件：提取后台长任务抽屉组件，兼容旧引入并对接新的 TaskCenterDrawer。
// 它解决什么问题：解耦后台任务列表视图与主页面骨架，展示进度、状态 Tag 与跳转引导。

import React from 'react';
import type { Job } from '../shared/types.ts';
import {
  TaskCenterDrawer,
  type TaskCenterDrawerProps,
} from '../shell/TaskCenterDrawer.tsx';
import type { TaskItem } from '../shell/task-center.ts';

export interface TaskDrawerProps {
  open: boolean;
  onClose: () => void;
  jobs: Job[];
  onViewAll: () => void;
  onNavigateJob: (job: Job | any) => void;
  onRetry?: (jobId: string, failedStepKey?: string) => Promise<void> | void;
  onCancel?: (jobId: string) => Promise<void> | void;
  companyId?: string;
  width?: number | string;
}

export function TaskDrawer({
  open,
  onClose,
  jobs,
  onViewAll,
  onNavigateJob,
  onRetry,
  onCancel,
  companyId,
  width,
}: TaskDrawerProps) {
  return (
    <TaskCenterDrawer
      open={open}
      onClose={onClose}
      tasks={jobs}
      companyId={companyId}
      onViewAll={onViewAll}
      onNavigateJob={task => {
        // 传递原始任务或 task item 兼容调用方
        const found = jobs.find(j => j.id === task.id);
        onNavigateJob(found || (task as unknown as Job));
      }}
      onRetry={onRetry}
      onCancel={onCancel}
      width={width}
    />
  );
}

export { TaskCenterDrawer };
