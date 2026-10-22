// 为什么有这个文件：封装增值理由编辑弹窗 ValueAddedReasonModal。
// 它解决什么问题：
// 1. 为特定章节（特别是专项方案章节）编辑或维护增值理由，阐述方案优势与超出招标文件承诺；
// 2. 提供预置增值模板一键快速填入，提高标书编制效率；
// 3. 严格控制字数上限（500 字）并提供直观字符统计，支持数据权限只读态拦截。

import React, { useEffect, useState } from 'react';
import { Alert, Button, Form, Input, Modal, Space, Tag, Typography } from 'antd';
import { BulbOutlined, EditOutlined, SaveOutlined } from '@ant-design/icons';
import {
  VALUE_ADDED_PRESETS,
  validateValueAddedReason,
  type ChapterOutlineNode,
} from './outline-tree.ts';
import { ChapterTypeBadge } from './ChapterTypeBadge.tsx';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

export interface ValueAddedReasonModalProps {
  open: boolean;
  chapter?: ChapterOutlineNode | null;
  readOnly?: boolean;
  readOnlyReason?: string;
  onSave: (chapterId: string, valueAddedReason: string) => void;
  onCancel: () => void;
}

export function ValueAddedReasonModal({
  open,
  chapter,
  readOnly = false,
  readOnlyReason,
  onSave,
  onCancel,
}: ValueAddedReasonModalProps) {
  const [reasonText, setReasonText] = useState('');
  const [errorText, setErrorText] = useState<string | null>(null);

  useEffect(() => {
    if (chapter) {
      setReasonText(chapter.valueAddedReason || '');
      setErrorText(null);
    }
  }, [chapter, open]);

  const handleApplyPreset = (preset: string) => {
    if (readOnly) return;
    if (!reasonText || reasonText.trim() === '') {
      setReasonText(preset);
    } else {
      setReasonText(`${reasonText}\n${preset}`);
    }
    setErrorText(null);
  };

  const handleSave = () => {
    if (readOnly || !chapter) return;
    const validation = validateValueAddedReason(reasonText, chapter.chapterType);
    if (!validation.valid) {
      setErrorText(validation.error || '增值理由格式有误');
      return;
    }
    onSave(chapter.id, reasonText.trim());
  };

  if (!chapter) return null;

  return (
    <Modal
      title={
        <Space align="center">
          <EditOutlined style={{ color: '#1e4db7' }} />
          <span>编辑章节增值理由</span>
        </Space>
      }
      open={open}
      onCancel={onCancel}
      width={640}
      destroyOnClose
      footer={[
        <Button key="cancel" onClick={onCancel}>
          取消
        </Button>,
        <Button
          key="save"
          type="primary"
          icon={<SaveOutlined />}
          disabled={readOnly}
          onClick={handleSave}
          data-testid="value-added-save-btn"
        >
          保存理由
        </Button>,
      ]}
      data-testid="value-added-modal"
    >
      {/* 只读拦截提示 */}
      {readOnly && (
        <Alert
          type="warning"
          showIcon
          message="只读模式"
          description={readOnlyReason || '当前处于只读模式，无法修改增值理由。'}
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 章节概要信息 */}
      <div className="icg-modal-chapter-info" style={{ marginBottom: 16, padding: '10px 14px', background: '#f7f8fa', borderRadius: 6 }}>
        <Space wrap size={12} align="center">
          <Text strong style={{ fontSize: 14 }}>
            {chapter.chapterNumber ? `${chapter.chapterNumber} ` : ''}
            {chapter.title}
          </Text>
          <ChapterTypeBadge type={chapter.chapterType} />
          {chapter.isStarred && <Tag color="error">星号条款 ★</Tag>}
          {chapter.isBlocker && <Tag color="volcano">废标条款</Tag>}
        </Space>
      </div>

      <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 12 }}>
        说明：增值理由用于在投标方案中突出本章节的亮点设计、超越招标文件基础要求的服务承诺与加分优势，将作为后续 AI 章节生成与建议的要点输入。
      </Paragraph>

      {/* 快捷预置模板选择 */}
      {!readOnly && (
        <div style={{ marginBottom: 14 }}>
          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
            <BulbOutlined style={{ marginRight: 4, color: '#faad14' }} />
            常用增值理由模板（点击插入）：
          </Text>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {VALUE_ADDED_PRESETS.map((preset, index) => (
              <Button
                key={index}
                size="small"
                type="dashed"
                style={{
                  textAlign: 'left',
                  height: 'auto',
                  whiteSpace: 'normal',
                  padding: '6px 10px',
                  fontSize: 12,
                  color: '#4e5969',
                }}
                onClick={() => handleApplyPreset(preset)}
                data-testid={`preset-item-${index}`}
              >
                + {preset}
              </Button>
            ))}
          </div>
        </div>
      )}

      {/* 文本域输入 */}
      <Form.Item
        label={<span style={{ fontWeight: 500 }}>增值理由与方案亮点阐述</span>}
        validateStatus={errorText ? 'error' : undefined}
        help={errorText}
        style={{ marginBottom: 8 }}
      >
        <TextArea
          rows={5}
          maxLength={500}
          showCount
          disabled={readOnly}
          value={reasonText}
          onChange={e => {
            setReasonText(e.target.value);
            if (errorText) setErrorText(null);
          }}
          placeholder="请输入本章节的方案亮点与增值承诺（例如超出技术要求的指标、专属售后保障团队等）..."
          data-testid="value-added-textarea"
          style={{ fontSize: 13, lineHeight: 1.6 }}
        />
      </Form.Item>
    </Modal>
  );
}
