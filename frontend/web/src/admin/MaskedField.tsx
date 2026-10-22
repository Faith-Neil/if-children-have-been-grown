// 为什么有这个文件：封装高敏个人信息脱敏展示组件（MaskedField）。
// 它解决什么问题：落实 PRD v1.8 §5.4.5、§2.3 与 §5.9.1 规范，实现身份证、手机号、银行卡号等按表格规则掩码，集成 <Can perform="id_card:view"> 权限判定（仅 company_admin 与 data_admin 显示“查看完整值”），并调起查看原因必填弹窗。

import React, { useState, type CSSProperties } from 'react';
import { Button, Space, Tooltip } from 'antd';
import { EyeOutlined, LockOutlined } from '@ant-design/icons';
import {
  maskSensitiveValue,
  SENSITIVE_FIELD_LABELS,
  type MaskRule,
  type SensitiveFieldType,
} from './sensitive-mask.ts';
import { useCan } from '../shell/useCan.ts';
import { RevealFieldModal } from './RevealFieldModal.tsx';
import { useCompanyMaskSettings } from './useCompanyMaskSettings.ts';

export interface MaskedFieldProps {
  /** 完整明文（可传入，组件自动按规则掩码并提供调阅） */
  value?: string | null;
  /** 已脱敏遮蔽的文本（若外部已脱敏，优先展示） */
  maskedValue?: string;
  /** 敏感字段类型（默认 'id_card'） */
  fieldType?: SensitiveFieldType;
  /** 字段自定义显示名称（如“身份证号”） */
  fieldName?: string;
  /** 掩码规则（可配置 prefix, suffix, maskChar, fixedLength） */
  maskRule?: Partial<MaskRule>;
  /** 记录或人员唯一标识 ID（供审计追踪） */
  recordId?: string;
  /** 异步调阅完整值处理函数（接收 reason，返回完整明文） */
  onReveal?: (reason: string) => Promise<string | void> | string | void;
  /** 查看操作按钮文字（默认“查看完整值”） */
  actionText?: string;
  /** 是否有调阅权限（可选；缺省时自动通过 useCan('id_card:view') 核验） */
  canReveal?: boolean;
  /** 当无权限时的展示模式：'hide'（隐藏操作，默认）| 'disabled'（置灰并展示无权限 Tooltip） */
  unauthorizedMode?: 'hide' | 'disabled';
  /** 无权限置灰时的悬浮提示文案 */
  unauthorizedTooltip?: string;
  /** 弹窗自定义标题 */
  modalTitle?: string;
  /** 查看原因最小字数限制（默认 5 字） */
  minReasonLength?: number;
  /** 自定义容器类名与样式 */
  className?: string;
  style?: CSSProperties;
  /** 测试标识 */
  testId?: string;
}

/**
 * 高敏个人信息脱敏展示组件
 */
export function MaskedField({
  value,
  maskedValue,
  fieldType = 'id_card',
  fieldName,
  maskRule,
  recordId,
  onReveal,
  actionText = '查看完整值',
  canReveal: explicitCanReveal,
  unauthorizedMode = 'hide',
  unauthorizedTooltip,
  modalTitle,
  minReasonLength = 5,
  className = '',
  style,
  testId = 'masked-field',
}: MaskedFieldProps) {
  const [modalOpen, setModalOpen] = useState(false);
  const { getRule } = useCompanyMaskSettings();

  // 1. 计算显示掩码值：显式传入 maskRule 优先，未传时自适应公司动态规则
  const effectiveRule = maskRule || getRule(fieldType);
  const displayMasked =
    maskedValue ||
    (value !== null && value !== undefined && value !== ''
      ? maskSensitiveValue(value, fieldType, effectiveRule)
      : '-');

  // 2. 权限校验：查看完整高敏身份证号仅限 company_admin 与 data_admin
  const canViewAction = fieldType === 'id_card' ? 'id_card:view' : 'id_card:view';
  const permissionResult = useCan(canViewAction);
  const isAllowed = explicitCanReveal !== undefined ? explicitCanReveal : permissionResult.allowed;

  const resolvedFieldName = fieldName || SENSITIVE_FIELD_LABELS[fieldType] || '高敏信息';

  return (
    <span
      className={`icg-masked-field ${className}`}
      style={{ display: 'inline-flex', alignItems: 'center', gap: 6, ...style }}
      data-testid={testId}
    >
      {/* 掩码文本 */}
      <span
        className="icg-masked-value"
        data-testid="masked-value-text"
        style={{
          fontFamily: 'SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace',
          color: '#1d2129',
          fontSize: 14,
        }}
      >
        {displayMasked}
      </span>

      {/* 查看完整值入口 */}
      {isAllowed ? (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => setModalOpen(true)}
          style={{ padding: '0 4px', fontSize: 13, height: 'auto' }}
          data-testid="reveal-action-button"
        >
          {actionText}
        </Button>
      ) : unauthorizedMode === 'disabled' ? (
        <Tooltip
          title={
            unauthorizedTooltip ||
            permissionResult.reason ||
            '仅公司管理员与资料管理员可查看完整高敏信息'
          }
        >
          <Button
            type="link"
            size="small"
            disabled
            icon={<LockOutlined />}
            style={{ padding: '0 4px', fontSize: 13, height: 'auto' }}
            data-testid="reveal-action-disabled"
          >
            {actionText}
          </Button>
        </Tooltip>
      ) : null}

      {/* 调阅弹窗 */}
      <RevealFieldModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        fieldType={fieldType}
        fieldName={resolvedFieldName}
        maskedValue={displayMasked}
        fullValue={value}
        onReveal={onReveal}
        recordId={recordId}
        title={modalTitle}
        minReasonLength={minReasonLength}
      />
    </span>
  );
}

export default MaskedField;
