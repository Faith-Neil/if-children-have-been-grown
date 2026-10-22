// 为什么有这个文件：封装查看高敏个人信息留痕合规提示组件（MaskNoticeBanner / AuditTraceHint）。
// 它解决什么问题：落实 PRD v1.8 §5.4.5、§5.9.1 与 §7.3 审计留痕规范，在涉及敏感个人信息页面或模块呈现统一、合规且高对比度的留痕告警说明。

import React, { type CSSProperties } from 'react';
import { Alert, Space, Tooltip } from 'antd';
import {
  LockOutlined,
  SafetyCertificateOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import {
  DEFAULT_AUDIT_TRACE_NOTICE,
  DEFAULT_AUDIT_TRACE_DETAIL,
} from './company-mask-settings.ts';

export interface MaskNoticeBannerProps {
  /** 展示模式：'banner'（常规告警条，默认）| 'inline'（内联行提示）| 'compact'（带 Tooltip 紧凑图标） */
  mode?: 'banner' | 'inline' | 'compact';
  /** 主标题或主提示文案（默认规范文案：“当前页面涉及敏感个人信息，调阅完整值将被记录安全审计日志（操作人、时间、原因与网络环境）”） */
  message?: React.ReactNode;
  /** 补充说明或合规条款解释 */
  description?: React.ReactNode;
  /** 是否展示安全图标（默认 true） */
  showIcon?: boolean;
  /** 是否可关闭（默认 false，合规提示建议常驻） */
  closable?: boolean;
  /** 警告级别：'warning'（琥珀黄，默认）| 'info'（信息蓝） */
  type?: 'warning' | 'info';
  /** 自定义容器类名与样式 */
  className?: string;
  style?: CSSProperties;
  /** 自动化测试标识 */
  testId?: string;
}

/**
 * 高敏信息查看留痕合规警示横幅
 */
export function MaskNoticeBanner({
  mode = 'banner',
  message = DEFAULT_AUDIT_TRACE_NOTICE,
  description,
  showIcon = true,
  closable = false,
  type = 'warning',
  className = '',
  style,
  testId = 'mask-notice-banner',
}: MaskNoticeBannerProps) {
  // 1. 紧凑模式 (compact)：用于字段旁或表格小表头
  if (mode === 'compact') {
    return (
      <Tooltip
        title={
          <div style={{ maxWidth: 280, fontSize: 12 }}>
            <div>{message}</div>
            {description && <div style={{ marginTop: 4, opacity: 0.85 }}>{description}</div>}
          </div>
        }
      >
        <span
          className={`icg-audit-trace-compact ${className}`}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            cursor: 'help',
            color: '#b25900', // WCAG AA 4.5:1 对比度
            fontSize: 12,
            ...style,
          }}
          data-testid={testId}
        >
          {showIcon && <LockOutlined style={{ fontSize: 12 }} />}
          <span>审计留痕</span>
        </span>
      </Tooltip>
    );
  }

  // 2. 内联模式 (inline)：适用于卡片顶栏或表单分组标题旁
  if (mode === 'inline') {
    return (
      <div
        className={`icg-audit-trace-inline ${className}`}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          backgroundColor: '#fffbe6',
          border: '1px solid #ffe58f',
          borderRadius: 4,
          padding: '2px 8px',
          fontSize: 12,
          color: '#613400', // WCAG AA 4.5:1 对比度
          lineHeight: '20px',
          ...style,
        }}
        data-testid={testId}
      >
        {showIcon && <SafetyCertificateOutlined style={{ color: '#d46b08', fontSize: 13 }} />}
        <span className="icg-audit-trace-text">{message}</span>
      </div>
    );
  }

  // 3. 常规横幅模式 (banner)
  const isWarning = type === 'warning';
  const customIcon = showIcon ? (
    <SafetyCertificateOutlined
      style={{
        color: isWarning ? '#d46b08' : '#1e4db7',
        fontSize: 16,
      }}
    />
  ) : undefined;

  return (
    <Alert
      className={`icg-mask-notice-banner ${className}`}
      message={
        <span
          style={{
            fontWeight: 500,
            color: isWarning ? '#613400' : '#002c8c',
            fontSize: 13,
          }}
        >
          {message}
        </span>
      }
      description={
        description ? (
          <div style={{ marginTop: 4, fontSize: 12, color: isWarning ? '#873800' : '#1d2129' }}>
            {description}
          </div>
        ) : undefined
      }
      type={type}
      showIcon={showIcon}
      icon={customIcon}
      closable={closable}
      style={{
        marginBottom: 16,
        borderRadius: 6,
        backgroundColor: isWarning ? '#fffbe6' : '#e6f4ff',
        borderColor: isWarning ? '#ffe58f' : '#91caff',
        ...style,
      }}
      data-testid={testId}
    />
  );
}

/**
 * 查看留痕提示组件快捷别名 (AuditTraceHint)
 * 默认以内联或紧凑模式呈现，贴合字段及模块说明需求
 */
export function AuditTraceHint(props: MaskNoticeBannerProps) {
  return (
    <MaskNoticeBanner
      mode={props.mode || 'inline'}
      testId={props.testId || 'audit-trace-hint'}
      {...props}
    />
  );
}

export default MaskNoticeBanner;
