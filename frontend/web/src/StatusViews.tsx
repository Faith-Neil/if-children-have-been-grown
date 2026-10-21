// 为什么有这个文件：封装统一的状态组件（骨架屏、空态、错误、无权限、已过期、只读）。
// 它解决什么问题：统一全站状态呈现，支持错误码/追踪号一键复制，符合 ICG 规范与 WCAG 4.5:1 对比度。
import { useEffect, useState, type CSSProperties, type ReactNode } from 'react';
import { Alert, Button, Card, Col, Empty, Result, Row, Skeleton, Space, Tag, Tooltip, type ButtonProps } from 'antd';
import { CheckOutlined, ClockCircleOutlined, CopyOutlined, InfoCircleOutlined, LockOutlined, ReloadOutlined, WarningOutlined } from '@ant-design/icons';
import {
  copyText,
  extractErrorInfo,
  STATUS_CONTRAST_TOKENS,
  resolveEmptyState,
  resolveForbidden,
  resolveExpired,
  resolveReadonly,
  type ExtractedErrorInfo,
} from './status-views';

export {
  copyText,
  extractErrorInfo,
  STATUS_CONTRAST_TOKENS,
  resolveEmptyState,
  resolveForbidden,
  resolveExpired,
  resolveReadonly,
  type ExtractedErrorInfo,
};

/* ========================================================================= */
/* 1. Skeleton 骨架屏加载态                                                 */
/* ========================================================================= */

export interface SkeletonViewProps {
  variant?: 'page' | 'table' | 'cards' | 'detail';
  rows?: number;
  cards?: number;
  active?: boolean;
  loading?: boolean;
  tip?: ReactNode;
  timeoutSeconds?: number;
  showTimeoutNotice?: boolean;
  children?: ReactNode;
  className?: string;
  style?: CSSProperties;
}

export function SkeletonView({
  variant = 'page',
  rows = 5,
  cards = 3,
  active = true,
  loading = true,
  tip,
  timeoutSeconds = 10,
  showTimeoutNotice = true,
  children,
  className = '',
  style,
}: SkeletonViewProps) {
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    if (!loading || !showTimeoutNotice || timeoutSeconds <= 0) {
      setTimedOut(false);
      return;
    }
    const timer = setTimeout(() => {
      setTimedOut(true);
    }, timeoutSeconds * 1000);
    return () => clearTimeout(timer);
  }, [loading, showTimeoutNotice, timeoutSeconds]);

  if (!loading) {
    return children ? <>{children}</> : null;
  }

  const renderContent = () => {
    if (variant === 'table') {
      return (
        <div className="icg-status-skeleton-table" data-testid="skeleton-table">
          <div className="icg-status-skeleton-table-header" style={{ marginBottom: 16 }}>
            <Skeleton.Input active={active} size="small" style={{ width: 120, marginRight: 16 }} />
            <Skeleton.Input active={active} size="small" style={{ width: 200, marginRight: 16 }} />
            <Skeleton.Input active={active} size="small" style={{ width: 100 }} />
          </div>
          {Array.from({ length: rows }).map((_, i) => (
            <div key={i} style={{ padding: '12px 0', borderBottom: '1px solid #f0f2f5' }}>
              <Skeleton active={active} title={false} paragraph={{ rows: 1, width: ['100%'] }} />
            </div>
          ))}
        </div>
      );
    }

    if (variant === 'cards') {
      return (
        <Row gutter={[16, 16]} className="icg-status-skeleton-cards" data-testid="skeleton-cards">
          {Array.from({ length: cards }).map((_, i) => (
            <Col span={24 / Math.min(cards, 4)} key={i}>
              <Card>
                <Skeleton active={active} paragraph={{ rows: 3 }} />
              </Card>
            </Col>
          ))}
        </Row>
      );
    }

    if (variant === 'detail') {
      return (
        <div className="icg-status-skeleton-detail" data-testid="skeleton-detail">
          <Skeleton active={active} avatar paragraph={{ rows: 4 }} />
        </div>
      );
    }

    // Default 'page'
    return (
      <div className="icg-status-skeleton-page" data-testid="skeleton-page">
        <div style={{ marginBottom: 24 }}>
          <Skeleton.Input active={active} size="large" style={{ width: 240, height: 32, marginBottom: 8 }} />
          <br />
          <Skeleton.Input active={active} size="small" style={{ width: 360, height: 16 }} />
        </div>
        <Card>
          <Skeleton active={active} paragraph={{ rows }} />
        </Card>
      </div>
    );
  };

  return (
    <div
      className={`icg-status-skeleton ${className}`}
      style={style}
      role="status"
      aria-busy="true"
      aria-live="polite"
    >
      {tip && <div className="icg-status-skeleton-tip" style={{ marginBottom: 16, color: '#4e5969', fontSize: 13 }}>{tip}</div>}
      {renderContent()}
      {timedOut && (
        <Alert
          className="icg-status-skeleton-timeout"
          type="info"
          showIcon
          icon={<ClockCircleOutlined />}
          message="仍在加载，可离开本页，任务在后台继续"
          style={{ marginTop: 16 }}
        />
      )}
    </div>
  );
}

export const PageSkeleton = SkeletonView;

/* ========================================================================= */
/* 2. Empty 空态展示与创建引导                                              */
/* ========================================================================= */

export interface EmptyStateProps {
  mode?: 'empty' | 'filtered' | 'search';
  image?: 'simple' | 'default' | ReactNode;
  title?: ReactNode;
  description?: ReactNode;
  actionText?: ReactNode;
  onAction?: () => void;
  actionButtonProps?: ButtonProps;
  searchKeyword?: string;
  extra?: ReactNode;
  className?: string;
  style?: CSSProperties;
}

export function EmptyState({
  mode = 'empty',
  image = 'simple',
  title,
  description,
  actionText,
  onAction,
  actionButtonProps,
  searchKeyword,
  extra,
  className = '',
  style,
}: EmptyStateProps) {
  let resolvedTitle = title;
  let resolvedDesc = description;
  let resolvedActionText = actionText;

  if (mode === 'filtered') {
    resolvedTitle = resolvedTitle ?? '没有符合条件的记录';
    resolvedDesc = resolvedDesc ?? '请尝试调整或重置筛选条件';
    resolvedActionText = resolvedActionText ?? '清除筛选';
  } else if (mode === 'search') {
    resolvedTitle = resolvedTitle ?? '未找到匹配结果';
    resolvedDesc = resolvedDesc ?? (searchKeyword ? `没有找到名称包含“${searchKeyword}”的项目或资料` : '没有找到匹配的记录');
  } else {
    resolvedTitle = resolvedTitle ?? '暂无数据';
  }

  const resolvedImage = image === 'simple'
    ? Empty.PRESENTED_IMAGE_SIMPLE
    : image === 'default'
      ? Empty.PRESENTED_IMAGE_DEFAULT
      : image;

  return (
    <div
      className={`icg-status-empty ${className}`}
      style={style}
      role="status"
      aria-label={typeof resolvedTitle === 'string' ? resolvedTitle : '空态'}
    >
      <Empty
        image={resolvedImage}
        description={
          <div className="icg-status-empty-text">
            {resolvedTitle && <div className="icg-status-empty-title">{resolvedTitle}</div>}
            {resolvedDesc && <div className="icg-status-empty-desc">{resolvedDesc}</div>}
          </div>
        }
      >
        <Space direction="horizontal" size="middle" wrap style={{ justifyContent: 'center' }}>
          {resolvedActionText && onAction && (
            <Button
              type="primary"
              onClick={onAction}
              {...actionButtonProps}
            >
              {resolvedActionText}
            </Button>
          )}
          {extra}
        </Space>
      </Empty>
    </div>
  );
}

export const EmptyView = EmptyState;

/* ========================================================================= */
/* 3. ErrorView 带统一错误体 code、message 与 traceId 一键复制              */
/* ========================================================================= */

export interface ErrorViewProps {
  error?: unknown;
  code?: string;
  message?: ReactNode;
  traceId?: string;
  details?: Record<string, unknown>;
  layout?: 'page' | 'block' | 'inline';
  onRetry?: () => void;
  retryLoading?: boolean;
  retryText?: ReactNode;
  onCopyTraceId?: (traceId: string) => void;
  copyHandler?: (text: string) => Promise<boolean>;
  extra?: ReactNode;
  className?: string;
  style?: CSSProperties;
}

export function ErrorView({
  error,
  code,
  message,
  traceId,
  details: _details,
  layout = 'block',
  onRetry,
  retryLoading = false,
  retryText = '重试',
  onCopyTraceId,
  copyHandler = copyText,
  extra,
  className = '',
  style,
}: ErrorViewProps) {
  const extracted = extractErrorInfo(error);
  const activeCode = code ?? extracted.code;
  const activeMessage = message ?? extracted.message;
  const activeTraceId = traceId ?? extracted.traceId;

  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!activeTraceId) return;
    const success = await copyHandler(activeTraceId);
    if (success) {
      setCopied(true);
      onCopyTraceId?.(activeTraceId);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const renderTraceRow = () => {
    if (!activeTraceId) return null;
    return (
      <div className="icg-status-error-trace" data-testid="error-trace-row">
        <span>请求编号 (traceId)：</span>
        <code className="icg-trace-code" data-testid="trace-id-value">{activeTraceId}</code>
        <Tooltip title={copied ? '已复制追踪号' : '点击复制请求追踪号'}>
          <Button
            type="text"
            size="small"
            icon={copied ? <CheckOutlined style={{ color: '#2b9d5c' }} /> : <CopyOutlined />}
            onClick={handleCopy}
            aria-label="复制请求编号"
            data-testid="copy-trace-button"
          >
            {copied ? '已复制' : '复制'}
          </Button>
        </Tooltip>
      </div>
    );
  };

  const renderActions = () => {
    if (!onRetry && !extra) return null;
    return (
      <Space size="middle" className="icg-status-error-actions">
        {onRetry && (
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            loading={retryLoading}
            onClick={onRetry}
            data-testid="error-retry-button"
          >
            {retryText}
          </Button>
        )}
        {extra}
      </Space>
    );
  };

  if (layout === 'page') {
    return (
      <div className={`icg-status-error icg-status-error-page ${className}`} style={style}>
        <Result
          status="error"
          title={typeof activeMessage === 'string' ? activeMessage : '操作失败'}
          subTitle={
            <div style={{ textAlign: 'center' }}>
              <div style={{ marginBottom: 8 }}>
                <Tag color="red" className="icg-status-error-code" data-testid="error-code-tag">{activeCode}</Tag>
              </div>
              {renderTraceRow()}
            </div>
          }
          extra={renderActions()}
        />
      </div>
    );
  }

  if (layout === 'inline') {
    return (
      <Alert
        className={`icg-status-error icg-status-error-inline ${className}`}
        style={style}
        type="error"
        showIcon
        message={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span>{activeMessage}</span>
            <Tag color="red" className="icg-status-error-code" data-testid="error-code-tag">{activeCode}</Tag>
          </div>
        }
        description={
          <div>
            {renderTraceRow()}
            {renderActions()}
          </div>
        }
      />
    );
  }

  // Default 'block'
  return (
    <div className={`icg-status-error icg-status-error-block ${className}`} style={style} data-testid="error-view-block">
      <div className="icg-status-error-header">
        <Space size="small">
          <Tag color="red" className="icg-status-error-code" data-testid="error-code-tag">{activeCode}</Tag>
          <strong className="icg-status-error-title" style={{ fontSize: 14, color: '#1d2129' }}>{activeMessage}</strong>
        </Space>
      </div>
      {renderTraceRow()}
      <div style={{ marginTop: 12 }}>
        {renderActions()}
      </div>
    </div>
  );
}

export const ErrorState = ErrorView;

/* ========================================================================= */
/* 4. Forbidden403 无权限访问提示，保留当前上下文与返回引导                   */
/* ========================================================================= */

export interface ForbiddenContextObject {
  projectName?: string;
  roleName?: string;
  path?: string;
  retainedMessage?: string;
}

export interface Forbidden403Props {
  title?: ReactNode;
  subTitle?: ReactNode;
  reason?: ReactNode;
  contextInfo?: ForbiddenContextObject | ReactNode;
  showRetainedNotice?: boolean;
  onBack?: () => void;
  backText?: ReactNode;
  backPath?: string;
  extra?: ReactNode;
  layout?: 'page' | 'block';
  className?: string;
  style?: CSSProperties;
}

export function Forbidden403({
  title = '没有访问权限',
  subTitle = '你没有该页面的权限，请联系公司管理员。',
  reason,
  contextInfo,
  showRetainedNotice = false,
  onBack,
  backText = '返回工作台',
  backPath = '/workbench',
  extra,
  layout = 'page',
  className = '',
  style,
}: Forbidden403Props) {
  const isObjectContext = contextInfo && typeof contextInfo === 'object' && !('props' in (contextInfo as object));
  const ctx = isObjectContext ? (contextInfo as ForbiddenContextObject) : null;

  const renderContext = () => {
    if (!contextInfo) return null;
    if (!isObjectContext) {
      return <div className="icg-status-forbidden-context">{contextInfo as ReactNode}</div>;
    }
    return (
      <div className="icg-status-forbidden-context" data-testid="forbidden-context-info">
        <Space size="small" wrap>
          {ctx?.projectName && (
            <Tag color="blue">当前项目：{ctx.projectName}</Tag>
          )}
          {ctx?.roleName && (
            <Tag color="geekblue">当前身份：{ctx.roleName}</Tag>
          )}
          {ctx?.path && (
            <Tag color="default">目标路径：{ctx.path}</Tag>
          )}
        </Space>
        {ctx?.retainedMessage && (
          <p style={{ margin: '8px 0 0', color: '#4e5969' }}>{ctx.retainedMessage}</p>
        )}
      </div>
    );
  };

  const renderRetained = () => {
    if (!showRetainedNotice) return null;
    return (
      <Alert
        type="info"
        showIcon
        message="当前内容及未保存文字仍保留在下方，写入口已关闭。"
        style={{ marginTop: 12, textAlign: 'left' }}
        data-testid="retained-notice"
      />
    );
  };

  const renderActions = () => {
    return (
      <Space size="middle">
        {onBack ? (
          <Button type="primary" onClick={onBack} data-testid="forbidden-back-button">
            {backText}
          </Button>
        ) : backPath ? (
          <Button type="primary" href={backPath} data-testid="forbidden-back-button">
            {backText}
          </Button>
        ) : null}
        {extra}
      </Space>
    );
  };

  if (layout === 'block') {
    return (
      <div className={`icg-status-forbidden icg-status-forbidden-block ${className}`} style={style} data-testid="forbidden-block">
        <Space align="start" size="middle">
          <LockOutlined style={{ fontSize: 24, color: '#d9363e', marginTop: 4 }} />
          <div>
            <h4 style={{ margin: '0 0 6px', fontSize: 15, color: '#1d2129' }}>{title}</h4>
            <div style={{ color: '#4e5969', fontSize: 13 }}>{reason || subTitle}</div>
            {renderContext()}
            {renderRetained()}
            <div style={{ marginTop: 12 }}>{renderActions()}</div>
          </div>
        </Space>
      </div>
    );
  }

  // Default 'page'
  return (
    <div className={`icg-status-forbidden icg-status-forbidden-page ${className}`} style={style} data-testid="forbidden-page">
      <Result
        status="403"
        title={title}
        subTitle={
          <div>
            <div>{reason || subTitle}</div>
            {renderContext()}
            {renderRetained()}
          </div>
        }
        extra={renderActions()}
      />
    </div>
  );
}

export const NoPermission = Forbidden403;

/* ========================================================================= */
/* 5. ExpiredWarning 版本过期、需要重新核对的提示条                           */
/* ========================================================================= */

export interface ExpiredWarningProps {
  message?: ReactNode;
  description?: ReactNode;
  reason?: ReactNode;
  currentRevision?: number | string;
  latestRevision?: number | string;
  actionText?: ReactNode;
  onAction?: () => void;
  actionLoading?: boolean;
  closable?: boolean;
  onClose?: () => void;
  banner?: boolean;
  className?: string;
  style?: CSSProperties;
}

export function ExpiredWarning({
  message = '内容已修改，结果已过期',
  description,
  reason,
  currentRevision,
  latestRevision,
  actionText = '重新运行',
  onAction,
  actionLoading = false,
  closable = false,
  onClose,
  banner = false,
  className = '',
  style,
}: ExpiredWarningProps) {
  const hasRevisionComparison = currentRevision !== undefined && latestRevision !== undefined;

  const renderDescription = () => {
    return (
      <div className="icg-status-expired-desc">
        {description && <div>{description}</div>}
        {reason && <div style={{ marginTop: 4 }}>变更原因：{reason}</div>}
        {hasRevisionComparison && (
          <div style={{ marginTop: 4, fontSize: 12 }}>
            <span>当前已保存版本：<b>{currentRevision}</b></span>
            <span style={{ margin: '0 8px' }}>|</span>
            <span>后台最新版本：<b>{latestRevision}</b></span>
          </div>
        )}
      </div>
    );
  };

  const renderAction = () => {
    if (!onAction && !actionText) return undefined;
    return (
      <Button
        size="small"
        type="primary"
        ghost
        loading={actionLoading}
        onClick={onAction}
        style={{ borderColor: '#9a5608', color: '#9a5608' }}
        data-testid="expired-action-button"
      >
        {actionText}
      </Button>
    );
  };

  return (
    <Alert
      className={`icg-status-expired ${className}`}
      style={style}
      type="warning"
      showIcon
      icon={<WarningOutlined style={{ color: '#9a5608' }} />}
      banner={banner}
      closable={closable}
      onClose={onClose}
      message={<span className="icg-status-expired-message" style={{ fontWeight: 600, color: '#9a5608' }}>{message}</span>}
      description={(description || reason || hasRevisionComparison) ? renderDescription() : undefined}
      action={onAction ? renderAction() : undefined}
      data-testid="expired-warning-alert"
    />
  );
}

export const StaleBanner = ExpiredWarning;

/* ========================================================================= */
/* 6. ReadonlyBanner 只读会话保护横幅                                        */
/* ========================================================================= */

export interface ReadonlyBannerProps {
  reason?: string | ReactNode;
  message?: ReactNode;
  description?: ReactNode;
  scope?: string | ReactNode;
  roleName?: string;
  onAction?: () => void;
  actionText?: ReactNode;
  extra?: ReactNode;
  banner?: boolean;
  className?: string;
  style?: CSSProperties;
}

export function ReadonlyBanner({
  reason,
  message,
  description = '当前页面处于只读状态，所有修改、保存与生成入口已关闭，仅供查阅。',
  scope,
  roleName,
  onAction,
  actionText,
  extra,
  banner = false,
  className = '',
  style,
}: ReadonlyBannerProps) {
  const resolvedMessage = message ?? (reason ? `只读：${reason}` : '只读会话保护');

  const renderDescription = () => {
    return (
      <div className="icg-status-readonly-desc">
        <div>{description}</div>
        {(scope || roleName) && (
          <div style={{ marginTop: 6 }}>
            <Space size="small">
              {scope && <Tag color="default">范围：{scope}</Tag>}
              {roleName && <Tag color="blue">当前角色：{roleName}</Tag>}
            </Space>
          </div>
        )}
      </div>
    );
  };

  const renderAction = () => {
    if (!onAction && !extra) return undefined;
    return (
      <Space size="small">
        {onAction && actionText && (
          <Button size="small" onClick={onAction} data-testid="readonly-action-button">
            {actionText}
          </Button>
        )}
        {extra}
      </Space>
    );
  };

  return (
    <Alert
      className={`icg-status-readonly ${className}`}
      style={style}
      type="info"
      showIcon
      icon={<InfoCircleOutlined style={{ color: '#1e4db7' }} />}
      banner={banner}
      message={<span className="icg-status-readonly-title" style={{ fontWeight: 600, color: '#1d2129' }}>{resolvedMessage}</span>}
      description={renderDescription()}
      action={renderAction()}
      data-testid="readonly-banner-alert"
    />
  );
}

export const ReadOnlyBanner = ReadonlyBanner;
