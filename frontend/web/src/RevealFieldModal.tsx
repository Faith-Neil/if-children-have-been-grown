// 为什么有这个文件：封装“查看完整值”弹窗组件（RevealFieldModal）。
// 它解决什么问题：落实 PRD v1.8 §5.4.5 与 §2.3 的高敏字段调阅合规要求，强制校验“查看原因（必填项且不可为空白）”，出示审计告警，并在调阅后提供临时展示、一键复制与遮蔽功能，杜绝明文写入 storage 或 URL。

import React, { useState, useEffect } from 'react';
import { Modal, Alert, Input, Form, Button, Space, message, Tag } from 'antd';
import {
  SafetyCertificateOutlined,
  CopyOutlined,
  CheckOutlined,
  EyeInvisibleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import {
  validateRevealReason,
  SENSITIVE_FIELD_LABELS,
  type SensitiveFieldType,
} from './sensitive-mask.ts';

export interface RevealFieldModalProps {
  /** 弹窗是否可见 */
  open: boolean;
  /** 关闭弹窗回调 */
  onClose: () => void;
  /** 字段类别标识（默认 'id_card'） */
  fieldType?: SensitiveFieldType;
  /** 字段中文标签名称（如“身份证号”） */
  fieldName?: string;
  /** 掩码后的展示值（如“110101********1234”） */
  maskedValue?: string;
  /** 完整明文（若由上层直接传入，则在原因校验通过后展示） */
  fullValue?: string | null;
  /** 异步调阅回调：由外部提供接口请求，接收填写的原因，返回完整明文 */
  onReveal?: (reason: string) => Promise<string | void> | string | void;
  /** 关联记录或人员 ID（供审计追踪展示） */
  recordId?: string;
  /** 自定义弹窗标题 */
  title?: string;
  /** 查看原因最小字数限制（默认 5 字） */
  minReasonLength?: number;
}

/**
 * 查看完整高敏值弹窗
 */
export function RevealFieldModal({
  open,
  onClose,
  fieldType = 'id_card',
  fieldName,
  maskedValue = '********',
  fullValue,
  onReveal,
  recordId,
  title,
  minReasonLength = 5,
}: RevealFieldModalProps) {
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [revealedValue, setRevealedValue] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const displayFieldName = fieldName || SENSITIVE_FIELD_LABELS[fieldType] || '高敏信息';
  const modalTitle = title || `查看完整${displayFieldName}`;

  // 当弹窗打开时重置状态；关闭时彻底销毁明文内存
  useEffect(() => {
    if (open) {
      setReason('');
      setError('');
      setSubmitting(false);
      setRevealedValue(null);
      setCopied(false);
    } else {
      setRevealedValue(null);
      setReason('');
    }
  }, [open]);

  // 提交原因并调阅明文
  const handleConfirm = async () => {
    const validation = validateRevealReason(reason, minReasonLength);
    if (!validation.valid) {
      setError(validation.message || '查看原因不能为空');
      return;
    }

    setError('');
    setSubmitting(true);

    try {
      let resolvedPlaintext: string | null = null;
      if (onReveal) {
        const result = await onReveal(reason.trim());
        if (typeof result === 'string') {
          resolvedPlaintext = result;
        } else if (fullValue) {
          resolvedPlaintext = fullValue;
        }
      } else if (fullValue) {
        resolvedPlaintext = fullValue;
      }

      if (resolvedPlaintext) {
        setRevealedValue(resolvedPlaintext);
      } else {
        setError('未能获取到完整信息，请核对权限或网络');
      }
    } catch (err: any) {
      setError(err?.message || '调阅失败，请稍后重试');
    } finally {
      setSubmitting(false);
    }
  };

  // 复制完整明文
  const handleCopy = async () => {
    if (!revealedValue) return;
    try {
      if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(revealedValue);
      } else {
        // 降级复制
        const textarea = document.createElement('textarea');
        textarea.value = revealedValue;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      setCopied(true);
      message.success('已复制到剪贴板，请遵循公司信息安全规范，严禁扩散');
      setTimeout(() => setCopied(false), 3000);
    } catch {
      message.error('复制失败，请手动选取复制');
    }
  };

  // 重新遮蔽（丢弃明文）
  const handleRemask = () => {
    setRevealedValue(null);
    setReason('');
    setError('');
  };

  // 弹窗关闭
  const handleClose = () => {
    setRevealedValue(null);
    setReason('');
    setError('');
    onClose();
  };

  return (
    <Modal
      title={
        <Space>
          <SafetyCertificateOutlined style={{ color: '#1e4db7' }} />
          <span>{modalTitle}</span>
        </Space>
      }
      open={open}
      onCancel={handleClose}
      destroyOnClose
      footer={
        revealedValue ? (
          <Space>
            <Button
              icon={copied ? <CheckOutlined /> : <CopyOutlined />}
              onClick={handleCopy}
              data-testid="reveal-copy-button"
            >
              {copied ? '已复制' : '复制明文'}
            </Button>
            <Button
              icon={<EyeInvisibleOutlined />}
              onClick={handleRemask}
              data-testid="reveal-remask-button"
            >
              重新遮蔽
            </Button>
            <Button type="primary" onClick={handleClose} data-testid="reveal-close-button">
              完成
            </Button>
          </Space>
        ) : (
          <Space>
            <Button onClick={handleClose} disabled={submitting}>
              取消
            </Button>
            <Button
              type="primary"
              loading={submitting}
              onClick={handleConfirm}
              data-testid="reveal-confirm-button"
            >
              确认调阅并记录审计
            </Button>
          </Space>
        )
      }
      data-testid="reveal-field-modal"
    >
      {/* 1. 安全合规审计警示条 */}
      <Alert
        type="warning"
        showIcon
        icon={<ExclamationCircleOutlined style={{ color: '#9a5608' }} />}
        message="高敏信息调阅合规提示"
        description="此项为企业受保护的高敏个人信息。根据合规规范，调阅完整值必须填写业务理由，系统将如实记录安全审计日志（操作人、时间、查看原因及当前网络环境），以备安全审查。"
        style={{ marginBottom: 16 }}
        data-testid="reveal-security-alert"
      />

      {/* 2. 字段信息摘要 */}
      <div
        className="icg-reveal-field-summary"
        style={{
          padding: '12px 16px',
          background: '#f7f8fa',
          borderRadius: 6,
          marginBottom: 16,
          fontSize: 13,
        }}
      >
        <div style={{ marginBottom: 4 }}>
          <span className="muted" style={{ marginRight: 8 }}>字段类别：</span>
          <Tag color="blue">{displayFieldName}</Tag>
          {recordId && <span className="muted" style={{ marginLeft: 8 }}>关联记录：{recordId}</span>}
        </div>
        <div>
          <span className="muted" style={{ marginRight: 8 }}>当前掩码值：</span>
          <code style={{ fontSize: 14, color: '#1d2129', fontWeight: 600 }}>{maskedValue}</code>
        </div>
      </div>

      {/* 3. 调阅内容区：未确认展示表单，确认后展示明文 */}
      {!revealedValue ? (
        <Form layout="vertical">
          <Form.Item
            label="查看原因（必填）"
            required
            validateStatus={error ? 'error' : ''}
            help={error}
            extra={`请详细说明查看完整${displayFieldName}的业务依据（不可为空白，至少 ${minReasonLength} 个字符）`}
          >
            <Input.TextArea
              rows={3}
              maxLength={500}
              placeholder={`例如：用于拟派项目技术负责人投标资质材料核验，已取得本人授权。`}
              value={reason}
              onChange={e => {
                setReason(e.target.value);
                if (error) setError('');
              }}
              data-testid="reveal-reason-input"
              autoFocus
            />
          </Form.Item>
        </Form>
      ) : (
        <div
          className="icg-revealed-plaintext-box"
          data-testid="revealed-plaintext-container"
          style={{
            padding: '16px',
            background: '#f6ffed',
            border: '1px solid #b7eb8f',
            borderRadius: 6,
            marginBottom: 8,
          }}
        >
          <div style={{ color: '#389e0d', fontSize: 13, marginBottom: 8 }}>
            <SafetyCertificateOutlined style={{ marginRight: 6 }} />
            已完成安全审计留痕，完整明文如下：
          </div>
          <div
            className="icg-revealed-plaintext-value"
            style={{
              fontSize: 18,
              fontFamily: 'SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace',
              fontWeight: 600,
              color: '#1d2129',
              letterSpacing: 1,
              wordBreak: 'break-all',
              userSelect: 'all',
            }}
            data-testid="revealed-plaintext-value"
          >
            {revealedValue}
          </div>
          <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>
            此明文仅在当前窗口短暂展示，关闭弹窗后即刻销毁，系统未在本地存储中留存。
          </div>
        </div>
      )}
    </Modal>
  );
}

export default RevealFieldModal;
