// 为什么有这个文件：提取后台长任务抽屉组件，降低 App.tsx 单文件行数。
// 它解决什么问题：解耦后台任务列表视图与主页面骨架，展示进度、状态 Tag 与跳转引导。

import React from 'react';
import { Alert, Button, Card, Drawer, Progress, Space, Tag } from 'antd';
import type { Job } from '../shared/types.ts';
import { EmptyState } from './StatusViews.tsx';

export interface TaskDrawerProps {
  open: boolean;
  onClose: () => void;
  jobs: Job[];
  onViewAll: () => void;
  onNavigateJob: (job: Job) => void;
}

export function TaskDrawer({
  open,
  onClose,
  jobs,
  onViewAll,
  onNavigateJob,
}: TaskDrawerProps) {
  return (
    <Drawer
      title="后台任务"
      open={open}
      onClose={onClose}
      width={420}
      extra={
        <Button type="link" onClick={onViewAll}>
          查看全部
        </Button>
      }
    >
      <Alert
        type="info"
        message="当前任务同步执行，尚未提供断点恢复与取消"
        showIcon
        style={{ marginBottom: 16 }}
      />
      {jobs.length ? (
        jobs
          .slice()
          .reverse()
          .map(job => (
            <Card size="small" key={job.id} className="job-card">
              <Space>
                <Tag color={job.status === 'failed' ? 'red' : 'green'}>
                  {job.status === 'completed' ? '已完成' : job.status === 'failed' ? '失败' : job.status}
                </Tag>
                <b>{job.type === 'parse' ? '招标解析' : job.type === 'generate' ? '章节生成' : job.type}</b>
              </Space>
              <p>{job.message}</p>
              <Progress
                percent={job.progress}
                size="small"
                status={job.status === 'failed' ? 'exception' : undefined}
              />
              <Button type="link" onClick={() => onNavigateJob(job)}>
                前往页面
              </Button>
            </Card>
          ))
      ) : (
        <EmptyState description="暂无后台任务" />
      )}
    </Drawer>
  );
}
