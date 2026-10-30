// 为什么有这个文件：封装后台长任务进度组件 JobProgress，统一展示总进度条、子步骤明细、失败容错与追踪号。
// 它解决什么问题：
// 1. 严格落实 AI 专属紫与非 AI 企业主色的色彩隔离（AI 任务注入 .is-ai-progress 与专属紫色，非 AI 严禁出现紫色）；
// 2. 覆盖 pending/running/completed/failed/cancelled 5 类任务状态与步骤流转；
// 3. 失败时呈现标准错误信息结构与 traceId 一键复制；
// 4. 支持子步骤耗时统计与按权重的总体进度推导。

import React, { useState, type CSSProperties } from 'react';
import { Alert, Badge, Button, Progress, Space, Tag, Tooltip, Typography } from 'antd';
import {
  CheckCircleFilled,
  CheckOutlined,
  ClockCircleOutlined,
  CloseCircleFilled,
  CopyOutlined,
  ExclamationCircleFilled,
  LoadingOutlined,
  RedoOutlined,
  StopOutlined,
} from '@ant-design/icons';
import {
  deriveJobProgress,
  formatDuration,
  getJobTypeLabel,
  isAiJob,
  JOB_PROGRESS_COLORS,
  resolveJobStatusMeta,
  resolveProgressStrokeColor,
  type JobProgressData,
  type JobStep,
  type JobStepStatus,
} from './job-progress.ts';
import { copyText } from './status-views.ts';
import {
  createJobStreamSubscription,
  JobStreamSubscriptionManager,
  calculateBackoffDelay,
  parseSseLine,
  parseSseMessage,
  isJobTerminalStatus,
  type StreamConnectionStatus,
  type JobStreamSubscriptionOptions,
} from './job-progress-sse.ts';
import { useJobProgressSse, type UseJobProgressSseOptions } from './useJobProgressSse.ts';

export {
  JOB_PROGRESS_COLORS,
  deriveJobProgress,
  formatDuration,
  getJobTypeLabel,
  isAiJob,
  resolveJobStatusMeta,
  resolveProgressStrokeColor,
  useJobProgressSse,
  createJobStreamSubscription,
  JobStreamSubscriptionManager,
  calculateBackoffDelay,
  parseSseLine,
  parseSseMessage,
  isJobTerminalStatus,
  type JobProgressData,
  type JobStep,
  type JobStepStatus,
  type StreamConnectionStatus,
  type JobStreamSubscriptionOptions,
  type UseJobProgressSseOptions,
};

const { Text } = Typography;

export interface JobProgressProps {
  job: JobProgressData;
  showSteps?: boolean;
  compact?: boolean;
  onRetry?: (jobId: string, failedStepKey?: string) => void;
  onCancel?: (jobId: string) => void;
  className?: string;
  style?: CSSProperties;
  /** APP-M2-T020: 实时流已断开并降级为定时轮询标志 */
  isFallbackPolling?: boolean;
  /** APP-M2-T020: 当前流连接状态 */
  connectionStatus?: StreamConnectionStatus;
  /** 自定义降级提示语 */
  fallbackMessage?: string;
}

/**
 * 步骤图标渲染辅助函数
 */
function renderStepIcon(status: JobStepStatus, isStepAi: boolean) {
  switch (status) {
    case 'completed':
      return <CheckCircleFilled style={{ color: '#52c41a', fontSize: 14 }} />;
    case 'running':
      return (
        <LoadingOutlined
          style={{
            color: isStepAi ? '#722ed1' : '#1e4db7',
            fontSize: 14,
          }}
          spin
        />
      );
    case 'failed':
      return <CloseCircleFilled style={{ color: '#ff4d4f', fontSize: 14 }} />;
    case 'cancelled':
      return <StopOutlined style={{ color: '#8c8c8c', fontSize: 14 }} />;
    case 'pending':
    default:
      return <ClockCircleOutlined style={{ color: '#faad14', fontSize: 14 }} />;
  }
}

export function JobProgress({
  job,
  showSteps = true,
  compact = false,
  onRetry,
  onCancel,
  className = '',
  style,
  isFallbackPolling = false,
  connectionStatus,
  fallbackMessage,
}: JobProgressProps) {
  const [copied, setCopied] = useState(false);

  const isAi = isAiJob(job.jobType, job.isAi);
  const statusMeta = resolveJobStatusMeta(job.status);
  const percent = deriveJobProgress({
    status: job.status,
    explicitPercent: job.percent,
    steps: job.steps,
  });
  const strokeColor = resolveProgressStrokeColor(job.status, isAi);

  const handleCopyTraceId = async () => {
    if (!job.traceId) return;
    const ok = await copyText(job.traceId);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // 寻找首个失败步骤的 key
  const failedStep = job.steps?.find(s => s.status === 'failed');

  // 构建外层类名：AI 任务必须包含 .is-ai-progress，非 AI 严禁包含
  const rootClassNames = [
    'icg-job-progress',
    isAi ? 'is-ai-progress' : '',
    compact ? 'is-compact' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div
      className={rootClassNames}
      style={style}
      data-testid="job-progress"
      data-job-id={job.jobId}
      data-job-status={job.status}
      data-is-ai={isAi ? 'true' : 'false'}
    >
      {/* 1. 任务头部信息 */}
      <div className="icg-job-progress-header">
        <div className="icg-job-header-left">
          <span className="icg-job-title" data-testid="job-title">
            {job.title || getJobTypeLabel(job.jobType)}
          </span>
          <Tag
            color={isAi ? 'purple' : 'blue'}
            className="icg-job-type-tag"
            data-testid="job-type-tag"
          >
            {getJobTypeLabel(job.jobType)}
          </Tag>
          <Badge
            status={statusMeta.badgeStatus}
            text={statusMeta.text}
            className="icg-job-status-badge"
            data-testid="job-status-badge"
          />
        </div>
        <div className="icg-job-header-right">
          {job.durationMs !== undefined && job.durationMs >= 0 && (
            <span className="icg-job-duration" data-testid="job-duration">
              <ClockCircleOutlined style={{ marginRight: 4 }} />
              {formatDuration(job.durationMs)}
            </span>
          )}
          {/* 取消操作按钮 */}
          {(job.status === 'pending' || job.status === 'running') &&
            job.allowedActions?.includes('cancel') &&
            onCancel && (
              <Button
                size="small"
                danger
                type="text"
                icon={<StopOutlined />}
                onClick={() => onCancel(job.jobId)}
                data-testid="job-cancel-btn"
                className="icg-job-cancel-btn"
              >
                取消
              </Button>
            )}
        </div>
      </div>

      {/* 排队原因说明 */}
      {job.status === 'pending' && job.queueReason && (
        <div className="icg-job-queue-reason" data-testid="job-queue-reason">
          <Text type="secondary">
            <ClockCircleOutlined style={{ marginRight: 6 }} />
            排队原因：{job.queueReason}
          </Text>
        </div>
      )}

      {/* 实时流断线平滑回退轮询提示 (APP-M2-T020) */}
      {(isFallbackPolling || connectionStatus === 'polling') && (
        <div className="icg-job-stream-fallback-wrap" data-testid="job-stream-fallback-wrap" style={{ marginBottom: 6 }}>
          <Tag
            color="warning"
            className="icg-job-stream-fallback-tag"
            data-testid="job-stream-fallback-tag"
            icon={<ExclamationCircleFilled />}
          >
            {fallbackMessage || '实时流已断开，已切换为定时刷新'}
          </Tag>
        </div>
      )}

      {/* 2. 主进度条 */}
      <div className="icg-job-progress-bar-wrap" data-testid="job-main-progress">
        <Progress
          percent={percent}
          strokeColor={strokeColor}
          status={statusMeta.progressStatus}
          size={compact ? 'small' : 'default'}
          className={isAi ? 'icg-progress-ai' : 'icg-progress-default'}
        />
      </div>
      {job.description && job.status !== 'failed' && (
        <div className="icg-job-description" data-testid="job-description"><Text type="secondary">{job.description}</Text></div>
      )}

      {/* 3. 子步骤明细 Timeline/List */}
      {showSteps && job.steps && job.steps.length > 0 && (
        <div className="icg-job-steps-container" data-testid="job-steps-list">
          <div className="icg-job-steps-list">
            {job.steps.map((step, idx) => {
              const isStepAi = typeof step.isAi === 'boolean' ? step.isAi : isAi;
              const isCurrent = job.currentStepKey === step.key || step.status === 'running';

              return (
                <div
                  key={step.key || idx}
                  className={`icg-job-step-item icg-step-${step.status} ${
                    isCurrent ? 'is-current-step' : ''
                  }`}
                  data-testid="job-step-item"
                  data-step-key={step.key}
                  data-step-status={step.status}
                >
                  <div className="icg-step-icon-wrap">
                    {renderStepIcon(step.status, isStepAi)}
                  </div>
                  <div className="icg-step-content">
                    <div className="icg-step-header">
                      <span className="icg-step-title">{step.title}</span>
                      <Space size={8}>
                        {step.durationMs !== undefined && step.durationMs >= 0 && (
                          <span className="icg-step-duration">
                            {formatDuration(step.durationMs)}
                          </span>
                        )}
                        {typeof step.percent === 'number' && step.status === 'running' && (
                          <span className="icg-step-percent">{Math.round(step.percent)}%</span>
                        )}
                      </Space>
                    </div>

                    {step.description && (
                      <div className="icg-step-desc">{step.description}</div>
                    )}

                    {/* 子步骤进度细条 */}
                    {step.status === 'running' && typeof step.percent === 'number' && (
                      <div className="icg-step-minibar">
                        <Progress
                          percent={Math.min(100, Math.max(0, Math.round(step.percent)))}
                          size="small"
                          showInfo={false}
                          strokeColor={
                            isStepAi ? JOB_PROGRESS_COLORS.aiProgress : JOB_PROGRESS_COLORS.defaultProgress
                          }
                        />
                      </div>
                    )}

                    {/* 单步报错信息 */}
                    {step.status === 'failed' && (step.errorMessage || step.errorCode) && (
                      <div className="icg-step-error-hint">
                        {step.errorCode && (
                          <Tag color="error" className="icg-step-error-tag">
                            {step.errorCode}
                          </Tag>
                        )}
                        <Text type="danger">{step.errorMessage}</Text>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 4. 任务失败容错与追踪号区块 */}
      {job.status === 'failed' && (
        <div className="icg-job-error-block" data-testid="job-error-block">
          <Alert
            type="error"
            showIcon
            icon={<ExclamationCircleFilled />}
            message={
              <div className="icg-job-error-message-row">
                <span className="icg-job-error-title">
                  {job.errorMessage || '任务处理失败，请稍后重试'}
                </span>
                {job.errorCode && (
                  <Tag color="error" className="icg-job-error-code" data-testid="job-error-code">
                    {job.errorCode}
                  </Tag>
                )}
              </div>
            }
            description={
              <div className="icg-job-error-detail">
                {job.errorSummary && (
                  <p className="icg-job-error-summary" data-testid="job-error-summary">
                    {job.errorSummary}
                  </p>
                )}

                <div className="icg-job-error-footer">
                  {job.traceId && (
                    <div className="icg-job-trace-wrap" data-testid="job-trace-wrap">
                      <span className="icg-job-trace-label">追踪请求号 (Trace ID):</span>
                      <code className="icg-trace-code" data-testid="job-trace-code">
                        {job.traceId}
                      </code>
                      <Tooltip title={copied ? '已复制' : '复制追踪号'}>
                        <Button
                          size="small"
                          type="text"
                          icon={copied ? <CheckOutlined style={{ color: '#52c41a' }} /> : <CopyOutlined />}
                          onClick={handleCopyTraceId}
                          data-testid="copy-trace-btn"
                          className="icg-copy-trace-btn"
                        >
                          {copied ? '已复制' : '复制'}
                        </Button>
                      </Tooltip>
                    </div>
                  )}

                  {/* 重试按钮 */}
                  {job.allowedActions?.includes('retry') && onRetry && (
                    <div className="icg-job-retry-wrap">
                      <Button
                        size="small"
                        type="primary"
                        danger
                        icon={<RedoOutlined />}
                        onClick={() => onRetry(job.jobId, failedStep?.key)}
                        data-testid="job-retry-btn"
                        className="icg-job-retry-btn"
                      >
                        {failedStep ? `从失败步骤 [${failedStep.title}] 重试` : '重试任务'}
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            }
          />
        </div>
      )}
    </div>
  );
}

/**
 * APP-M2-T020: 支持自动连接 SSE 实时流与轮询降级的高阶任务进度组件
 */
export interface JobProgressWithSseProps extends Omit<JobProgressProps, 'job'> {
  jobId: string;
  token?: string | null;
  initialJob?: JobProgressData;
  baseUrl?: string;
  autoConnect?: boolean;
  /** 任务到终态（完成、失败、取消）时调用一次 */
  onTerminal?: (job: JobProgressData) => void;
}

export function JobProgressWithSse({
  jobId,
  token,
  initialJob,
  baseUrl,
  autoConnect = true,
  onTerminal,
  ...rest
}: JobProgressWithSseProps) {
  const { job, isPolling, connectionStatus, reason } = useJobProgressSse({
    jobId,
    token,
    initialJob,
    baseUrl,
    autoConnect,
    onTerminal,
  });

  if (!job) {
    return null;
  }

  return (
    <>
      <JobProgress
        {...rest}
        job={job}
        isFallbackPolling={isPolling}
        connectionStatus={connectionStatus}
      />
      {connectionStatus === 'error' && reason && (
        <Alert type="warning" showIcon message={`进度暂时无法刷新：${reason}`} data-testid="job-stream-error" style={{ marginTop: 6 }} />
      )}
    </>
  );
}


