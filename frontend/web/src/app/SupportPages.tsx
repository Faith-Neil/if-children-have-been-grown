// 为什么有这个文件：展示已经接通的资料与任务，并标明其余页面的真实边界。
// 它解决什么问题：辅助页面不再硬编码成功，也不会把待实现能力误当作完成。
import React, { useState } from 'react';
import { Alert, Badge, Button, Card, Progress, Space, Table, Tabs, Tag, Tooltip } from 'antd';
import { RedoOutlined, StopOutlined } from '@ant-design/icons';
import { formatTime } from './context';
import type { Job } from '../shared/types';
import { EmptyState } from '../status/StatusViews';
import {
  canPerformTaskAction,
  computeTaskCounts,
  filterTasks,
  formatDuration,
  formatTaskTime,
  getJobTypeLabel,
  isAiJob,
  isPlatformAdminRole,
  maskTaskForPlatformAdmin,
  normalizeTask,
  resolveJobStatusMeta,
  resolveProgressStrokeColor,
  type TaskFilterKey,
  type TaskItem,
} from '../shell/task-center.ts';

export { LibraryPage } from '../library/LibraryPages';

export interface JobsPageProps {
  jobs: Job[];
  openProject: (id: string) => void;
  onRetry?: (jobId: string, failedStepKey?: string) => Promise<void> | void;
  onCancel?: (jobId: string) => Promise<void> | void;
  companyId?: string;
  role?: string;
  masked?: boolean;
}

export function JobsPage({
  jobs,
  openProject,
  onRetry,
  onCancel,
  companyId,
  role,
  masked,
}: JobsPageProps) {
  const [filter, setFilter] = useState<TaskFilterKey>('all');
  const isPlatform = Boolean(masked || isPlatformAdminRole(role));

  const rawTasks: TaskItem[] = jobs.map(j => normalizeTask(j));
  const normalizedTasks: TaskItem[] = isPlatform
    ? rawTasks.map(t => maskTaskForPlatformAdmin(t))
    : rawTasks;
  const counts = computeTaskCounts(normalizedTasks, companyId);
  const filtered = filterTasks(normalizedTasks, filter, { companyId });

  const tabItems = [
    {
      key: 'all',
      label: (
        <span>
          全部 <Badge count={counts.all} overflowCount={99} size="small" style={{ backgroundColor: '#1e4db7' }} />
        </span>
      ),
    },
    {
      key: 'running',
      label: (
        <span>
          进行中 <Badge count={counts.running} overflowCount={99} size="small" style={{ backgroundColor: '#faad14' }} />
        </span>
      ),
    },
    {
      key: 'completed',
      label: (
        <span>
          已完成 <Badge count={counts.completed} overflowCount={99} size="small" style={{ backgroundColor: '#52c41a' }} />
        </span>
      ),
    },
    {
      key: 'failed',
      label: (
        <span>
          异常失败 <Badge count={counts.failed} overflowCount={99} size="small" style={{ backgroundColor: '#ff4d4f' }} />
        </span>
      ),
    },
  ];

  return (
    <>
      <div className="page-heading">
        <div>
          <h2>后台任务中心</h2>
          <p>集中查看与管理当前公司的异步任务运行进度与处理结果。</p>
        </div>
        {isPlatform && (
          <Tag color="default" data-testid="platform-admin-badge">
            平台管理员脱敏视图
          </Tag>
        )}
      </div>

      {isPlatform && (
        <Alert
          type="info"
          showIcon
          message="平台管理员只读运维视图"
          description="系统已对所有跨租户业务项目名称、招标文件及业务细节实施只读脱敏；平台运维人员不具备项目跳转与业务重试/取消权限。"
          style={{ marginBottom: 16 }}
          data-testid="platform-admin-masked-alert"
        />
      )}

      <Card>
        <Tabs
          activeKey={filter}
          onChange={key => setFilter(key as TaskFilterKey)}
          items={tabItems}
          style={{ marginBottom: 16 }}
        />

        <Table<TaskItem>
          rowKey="id"
          size="small"
          dataSource={filtered}
          pagination={{ pageSize: 10 }}
          columns={[
            {
              title: '任务类型',
              dataIndex: 'type',
              width: 140,
              render: (_, item) => (
                <Tag color={item.isAi ? 'purple' : 'blue'}>
                  {getJobTypeLabel(item.type)}
                </Tag>
              ),
            },
            {
              title: '任务标题 / 说明',
              dataIndex: 'title',
              render: (_, item) => (
                <Space direction="vertical" size={2}>
                  <Space size={6} wrap>
                    <span style={{ fontWeight: 500 }}>{item.title}</span>
                    {item.isMasked && (
                      <Tag color="default" style={{ margin: 0, fontSize: 11 }}>脱敏</Tag>
                    )}
                    {isPlatform && item.companyId && (
                      <Tag style={{ margin: 0, fontSize: 11 }}>租户: {item.companyId}</Tag>
                    )}
                  </Space>
                  {item.projectName && (
                    <small style={{ color: item.isMasked ? '#8c8c8c' : '#1e4db7' }}>
                      项目: {item.projectName}
                    </small>
                  )}
                  {item.currentStepTitle && (
                    <small style={{ color: '#8c8c8c' }}>步骤: {item.currentStepTitle}</small>
                  )}
                  {item.message && item.message !== item.title && (
                    <small style={{ color: '#4e5969' }}>{item.message}</small>
                  )}
                  {item.traceId && (
                    <small style={{ color: '#8c8c8c' }}>
                      Trace: <code>{item.traceId}</code>
                    </small>
                  )}
                </Space>
              ),
            },
            {
              title: '状态',
              dataIndex: 'status',
              width: 100,
              render: (_, item) => {
                const meta = resolveJobStatusMeta(
                  item.status === 'succeeded' ? 'completed' : item.status === 'queued' ? 'pending' : item.status
                );
                return <Badge status={meta.badgeStatus} text={meta.text} />;
              },
            },
            {
              title: '进度',
              width: 160,
              render: (_, item) => {
                const stroke = resolveProgressStrokeColor(
                  item.status === 'succeeded' ? 'completed' : item.status === 'queued' ? 'pending' : item.status,
                  item.isAi
                );
                const meta = resolveJobStatusMeta(
                  item.status === 'succeeded' ? 'completed' : item.status === 'queued' ? 'pending' : item.status
                );
                return (
                  <Progress
                    percent={item.progress}
                    size="small"
                    strokeColor={stroke}
                    status={meta.progressStatus}
                  />
                );
              },
            },
            {
              title: '创建时间',
              dataIndex: 'createdAt',
              width: 150,
              render: val => formatTaskTime(val),
            },
            {
              title: '耗时',
              width: 90,
              render: (_, item) => formatDuration(item.durationMs),
            },
            {
              title: '操作',
              width: 180,
              render: (_, item) => {
                if (isPlatform) {
                  return (
                    <span style={{ color: '#8c8c8c', fontSize: 12 }} data-testid="platform-admin-readonly-op">
                      只读运维
                    </span>
                  );
                }
                const showRetry = canPerformTaskAction(item, 'retry') && !!onRetry;
                const showCancel = canPerformTaskAction(item, 'cancel') && !!onCancel;

                return (
                  <Space size={4}>
                    {item.projectId && (
                      <Button
                        type="link"
                        size="small"
                        onClick={() => openProject(item.projectId!)}
                      >
                        前往项目
                      </Button>
                    )}
                    {showRetry && (
                      <Button
                        type="primary"
                        danger
                        size="small"
                        icon={<RedoOutlined />}
                        onClick={() => onRetry?.(item.id)}
                      >
                        重试
                      </Button>
                    )}
                    {showCancel && (
                      <Button
                        type="text"
                        danger
                        size="small"
                        icon={<StopOutlined />}
                        onClick={() => onCancel?.(item.id)}
                      >
                        取消
                      </Button>
                    )}
                  </Space>
                );
              },
            },
          ]}
        />
      </Card>
    </>
  );
}

export function PendingPage({ title, detail }: { title: string; detail: string }) {
  return (
    <>
      <div className="page-heading">
        <div>
          <h2>{title}</h2>
        </div>
        <Tag color="orange">尚未实现</Tag>
      </div>
      <Card>
        <EmptyState description={detail} />
      </Card>
    </>
  );
}
