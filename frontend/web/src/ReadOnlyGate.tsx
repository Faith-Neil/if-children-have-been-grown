// 为什么有这个文件：封装统一的只读守卫与只读文本排版组件（ReadOnlyGate、ReadOnlyField）。
// 它解决什么问题：落实 PRD v1.8 §5.11.9 验收约束——“只读成员与集团管理员看到文本而非控件，不是渲染了 input/select 之后再去 disabled，而是在只读模式下直接渲染排版语义的 <span>、<p> 或纯文本展示”，并呈现多粒度只读横幅提示。

import React, { type CSSProperties, type ReactNode } from 'react';
import { useDataPermission, type UseDataPermissionOptions } from './useDataPermission.ts';
import type { DataPermissionResult, DataPermissionScope } from './data-permission.ts';
import { ReadonlyBanner, type ReadonlyBannerProps } from './StatusViews.tsx';
import type { Chapter, Volume } from './types.ts';

/* ========================================================================= */
/* 1. ReadOnlyGate 容器与横幅组件                                             */
/* ========================================================================= */

export interface ReadOnlyGateProps extends UseDataPermissionOptions {
  /** 手动指定只读状态（缺省时自动通过 useDataPermission 判定） */
  readOnly?: boolean;
  /** 权限范围 override */
  scope?: DataPermissionScope;
  /** 是否自动在顶部渲染只读提示横幅（默认 true） */
  showBanner?: boolean;
  /** 自定义横幅提示文案 */
  bannerReason?: string;
  /** 自定义横幅附加属性 */
  bannerProps?: Partial<ReadonlyBannerProps>;
  /** 只读态渲染的内容（排版文本或纯文本视图），若提供则只读态直接替代 children，杜绝渲染表单控件 */
  readOnlyView?: ReactNode | ((permission: DataPermissionResult) => ReactNode);
  /** readOnlyView 别名 */
  fallback?: ReactNode;
  /** 可编辑态渲染的内容（或以函数形式注入 permission） */
  children?: ReactNode | ((permission: DataPermissionResult) => ReactNode);
  /** 容器自定义类名与样式 */
  className?: string;
  style?: CSSProperties;
}

/**
 * 只读控制网关（支持只读横幅 + 纯文本/控件视图无感切换）
 */
export function ReadOnlyGate({
  readOnly: explicitReadOnly,
  scope: explicitScope,
  volume,
  volumeId,
  chapter,
  chapterId,
  role,
  userId,
  workspace,
  showBanner = true,
  bannerReason,
  bannerProps,
  readOnlyView,
  fallback,
  children,
  className = '',
  style,
}: ReadOnlyGateProps) {
  const permission = useDataPermission({
    volume,
    volumeId,
    chapter,
    chapterId,
    role,
    userId,
    workspace,
  });

  const isReadOnly = explicitReadOnly !== undefined ? explicitReadOnly : permission.readOnly;
  const currentScope = explicitScope ?? permission.scope;
  const reasonText = bannerReason ?? permission.readOnlyReason;

  if (isReadOnly) {
    const alternativeView = readOnlyView ?? fallback;
    return (
      <div
        className={`icg-readonly-gate icg-readonly-gate-active ${className}`}
        style={style}
        data-testid="readonly-gate-container"
        data-readonly="true"
        data-scope={currentScope}
      >
        {showBanner && (
          <ReadonlyBanner
            banner
            reason={reasonText}
            scope={permission.scopeName || currentScope}
            roleName={permission.roleLabel}
            style={{ marginBottom: 16 }}
            {...bannerProps}
          />
        )}
        {alternativeView ? (
          typeof alternativeView === 'function' ? (
            alternativeView(permission)
          ) : (
            alternativeView
          )
        ) : typeof children === 'function' ? (
          children(permission)
        ) : (
          children
        )}
      </div>
    );
  }

  return (
    <div
      className={`icg-readonly-gate icg-readonly-gate-writable ${className}`}
      style={style}
      data-testid="readonly-gate-container"
      data-readonly="false"
    >
      {typeof children === 'function' ? children(permission) : children}
    </div>
  );
}

export const ReadOnlyWrapper = ReadOnlyGate;

/* ========================================================================= */
/* 2. ReadOnlyField / ReadOnlyText 字段级纯文本与控件切换组件                 */
/* ========================================================================= */

export interface ReadOnlyFieldProps {
  /** 当前字段取值 */
  value?: any;
  /** 空值占位符（默认 '-'） */
  placeholder?: string;
  /** 是否处于只读状态（缺省为 false） */
  readOnly?: boolean;
  /** 自定义文本格式化渲染函数 */
  format?: (val: any) => ReactNode;
  /** 可编辑状态下的输入控件渲染函数 */
  renderControl?: () => ReactNode;
  /** 可编辑状态下的子控件 */
  children?: ReactNode;
  /** 自定义类名与样式 */
  className?: string;
  style?: CSSProperties;
  /** 测试标识 */
  testId?: string;
}

/**
 * 字段级文本/控件无缝切换组件
 *
 * 核心保障：只读模式下直接渲染排版语义 <span> 纯文本，完全杜绝在 DOM 中渲染 <input>/<textarea> 再 disabled
 */
export function ReadOnlyField({
  value,
  placeholder = '-',
  readOnly = false,
  format,
  renderControl,
  children,
  className = '',
  style,
  testId,
}: ReadOnlyFieldProps) {
  if (readOnly) {
    let displayText: ReactNode;
    if (format) {
      displayText = format(value);
    } else if (value === null || value === undefined || value === '') {
      displayText = placeholder;
    } else if (typeof value === 'boolean') {
      displayText = value ? '是' : '否';
    } else if (Array.isArray(value)) {
      displayText = value.length > 0 ? value.join('、') : placeholder;
    } else {
      displayText = String(value);
    }

    return (
      <span
        className={`icg-readonly-field-text ${className}`}
        style={{
          display: 'inline-block',
          color: '#1d2129',
          fontSize: 14,
          lineHeight: '32px',
          padding: '0 4px',
          ...style,
        }}
        data-testid={testId || 'readonly-text-field'}
      >
        {displayText}
      </span>
    );
  }

  if (renderControl) {
    return <>{renderControl()}</>;
  }

  return <>{children}</>;
}

export const ReadOnlyText = ReadOnlyField;
