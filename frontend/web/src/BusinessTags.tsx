// 为什么有这个文件：封装前端统一业务小组件（LevelTag、AiTag、DirectTag、Cite、SourceBar）。
// 它解决什么问题：
// 1. LevelTag：条款级别标签（关键要求、一般条款、加分项、否决项、阻断），使用标准锁定色并满足 WCAG AA 4.5:1；
// 2. AiTag：AI 辅助生成/修改专用标签，严格锁定 AI 紫（#6E4BD8 / #A23CC8），防范紫色滥用；
// 3. DirectTag：系统直查/直接采用标签，使用蓝色浅底，严禁使用 AI 紫；
// 4. Cite：段落与资料引用标注组件，支持悬浮卡片查看来源元数据、版本号、有效期与摘录；
// 5. SourceBar：段落侧边 3px 色条或底部来源条，展示已确认资料名称、版本号与依据指纹溯源。

import React, { useState } from 'react';
import type { CSSProperties, MouseEvent, ReactNode } from 'react';
import { Button, Popover, Space, Tag, Tooltip } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  DatabaseOutlined,
  InfoCircleOutlined,
  LinkOutlined,
  MinusOutlined,
  PlusCircleOutlined,
  RobotOutlined,
  StarOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import {
  BIZ_COLOR_TOKENS,
  formatFingerprint,
  resolveAiTag,
  resolveCite,
  resolveDirectTag,
  resolveLevelTag,
  resolveSourceBar,
  type AiTagVariant,
  type CiteMetadata,
  type CiteType,
  type DirectTagVariant,
  type LevelTagType,
  type SourceKind,
} from './business-tags.ts';

// 导出核心纯函数与色彩常量供业务直接消费
export * from './business-tags.ts';

/* =========================================================================
 * 1. LevelTag 条款级别标签
 * ========================================================================= */
export interface LevelTagProps {
  level?: LevelTagType | string;
  solid?: boolean;
  label?: ReactNode;
  icon?: ReactNode;
  className?: string;
  style?: CSSProperties;
  onClick?: (e: MouseEvent<HTMLElement>) => void;
}

export const LevelTag: React.FC<LevelTagProps> = ({
  level = 'general',
  solid,
  label,
  icon,
  className = '',
  style,
  onClick,
}) => {
  const resolved = resolveLevelTag(level, {
    isSolid: solid,
    customLabel: typeof label === 'string' ? label : undefined,
  });

  const getIcon = () => {
    if (icon) return icon;
    switch (resolved.iconType) {
      case 'close-circle':
        return <CloseCircleOutlined />;
      case 'star':
        return <StarOutlined />;
      case 'warning':
        return <WarningOutlined />;
      case 'plus-circle':
        return <PlusCircleOutlined />;
      case 'check-circle':
        return <CheckCircleOutlined />;
      case 'info-circle':
        return <InfoCircleOutlined />;
      case 'minus':
      default:
        return <MinusOutlined />;
    }
  };

  const tagStyle: CSSProperties = {
    backgroundColor: resolved.bg,
    color: resolved.color,
    borderColor: resolved.border,
    fontWeight: resolved.isSolid ? 600 : 500,
    cursor: onClick ? 'pointer' : 'default',
    ...style,
  };

  return (
    <Tag
      data-testid="icg-level-tag"
      data-level={resolved.category}
      className={`icg-level-tag icg-level-${resolved.category} ${resolved.isSolid ? 'icg-level-solid' : ''} ${className}`}
      style={tagStyle}
      icon={getIcon()}
      role={resolved.ariaRole}
      aria-label={`条款级别：${label ?? resolved.label}`}
      onClick={onClick}
    >
      {label ?? resolved.label}
    </Tag>
  );
};

/* =========================================================================
 * 2. AiTag AI 辅助标签（严格锁定 AI 紫）
 * ========================================================================= */
export interface AiTagProps {
  variant?: AiTagVariant;
  solid?: boolean;
  label?: ReactNode;
  icon?: ReactNode;
  className?: string;
  style?: CSSProperties;
  onClick?: (e: MouseEvent<HTMLElement>) => void;
}

export const AiTag: React.FC<AiTagProps> = ({
  variant = 'suggestion',
  solid = false,
  label,
  icon,
  className = '',
  style,
  onClick,
}) => {
  const resolved = resolveAiTag(variant, {
    isSolid: solid,
    customLabel: typeof label === 'string' ? label : undefined,
  });

  const tagStyle: CSSProperties = {
    backgroundColor: resolved.bg,
    color: resolved.color,
    borderColor: resolved.border,
    fontWeight: resolved.isSolid ? 600 : 500,
    cursor: onClick ? 'pointer' : 'default',
    ...style,
  };

  return (
    <Tag
      data-testid="icg-ai-tag"
      data-variant={variant}
      className={`icg-ai-tag ${resolved.isSolid ? 'icg-ai-solid' : 'icg-ai-subtle'} ${className}`}
      style={tagStyle}
      icon={icon ?? <RobotOutlined />}
      role="status"
      aria-label={resolved.ariaLabel}
      onClick={onClick}
    >
      {label ?? resolved.label}
    </Tag>
  );
};

/* =========================================================================
 * 3. DirectTag 直接响应/直接采用标签（系统直查深蓝，不用 AI 紫）
 * ========================================================================= */
export interface DirectTagProps {
  variant?: DirectTagVariant;
  label?: ReactNode;
  icon?: ReactNode;
  className?: string;
  style?: CSSProperties;
  onClick?: (e: MouseEvent<HTMLElement>) => void;
}

export const DirectTag: React.FC<DirectTagProps> = ({
  variant = 'direct',
  label,
  icon,
  className = '',
  style,
  onClick,
}) => {
  const resolved = resolveDirectTag(variant, typeof label === 'string' ? label : undefined);

  const tagStyle: CSSProperties = {
    backgroundColor: resolved.bg,
    color: resolved.color,
    borderColor: resolved.border,
    cursor: onClick ? 'pointer' : 'default',
    fontWeight: 500,
    ...style,
  };

  return (
    <Tag
      data-testid="icg-direct-tag"
      data-variant={variant}
      className={`icg-direct-tag direct-tag ${className}`}
      style={tagStyle}
      icon={icon ?? <DatabaseOutlined />}
      role="status"
      aria-label={resolved.ariaLabel}
      onClick={onClick}
    >
      {label ?? resolved.label}
    </Tag>
  );
};

/* =========================================================================
 * 4. Cite 资料与正文段落引用标注组件（支持悬浮查看引用片段与来源）
 * ========================================================================= */
export interface CiteProps {
  type?: CiteType;
  marker?: ReactNode;
  metadata?: CiteMetadata;
  popoverContent?: ReactNode;
  className?: string;
  style?: CSSProperties;
  onClick?: (e: MouseEvent<HTMLElement>, meta?: CiteMetadata) => void;
  disabled?: boolean;
}

export const Cite: React.FC<CiteProps> = ({
  type = 'evidence',
  marker,
  metadata,
  popoverContent,
  className = '',
  style,
  onClick,
  disabled = false,
}) => {
  const resolved = resolveCite(type, marker, metadata);
  const [open, setOpen] = useState(false);

  // 渲染悬浮卡片内容
  const renderPopover = () => {
    if (popoverContent) return popoverContent;
    const m = resolved.metadata;
    return (
      <div className="icg-cite-popover" style={{ maxWidth: 320, fontSize: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6, gap: 8 }}>
          <strong style={{ color: BIZ_COLOR_TOKENS.directText, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {m.title || (type === 'tender' ? '招标文件原文' : type === 'snippet' ? '方案片段' : '资料证据')}
          </strong>
          {m.version !== undefined && <Tag style={{ fontSize: 11, lineHeight: '18px', padding: '0 4px' }}>v{m.version}</Tag>}
        </div>
        {m.page !== undefined && <div style={{ color: '#4E5969', marginBottom: 4 }}>页码位置：第 {m.page} 页</div>}
        {m.validUntil && <div style={{ color: '#4E5969', marginBottom: 4 }}>有效期至：{m.validUntil}</div>}
        {m.status && (
          <div style={{ color: '#4E5969', marginBottom: 4 }}>
            确认状态：<span style={{ color: m.status === 'confirmed' ? '#2B9D5C' : '#9A5608' }}>{m.status === 'confirmed' ? '已确认' : m.status}</span>
          </div>
        )}
        {m.assignee && <div style={{ color: '#4E5969', marginBottom: 4 }}>责任人：{m.assignee}</div>}
        {m.fingerprint && (
          <div style={{ color: '#86909C', fontSize: 11, marginBottom: 4, fontFamily: 'monospace' }}>
            依据指纹：{formatFingerprint(m.fingerprint)}
          </div>
        )}
        {m.quote && (
          <div
            style={{
              marginTop: 6,
              padding: '6px 8px',
              backgroundColor: '#F7F8FA',
              borderLeft: '2px solid #B7C9EE',
              borderRadius: 3,
              color: '#4E5969',
              lineHeight: 1.6,
              maxHeight: 120,
              overflow: 'auto',
            }}
          >
            {m.quote}
          </div>
        )}
      </div>
    );
  };

  const handleClick = (e: MouseEvent<HTMLElement>) => {
    if (disabled) return;
    if (onClick) onClick(e, resolved.metadata);
  };

  // 变量类型行内高亮渲染（黄底下划线）
  if (resolved.type === 'fact') {
    return (
      <Popover content={renderPopover()} title="项目事实 / 变量来源" open={disabled ? false : open} onOpenChange={setOpen}>
        <span
          data-testid="icg-cite-fact"
          tabIndex={0}
          role="button"
          aria-label={resolved.ariaLabel}
          className={`icg-cite icg-cite-fact ${className}`}
          style={{
            backgroundColor: resolved.bg,
            color: resolved.color,
            borderBottom: `2px solid ${resolved.border}`,
            padding: '1px 4px',
            borderRadius: 2,
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            fontSize: 12,
            fontWeight: 500,
            ...style,
          }}
          onClick={handleClick}
        >
          {marker ?? resolved.marker}
        </span>
      </Popover>
    );
  }

  // 无来源灰标签渲染
  if (resolved.type === 'none') {
    return (
      <Tag
        data-testid="icg-cite-none"
        className={`icg-cite icg-cite-none ${className}`}
        style={{
          backgroundColor: resolved.bg,
          color: resolved.color,
          borderColor: resolved.border,
          fontSize: 11,
          ...style,
        }}
        role="note"
        aria-label="无知识库来源"
      >
        {marker ?? resolved.marker}
      </Tag>
    );
  }

  // 上标引用方块渲染（证据、方案片段、招标原文）
  const citeElement = (
    <span
      data-testid="icg-cite-anchor"
      tabIndex={0}
      role="doc-biblioref"
      aria-label={resolved.ariaLabel}
      className={`icg-cite cite ${type === 'snippet' ? 'snippet' : ''} ${type === 'tender' ? 'tender' : ''} ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '0 4px',
        margin: '0 2px',
        backgroundColor: resolved.bg,
        color: resolved.color,
        border: `1px solid ${resolved.border}`,
        borderRadius: 3,
        fontSize: 11,
        lineHeight: '16px',
        verticalAlign: 'super',
        cursor: disabled ? 'default' : 'pointer',
        userSelect: 'none',
        fontWeight: 500,
        ...style,
      }}
      onClick={handleClick}
    >
      {marker ?? resolved.marker}
    </span>
  );

  return (
    <Popover
      content={renderPopover()}
      title={type === 'tender' ? '招标原文出处' : type === 'snippet' ? '方案片段溯源' : '资料证据出处'}
      open={disabled ? false : open}
      onOpenChange={setOpen}
    >
      {citeElement}
    </Popover>
  );
};

/* =========================================================================
 * 5. SourceBar 底部或段落侧边来源条
 * ========================================================================= */
export interface SourceBarProps {
  kind?: SourceKind;
  layout?: 'paragraph' | 'bottom' | 'inline';
  sourceName?: string;
  version?: string | number;
  fingerprint?: string | null;
  status?: 'confirmed' | 'stale' | 'pending' | 'review_required' | string;
  statusText?: string;
  assignee?: string;
  updatedAt?: string;
  quote?: string;
  extraActions?: ReactNode;
  onVerifySource?: () => void;
  className?: string;
  style?: CSSProperties;
  children?: ReactNode;
}

export const SourceBar: React.FC<SourceBarProps> = ({
  kind = 'evidence',
  layout = 'paragraph',
  sourceName,
  version,
  fingerprint,
  status = 'confirmed',
  statusText,
  assignee,
  updatedAt,
  quote,
  extraActions,
  onVerifySource,
  className = '',
  style,
  children,
}) => {
  const resolved = resolveSourceBar({
    kind,
    sourceName,
    version,
    fingerprint,
    status,
    statusText,
  });

  // 1. 段落侧边 3px 色条布局（gutter / paragraph）
  if (layout === 'paragraph') {
    const popoverContent = (
      <div style={{ maxWidth: 300, fontSize: 12 }}>
        <div style={{ fontWeight: 600, color: '#1D2129', marginBottom: 4 }}>{resolved.sourceName}</div>
        <div style={{ color: '#4E5969', marginBottom: 3 }}>
          来源类型：<span style={{ color: resolved.color }}>{resolved.kindLabel}</span>
          {resolved.versionLabel && <span> · {resolved.versionLabel}</span>}
        </div>
        <div style={{ color: '#4E5969', marginBottom: 3 }}>
          状态：
          <span style={{ color: resolved.isStale ? '#9A5608' : '#2B9D5C', fontWeight: 500 }}>
            {resolved.statusLabel}
          </span>
        </div>
        {assignee && <div style={{ color: '#4E5969', marginBottom: 3 }}>写入人：{assignee}</div>}
        {updatedAt && <div style={{ color: '#4E5969', marginBottom: 3 }}>更新时间：{updatedAt}</div>}
        {resolved.formattedFingerprint && (
          <div style={{ color: '#86909C', fontSize: 11, fontFamily: 'monospace' }}>
            依据指纹：{resolved.formattedFingerprint}
          </div>
        )}
        {quote && (
          <div
            style={{
              marginTop: 6,
              padding: '4px 6px',
              backgroundColor: '#F7F8FA',
              borderLeft: `2px solid ${resolved.color}`,
              fontSize: 11,
              color: '#4E5969',
            }}
          >
            {quote}
          </div>
        )}
        {onVerifySource && (
          <div style={{ marginTop: 8 }}>
            <Button size="small" type="primary" onClick={onVerifySource}>
              核对最新来源
            </Button>
          </div>
        )}
      </div>
    );

    return (
      <div
        data-testid="icg-source-bar-paragraph"
        data-kind={kind}
        className={`icg-source-bar-paragraph icg-source-${kind} ${className}`}
        style={{
          borderLeft: `3px solid ${resolved.color}`,
          paddingLeft: 12,
          position: 'relative',
          margin: '8px 0',
          ...style,
        }}
        role="region"
        aria-label={resolved.ariaLabel}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
          <Popover content={popoverContent} title="段落来源溯源">
            <span
              tabIndex={0}
              role="button"
              style={{
                fontSize: 11,
                padding: '1px 6px',
                borderRadius: 3,
                backgroundColor: resolved.bg,
                color: resolved.color,
                border: `1px solid ${resolved.color}40`,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
                fontWeight: 500,
              }}
            >
              <LinkOutlined />
              {resolved.kindLabel}
              {resolved.versionLabel && ` ${resolved.versionLabel}`}
              {resolved.isStale && <span style={{ color: '#9A5608' }}> (待核对)</span>}
            </span>
          </Popover>
          {resolved.formattedFingerprint && (
            <span style={{ fontSize: 11, color: '#86909C', fontFamily: 'monospace' }}>
              {resolved.formattedFingerprint}
            </span>
          )}
        </div>
        {children}
      </div>
    );
  }

  // 2. 底部或独立来源条布局（bottom / bar）
  return (
    <div
      data-testid="icg-source-bar-bottom"
      data-kind={kind}
      className={`icg-source-bar-bottom ${resolved.isStale ? 'icg-source-stale' : ''} ${className}`}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 8,
        padding: '8px 12px',
        backgroundColor: resolved.isStale ? '#FFFBE6' : '#F7F8FA',
        border: `1px solid ${resolved.isStale ? '#FFE58F' : '#E8EBF0'}`,
        borderLeft: `4px solid ${resolved.color}`,
        borderRadius: 4,
        fontSize: 12,
        margin: '10px 0',
        ...style,
      }}
      role="region"
      aria-label={resolved.ariaLabel}
    >
      <Space wrap size={8} style={{ minWidth: 0 }}>
        <Tag
          style={{
            backgroundColor: resolved.bg,
            color: resolved.color,
            borderColor: `${resolved.color}50`,
            fontWeight: 500,
          }}
        >
          {resolved.kindLabel}
        </Tag>
        <strong style={{ color: '#1D2129' }}>{resolved.sourceName}</strong>
        {resolved.versionLabel && <Tag style={{ fontSize: 11, lineHeight: '18px', padding: '0 4px' }}>{resolved.versionLabel}</Tag>}
        <Tag color={resolved.isStale ? 'warning' : 'success'}>{resolved.statusLabel}</Tag>
        {resolved.formattedFingerprint && (
          <Tooltip title={`完整依据指纹：${fingerprint}`}>
            <span
              style={{
                fontFamily: 'monospace',
                fontSize: 11,
                color: '#4E5969',
                backgroundColor: '#FFFFFF',
                padding: '1px 5px',
                border: '1px solid #DCDFE6',
                borderRadius: 3,
              }}
            >
              {resolved.formattedFingerprint}
            </span>
          </Tooltip>
        )}
      </Space>

      <Space wrap size={8}>
        {extraActions}
        {onVerifySource && (
          <Button size="small" type={resolved.isStale ? 'primary' : 'default'} onClick={onVerifySource}>
            {resolved.isStale ? '核对最新来源' : '重新核对'}
          </Button>
        )}
      </Space>
    </div>
  );
};
