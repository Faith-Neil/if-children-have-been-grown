// 为什么有这个文件：封装通用的表单吸底操作条（FormActionFooter）。
// 它解决什么问题：
// 1. 固底吸附展示（Sticky Footer Bar），避免长表单滚至底部才能保存；
// 2. 实时显示“已修改 N 项”脏数据状态与 ★ 关键字段变更提示；
// 3. 规范化集成保存（Primary）、重置（Reset）、取消（Cancel）按钮与自定义操作扩展槽位；
// 4. 文字色彩与警示严格符合 WCAG AA 4.5:1 对比度标准。

import React, { type CSSProperties, type ReactNode } from 'react';
import { Button, Space, Tag, Typography } from 'antd';
import { CheckCircleOutlined, ExclamationCircleOutlined, ReloadOutlined, WarningOutlined } from '@ant-design/icons';

const { Text } = Typography;

export interface FormActionFooterProps {
  /** 是否存在未保存的修改 */
  isDirty?: boolean;
  /** 已修改字段数 */
  modifiedCount?: number;
  /** 已修改的 ★ 关键字段数 */
  starredModifiedCount?: number;
  /** 自定义修改摘要文案（缺省时根据 modifiedCount 自动生成） */
  summaryText?: string;
  /** 提交保存中 loading 状态 */
  loading?: boolean;
  /** 整栏是否禁用（例如无编辑权限） */
  disabled?: boolean;
  /** 提交按钮文字（默认 "保存"） */
  submitText?: string;
  /** 重置按钮文字（默认 "重置"） */
  resetText?: string;
  /** 取消按钮文字（默认 "取消"） */
  cancelText?: string;
  /** 是否显示提交按钮（默认 true） */
  showSubmit?: boolean;
  /** 是否显示重置按钮（默认 true） */
  showReset?: boolean;
  /** 是否显示取消按钮（默认 false） */
  showCancel?: boolean;
  /** 是否启用底部吸附（默认 true） */
  sticky?: boolean;
  /** 点击提交回调（htmlType 缺省为 submit） */
  onSubmit?: () => void;
  /** 点击重置回调 */
  onReset?: () => void;
  /** 点击取消回调 */
  onCancel?: () => void;
  /** 附加扩展内容（放在按钮右侧或左侧） */
  extra?: ReactNode;
  /** 自定义类名与样式 */
  className?: string;
  style?: CSSProperties;
}

export function FormActionFooter({
  isDirty = false,
  modifiedCount = 0,
  starredModifiedCount = 0,
  summaryText,
  loading = false,
  disabled = false,
  submitText = '保存',
  resetText = '重置',
  cancelText = '取消',
  showSubmit = true,
  showReset = true,
  showCancel = false,
  sticky = true,
  onSubmit,
  onReset,
  onCancel,
  extra,
  className = '',
  style,
}: FormActionFooterProps) {
  // 1. 生成已修改摘要文案
  let computedSummary = summaryText;
  if (!computedSummary) {
    if (!isDirty) {
      computedSummary = '表单内容与初始版本一致';
    } else if (starredModifiedCount > 0) {
      computedSummary = `已修改 ${modifiedCount} 项（含 ${starredModifiedCount} 项 ★ 关键字段）`;
    } else {
      computedSummary = `已修改 ${modifiedCount} 项`;
    }
  }

  return (
    <div
      className={`icg-form-sticky-footer ${sticky ? 'is-sticky' : ''} ${className}`}
      style={style}
      data-testid="form-action-footer"
    >
      <div className="icg-footer-inner">
        {/* 左侧：脏数据与 ★ 关键字段修改状态摘要 */}
        <div className="icg-footer-left-info" data-testid="form-footer-info">
          {isDirty ? (
            <Space size={8} wrap>
              <Tag
                color={starredModifiedCount > 0 ? 'warning' : 'blue'}
                className="icg-footer-modified-tag"
                data-testid="dirty-count-tag"
              >
                {starredModifiedCount > 0 ? (
                  <WarningOutlined style={{ marginRight: 4, color: '#9a5608' }} />
                ) : (
                  <ExclamationCircleOutlined style={{ marginRight: 4 }} />
                )}
                {computedSummary}
              </Tag>
              {starredModifiedCount > 0 && (
                <Text type="warning" style={{ fontSize: 12, color: '#9a5608' }}>
                  <WarningOutlined style={{ marginRight: 4 }} />
                  检测到 ★ 关键字段变动，保存后将需重新核对确认。
                </Text>
              )}
            </Space>
          ) : (
            <Space size={6} className="muted" style={{ fontSize: 13, color: '#86909c' }}>
              <CheckCircleOutlined style={{ color: '#00b42a' }} />
              <span>{computedSummary}</span>
            </Space>
          )}
        </div>

        {/* 右侧：操作按钮与额外插槽 */}
        <div className="icg-footer-right-actions">
          <Space size={12} wrap>
            {extra}

            {showCancel && (
              <Button
                onClick={onCancel}
                disabled={loading}
                data-testid="form-footer-cancel"
              >
                {cancelText}
              </Button>
            )}

            {showReset && (
              <Button
                onClick={onReset}
                disabled={disabled || loading || !isDirty}
                icon={<ReloadOutlined />}
                data-testid="form-footer-reset"
              >
                {resetText}
              </Button>
            )}

            {showSubmit && (
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                disabled={disabled}
                onClick={onSubmit}
                data-testid="form-footer-submit"
              >
                {submitText}
              </Button>
            )}
          </Space>
        </div>
      </div>
    </div>
  );
}

export default FormActionFooter;
