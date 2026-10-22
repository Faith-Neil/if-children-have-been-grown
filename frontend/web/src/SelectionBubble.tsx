// 为什么有这个文件：为编辑台正文选区提供划词快捷操作气泡（Action Bubble）。
// 它解决什么问题：
// 1. 用户划选一段文字后，在选区上方自适应呈现轻量浮动操作条；
// 2. 提供「AI润色」（带入右侧助手 polish 场景）与「合规问答」（带入 compliance 场景）一键直达入口；
// 3. 支持「清除选区」快速收起，与右侧 AI 助手输入无缝联动。

import React from 'react';
import { Button, Space, Typography } from 'antd';
import {
  EditOutlined,
  SafetyCertificateOutlined,
  CloseOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

export interface SelectionBubbleProps {
  visible: boolean;
  position: { top: number; left: number } | null;
  selectedText: string;
  onPolish: (text: string) => void;
  onComplianceQa: (text: string) => void;
  onClear: () => void;
}

export const SelectionBubble: React.FC<SelectionBubbleProps> = ({
  visible,
  position,
  selectedText,
  onPolish,
  onComplianceQa,
  onClear,
}) => {
  if (!visible || !selectedText || !position) {
    return null;
  }

  const trimmed = selectedText.trim();
  if (trimmed.length === 0) {
    return null;
  }

  return (
    <div
      className="icg-selection-bubble"
      data-testid="selection-action-bubble"
      style={{
        position: 'absolute',
        top: Math.max(8, position.top),
        left: Math.max(16, position.left),
        transform: 'translate(-50%, -100%)',
        zIndex: 1050,
        backgroundColor: '#ffffff',
        border: '1px solid #d9e1ec',
        borderRadius: 8,
        boxShadow: '0 6px 16px 0 rgba(0, 0, 0, 0.08), 0 3px 6px -4px rgba(0, 0, 0, 0.12)',
        padding: '4px 8px',
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        userSelect: 'none',
        animation: 'bubbleFadeIn 0.15s ease-out',
      }}
      onMouseDown={e => {
        // 阻止点击气泡内部按钮导致编辑框失焦或取消选区
        e.preventDefault();
      }}
    >
      <div
        className="bubble-header"
        data-testid="bubble-selected-count"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          paddingRight: 6,
          borderRight: '1px solid #f0f0f0',
        }}
      >
        <ThunderboltOutlined style={{ color: '#722ed1', fontSize: 12 }} />
        <Text style={{ fontSize: 11, color: '#86909c' }}>
          已选 <b style={{ color: '#1d2129' }}>{trimmed.length}</b> 字
        </Text>
      </div>

      <Space size={4}>
        <Button
          size="small"
          type="primary"
          icon={<EditOutlined />}
          onClick={() => onPolish(trimmed)}
          data-testid="bubble-polish-btn"
          style={{
            fontSize: 12,
            height: 24,
            padding: '0 8px',
            backgroundColor: '#722ed1',
            borderColor: '#722ed1',
          }}
        >
          AI润色
        </Button>

        <Button
          size="small"
          type="default"
          icon={<SafetyCertificateOutlined style={{ color: '#1677ff' }} />}
          onClick={() => onComplianceQa(trimmed)}
          data-testid="bubble-compliance-btn"
          style={{
            fontSize: 12,
            height: 24,
            padding: '0 8px',
          }}
        >
          合规问答
        </Button>

        <Button
          size="small"
          type="text"
          icon={<CloseOutlined style={{ fontSize: 10, color: '#8c8c8c' }} />}
          onClick={onClear}
          data-testid="bubble-clear-btn"
          title="清除选区"
          style={{
            height: 24,
            width: 24,
            padding: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        />
      </Space>
    </div>
  );
};
