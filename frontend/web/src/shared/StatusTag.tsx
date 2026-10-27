// 为什么有这个文件：依据 PRD MVP v1.8 §5.10.3 与设计规范 9.3 封装全站统一业务状态标签组件。
// 它解决什么问题：
// 1. 彻底消灭散落在项目列表、章节大纲树、长任务中心、合规检查中心、导出交付台与编辑台中的各异 Tag；
// 2. 贯彻 Layout First 克制原则，以紧凑清晰的标签与 WCAG AA 4.5:1 对比度色彩自然表达业务意图；
// 3. 支持三种视觉形态（solid/subtle/outline）、两种尺寸（default/small）、小圆点 Badge 模式与 Tooltip 辅助描述。

import React from 'react';
import type { CSSProperties, MouseEvent, ReactNode } from 'react';
import { Tag, Tooltip } from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  EditOutlined,
  ExclamationCircleOutlined,
  FieldTimeOutlined,
  FileTextOutlined,
  InboxOutlined,
  LoadingOutlined,
  LockOutlined,
  MinusCircleOutlined,
  QuestionCircleOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  StopOutlined,
  SyncOutlined,
  UnlockOutlined,
} from '@ant-design/icons';
import {
  resolveStatus,
  type StatusDomain,
  type StatusMeta,
  type TagSize,
  type TagVariant,
} from './status-registry.ts';

export * from './status-registry.ts';

export interface StatusTagProps {
  /** 业务领域：项目、章节、长任务、合规检查、导出交付、编辑租约 */
  type: StatusDomain;
  /** 业务状态代码（支持规范代码与大小写/别名兼容） */
  status?: string | null;
  /** 视觉变体：subtle(浅底描边，默认), solid(实心高对比), outline(白底描边) */
  variant?: TagVariant;
  /** 尺寸：default(24px) 或 small(20px) */
  size?: TagSize;
  /** 是否展示对应状态的语义图标 */
  showIcon?: boolean;
  /** 是否展示左侧状态小圆点 Badge */
  showBadge?: boolean;
  /** 自定义文字标签覆盖 */
  customLabel?: ReactNode;
  /** 自定义图标覆盖 */
  icon?: ReactNode;
  /** 气泡提示：true 则显示状态描述，亦可传入自定义 ReactNode */
  tooltip?: boolean | ReactNode;
  className?: string;
  style?: CSSProperties;
  onClick?: (e: MouseEvent<HTMLElement>) => void;
}

/**
 * 状态图标渲染派发函数
 */
function renderStatusIcon(iconName: string): ReactNode {
  switch (iconName) {
    case 'CheckCircleOutlined':
      return <CheckCircleOutlined />;
    case 'ClockCircleOutlined':
      return <ClockCircleOutlined />;
    case 'CloseCircleOutlined':
      return <CloseCircleOutlined />;
    case 'EditOutlined':
      return <EditOutlined />;
    case 'ExclamationCircleOutlined':
      return <ExclamationCircleOutlined />;
    case 'FieldTimeOutlined':
      return <FieldTimeOutlined />;
    case 'FileTextOutlined':
      return <FileTextOutlined />;
    case 'InboxOutlined':
      return <InboxOutlined />;
    case 'LoadingOutlined':
      return <LoadingOutlined spin />;
    case 'LockOutlined':
      return <LockOutlined />;
    case 'MinusCircleOutlined':
      return <MinusCircleOutlined />;
    case 'QuestionCircleOutlined':
      return <QuestionCircleOutlined />;
    case 'RobotOutlined':
      return <RobotOutlined />;
    case 'SafetyCertificateOutlined':
      return <SafetyCertificateOutlined />;
    case 'StopOutlined':
      return <StopOutlined />;
    case 'SyncOutlined':
      return <SyncOutlined spin />;
    case 'UnlockOutlined':
      return <UnlockOutlined />;
    default:
      return null;
  }
}

/**
 * 依据变体与尺寸计算内联样式（严格保持 WCAG AA 4.5:1 对比度与 Layout First 克制边距）
 */
function computeTagStyle(
  meta: StatusMeta,
  variant: TagVariant,
  size: TagSize,
  isClickable: boolean,
  customStyle?: CSSProperties
): CSSProperties {
  const isSmall = size === 'small';

  const baseStyle: CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    margin: 0,
    fontWeight: 500,
    transition: 'all 0.15s ease-in-out',
    cursor: isClickable ? 'pointer' : 'default',
    lineHeight: 1,
    boxSizing: 'border-box',
    userSelect: 'none',
  };

  // 尺寸样式
  if (isSmall) {
    baseStyle.fontSize = 12;
    baseStyle.padding = '0 6px';
    baseStyle.height = 20;
    baseStyle.borderRadius = 3;
  } else {
    baseStyle.fontSize = 12;
    baseStyle.padding = '1px 8px';
    baseStyle.height = 24;
    baseStyle.borderRadius = 4;
  }

  // 变体色彩样式
  if (variant === 'solid') {
    baseStyle.backgroundColor = meta.solidBg;
    baseStyle.color = meta.solidText;
    baseStyle.border = 'none';
  } else if (variant === 'outline') {
    baseStyle.backgroundColor = '#FFFFFF';
    baseStyle.color = meta.outlineText;
    baseStyle.border = `1px solid ${meta.outlineBorder}`;
  } else {
    // 默认 subtle
    baseStyle.backgroundColor = meta.subtleBg;
    baseStyle.color = meta.subtleText;
    baseStyle.border = `1px solid ${meta.subtleBorder}`;
  }

  return { ...baseStyle, ...customStyle };
}

/**
 * 统一状态标签组件
 */
export const StatusTag: React.FC<StatusTagProps> = ({
  type,
  status,
  variant = 'subtle',
  size = 'default',
  showIcon = false,
  showBadge = false,
  customLabel,
  icon,
  tooltip,
  className = '',
  style,
  onClick,
}) => {
  const meta = resolveStatus(type, status);
  const tagStyle = computeTagStyle(meta, variant, size, !!onClick, style);

  // 决定显示的图标
  const resolvedIcon = icon !== undefined ? icon : showIcon ? renderStatusIcon(meta.iconName) : null;
  const resolvedLabel = customLabel !== undefined ? customLabel : meta.label;

  const tagNode = (
    <span
      role="status"
      aria-label={meta.ariaLabel}
      data-testid={`status-tag-${type}-${meta.code}`}
      data-domain={type}
      data-status={meta.code}
      data-variant={variant}
      data-size={size}
      className={`icg-status-tag icg-status-tag-${type} icg-status-tag-${meta.code} ${className}`.trim()}
      style={tagStyle}
      onClick={onClick}
    >
      {showBadge && (
        <span
          className="icg-status-tag-badge-dot"
          style={{
            width: size === 'small' ? 5 : 6,
            height: size === 'small' ? 5 : 6,
            borderRadius: '50%',
            backgroundColor: variant === 'solid' ? meta.solidText : meta.solidBg,
            flexShrink: 0,
          }}
        />
      )}
      {resolvedIcon && <span className="icg-status-tag-icon">{resolvedIcon}</span>}
      <span className="icg-status-tag-text">{resolvedLabel}</span>
    </span>
  );

  if (tooltip) {
    const tooltipContent = tooltip === true ? meta.description : tooltip;
    return <Tooltip title={tooltipContent}>{tagNode}</Tooltip>;
  }

  return tagNode;
};

// ============================================================================
// 便捷领域派生组件（供业务层直观引用）
// ============================================================================

export type DomainTagProps = Omit<StatusTagProps, 'type'>;

export const ProjectStatusTag: React.FC<DomainTagProps> = props => (
  <StatusTag type="project" {...props} />
);

export const ChapterStatusTag: React.FC<DomainTagProps> = props => (
  <StatusTag type="chapter" {...props} />
);

export const JobStatusTag: React.FC<DomainTagProps> = props => (
  <StatusTag type="job" {...props} />
);

export const CheckStatusTag: React.FC<DomainTagProps> = props => (
  <StatusTag type="check" {...props} />
);

export const ExportStatusTag: React.FC<DomainTagProps> = props => (
  <StatusTag type="export" {...props} />
);

export const LockStatusTag: React.FC<DomainTagProps> = props => (
  <StatusTag type="lock" {...props} />
);

export default StatusTag;
