// 为什么有这个文件：实现任务中心抽屉（TaskCenterDrawer）与独立任务卡片组件。
// 它解决什么问题：
// 1. 提供四分类（全部、运行中、已完成、异常失败）选项卡与实时数量角标；
// 2. 展现结构清晰的任务卡片：标题、类型 Tag、项目归属、当前步骤、耗时与创建时间；
// 3. 严格复用 JobProgress 的 AI 紫与企业蓝色彩隔离体系；
// 4. 支持运行中任务“取消”（cancel）与失败任务“重试”（retry），并提供追踪号复制与页面跳转。

import React, { useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Drawer,
  Empty,
  Progress,
  Space,
  Tabs,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  CheckCircleFilled,
  ClockCircleOutlined,
  CloseCircleFilled,
  CopyOutlined,
  CheckOutlined,
  ExclamationCircleFilled,
  FolderOutlined,
  LoadingOutlined,
  RedoOutlined,
  RightOutlined,
  StopOutlined,
} from '@ant-design/icons';
import {
  canPerformTaskAction,
  formatDuration,
  formatTaskTime,
  getJobTypeLabel,
  isAiJob,
  isPlatformAdminRole,
  maskTaskForPlatformAdmin,
  normalizeTask,
  resolveJobStatusMeta,
  resolveProgressStrokeColor,
  type RawTaskInput,
  type TaskFilterKey,
  type TaskItem,
} from './task-center.ts';
import { useTaskBadge } from './useTaskBadge.ts';
import { copyText } from '../status/status-views.ts';
import type { JobProgressData } from '../status/job-progress.ts';
import type { Job } from '../shared/types.ts';

const { Text } = Typography;

export interface TaskCenterCardProps {
  task: TaskItem;
  onRetry?: (jobId: string, failedStepKey?: string) => Promise<void> | void;
  onCancel?: (jobId: string) => Promise<void> | void;
  onNavigateJob?: (task: TaskItem) => void;
  compact?: boolean;
  masked?: boolean;
}

/**
 * 单个任务卡片呈现组件（复用 JobProgress 色彩与排版规范）
 */
export function TaskCenterCard({
  task,
  onRetry,
  onCancel,
  onNavigateJob,
  compact = false,
  masked = false,
}: TaskCenterCardProps) {
  const isMasked = masked || task.isMasked;
  const [copied, setCopied] = useState(false);
  const statusMeta = resolveJobStatusMeta(
    task.status === 'succeeded'
      ? 'completed'
      : task.status === 'queued'
      ? 'pending'
      : task.status
  );
  const isAi = task.isAi;
  const strokeColor = resolveProgressStrokeColor(
    task.status === 'succeeded' ? 'completed' : task.status === 'queued' ? 'pending' : task.status,
    isAi
  );

  const handleCopyTrace = async () => {
    if (!task.traceId) return;
    const ok = await copyText(task.traceId);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const cardClassNames = [
    'task-center-card',
    isAi ? 'is-ai-task-card' : 'is-default-task-card',
    `status-${task.status}`,
    compact ? 'is-compact' : '',
    isMasked ? 'is-masked-card' : '',
  ]
    .filter(Boolean)
    .join(' ');

  const showRetry = !isMasked && canPerformTaskAction(task, 'retry') && !!onRetry;
  const showCancel = !isMasked && canPerformTaskAction(task, 'cancel') && !!onCancel;

  return (
    <Card
      size="small"
      className={cardClassNames}
      data-testid="task-center-card"
      data-task-id={task.id}
      data-task-status={task.status}
      data-is-ai={isAi ? 'true' : 'false'}
      data-is-masked={isMasked ? 'true' : 'false'}
      style={{
        marginBottom: 12,
        borderRadius: 8,
        borderColor: isAi ? '#d3adf7' : '#e8ebf0',
        backgroundColor: isAi ? '#fdfaff' : '#ffffff',
      }}
    >
      {/* 1. 卡片头部：标题、类型标签、状态、耗时与时间 */}
      <div
        className="task-card-header"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 8,
          gap: 8,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <Text strong style={{ fontSize: 14 }}>
            {task.title}
          </Text>
          <Tag
            color={isAi ? 'purple' : 'blue'}
            style={{ margin: 0, fontSize: 11 }}
            data-testid="task-type-tag"
          >
            {getJobTypeLabel(task.type)}
          </Tag>
          <Badge
            status={statusMeta.badgeStatus}
            text={statusMeta.text}
            style={{ fontSize: 12 }}
            data-testid="task-status-badge"
          />
          {isMasked && (
            <Tag color="default" style={{ margin: 0, fontSize: 11 }} data-testid="task-masked-tag">
              平台脱敏
            </Tag>
          )}
          {isMasked && task.companyId && (
            <Tag style={{ margin: 0, fontSize: 11 }} data-testid="task-company-tag">
              租户: {task.companyId}
            </Tag>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#8c8c8c' }}>
          {task.durationMs !== undefined && task.durationMs >= 0 && (
            <span data-testid="task-duration">
              <ClockCircleOutlined style={{ marginRight: 3 }} />
              {formatDuration(task.durationMs)}
            </span>
          )}
          {task.createdAt && <span>{formatTaskTime(task.createdAt)}</span>}
        </div>
      </div>

      {/* 2. 所属项目与步骤信息 */}
      <div
        className="task-card-meta-row"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: 12,
          color: '#4e5969',
          marginBottom: 8,
          gap: 8,
        }}
      >
        {(task.projectName || task.projectId) && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }} data-testid="task-project-info">
            <FolderOutlined style={{ color: isMasked ? '#8c8c8c' : '#1e4db7' }} />
            <Text ellipsis style={{ maxWidth: 220, fontSize: 12, color: isMasked ? '#8c8c8c' : '#1e4db7' }}>
              {task.projectName || (isMasked ? '*** (项目已脱敏)' : `项目 (${task.projectId})`)}
            </Text>
          </div>
        )}

        {task.currentStepTitle && (
          <div
            style={{ display: 'flex', alignItems: 'center', gap: 4, marginLeft: 'auto' }}
            data-testid="task-step-info"
          >
            {task.status === 'running' ? (
              <LoadingOutlined style={{ color: isAi ? '#722ed1' : '#1e4db7' }} spin />
            ) : task.status === 'completed' || task.status === 'succeeded' ? (
              <CheckCircleFilled style={{ color: '#52c41a' }} />
            ) : task.status === 'failed' ? (
              <CloseCircleFilled style={{ color: '#ff4d4f' }} />
            ) : null}
            <Text type="secondary" style={{ fontSize: 12 }}>
              {task.currentStepTitle}
            </Text>
          </div>
        )}
      </div>

      {/* 任务描述 / 简要信息 */}
      {task.message && (
        <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>
          {task.message}
        </div>
      )}

      {/* 3. 百分比进度条 */}
      <div style={{ marginBottom: 8 }} data-testid="task-progress-bar">
        <Progress
          percent={task.progress}
          strokeColor={strokeColor}
          size="small"
          status={statusMeta.progressStatus}
        />
      </div>

      {/* 4. 异常失败区块与追踪号 */}
      {task.status === 'failed' && (
        <Alert
          type="error"
          showIcon
          icon={<ExclamationCircleFilled />}
          style={{ marginBottom: 8, padding: '6px 10px' }}
          message={
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 6 }}>
              <span style={{ fontSize: 12, fontWeight: 500 }}>
                {task.errorMessage || '任务执行异常，请查看详情或重试'}
              </span>
              {task.errorCode && (
                <Tag color="error" style={{ margin: 0, fontSize: 11 }}>
                  {task.errorCode}
                </Tag>
              )}
            </div>
          }
          description={
            task.traceId ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4, fontSize: 11 }}>
                <span style={{ color: '#8c8c8c' }}>Trace ID:</span>
                <code style={{ fontSize: 11, background: '#fff1f0', padding: '1px 4px', borderRadius: 3 }}>
                  {task.traceId}
                </code>
                <Tooltip title={copied ? '已复制' : '复制追踪号'}>
                  <Button
                    size="small"
                    type="text"
                    icon={copied ? <CheckOutlined style={{ color: '#52c41a' }} /> : <CopyOutlined />}
                    onClick={handleCopyTrace}
                    style={{ padding: 0, height: 'auto' }}
                  />
                </Tooltip>
              </div>
            ) : null
          }
        />
      )}

      {/* 5. 底部操作按钮区域 */}
      <div
        className="task-card-actions"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: isMasked ? 'space-between' : 'flex-end',
          gap: 8,
          borderTop: '1px solid #f0f0f0',
          paddingTop: 8,
        }}
      >
        {isMasked && (
          <span style={{ fontSize: 12, color: '#8c8c8c' }} data-testid="task-masked-actions-hint">
            平台运维视图 · 无业务操作权限
          </span>
        )}

        {/* 重试按钮 */}
        {showRetry && (
          <Button
            size="small"
            type="primary"
            danger
            icon={<RedoOutlined />}
            onClick={() => onRetry(task.id)}
            data-testid="task-retry-btn"
          >
            重试
          </Button>
        )}

        {/* 取消按钮 */}
        {showCancel && (
          <Button
            size="small"
            danger
            type="text"
            icon={<StopOutlined />}
            onClick={() => onCancel(task.id)}
            data-testid="task-cancel-btn"
          >
            取消
          </Button>
        )}

        {/* 前往页面 / 前往项目 */}
        {!isMasked && onNavigateJob && (
          <Button
            size="small"
            type="link"
            icon={<RightOutlined />}
            onClick={() => onNavigateJob(task)}
            style={{ padding: '0 4px' }}
            data-testid="task-navigate-btn"
          >
            前往页面
          </Button>
        )}
      </div>
    </Card>
  );
}

export interface TaskCenterDrawerProps {
  open: boolean;
  onClose: () => void;
  tasks: RawTaskInput[];
  companyId?: string;
  role?: string;
  masked?: boolean;
  onViewAll?: () => void;
  onNavigateJob?: (task: TaskItem) => void;
  onRetry?: (jobId: string, failedStepKey?: string) => Promise<void> | void;
  onCancel?: (jobId: string) => Promise<void> | void;
  width?: number | string;
}

export function TaskCenterDrawer({
  open,
  onClose,
  tasks,
  companyId,
  role,
  masked,
  onViewAll,
  onNavigateJob,
  onRetry,
  onCancel,
  width = 460,
}: TaskCenterDrawerProps) {
  const isPlatform = Boolean(masked || isPlatformAdminRole(role));

  const {
    counts,
    filter,
    setFilter,
    filteredTasks,
  } = useTaskBadge({
    tasks,
    companyId,
    initialFilter: 'all',
    initialOpen: open,
  });

  const displayTasks = isPlatform
    ? filteredTasks.map(task => maskTaskForPlatformAdmin(task))
    : filteredTasks;

  const tabItems = [
    {
      key: 'all',
      label: (
        <span data-testid="tab-all">
          全部 <Badge count={counts.all} overflowCount={99} size="small" style={{ backgroundColor: '#1e4db7' }} />
        </span>
      ),
    },
    {
      key: 'running',
      label: (
        <span data-testid="tab-running">
          进行中 <Badge count={counts.running} overflowCount={99} size="small" style={{ backgroundColor: '#faad14' }} />
        </span>
      ),
    },
    {
      key: 'completed',
      label: (
        <span data-testid="tab-completed">
          已完成 <Badge count={counts.completed} overflowCount={99} size="small" style={{ backgroundColor: '#52c41a' }} />
        </span>
      ),
    },
    {
      key: 'failed',
      label: (
        <span data-testid="tab-failed">
          异常失败 <Badge count={counts.failed} overflowCount={99} size="small" style={{ backgroundColor: '#ff4d4f' }} />
        </span>
      ),
    },
  ];

  return (
    <Drawer
      title="任务中心"
      open={open}
      onClose={onClose}
      width={width}
      className="task-center-drawer"
      data-testid="task-center-drawer"
      extra={
        onViewAll ? (
          <Button
            type="link"
            size="small"
            onClick={onViewAll}
            data-testid="view-all-jobs-btn"
          >
            查看全部任务
          </Button>
        ) : null
      }
    >
      {/* 平台管理员脱敏提示横幅 (APP-M2-T022) */}
      {isPlatform && (
        <Alert
          type="info"
          showIcon
          message="平台管理员脱敏视图"
          description="已自动隐藏项目名称、标书文件名及客户敏感业务上下文；禁用业务跳转与业务重试/取消操作。"
          style={{ marginBottom: 16 }}
          data-testid="platform-admin-masked-alert"
        />
      )}

      {/* 四分类筛选 Tabs */}
      <Tabs
        activeKey={filter}
        onChange={key => setFilter(key as TaskFilterKey)}
        items={tabItems}
        size="small"
        style={{ marginBottom: 16 }}
        data-testid="task-filter-tabs"
      />

      {/* 任务卡片列表 */}
      {displayTasks.length > 0 ? (
        <div className="task-cards-list" data-testid="task-cards-list">
          {displayTasks.map(task => (
            <TaskCenterCard
              key={task.id}
              task={task}
              masked={isPlatform}
              onRetry={isPlatform ? undefined : onRetry}
              onCancel={isPlatform ? undefined : onCancel}
              onNavigateJob={isPlatform ? undefined : onNavigateJob}
            />
          ))}
        </div>
      ) : (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="暂无相关任务"
          style={{ margin: '48px 0' }}
          data-testid="task-center-empty"
        />
      )}
    </Drawer>
  );
}
