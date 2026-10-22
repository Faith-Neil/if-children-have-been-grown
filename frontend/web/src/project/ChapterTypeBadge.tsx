// 为什么有这个文件：封装统一的章节类型徽标组件 ChapterTypeBadge。
// 它解决什么问题：
// 1. 直观区分专项方案、通用方案、系统生成、封面目录与不适用 5 类章节属性；
// 2. 系统生成章节与 AI 关联章节严格遵循色彩令牌与专属标识规范；
// 3. 支持 Tooltip 悬浮展示章节类型说明与适用场景。

import React, { type CSSProperties } from 'react';
import { Tag, Tooltip } from 'antd';
import {
  FileTextOutlined,
  AppstoreOutlined,
  ThunderboltOutlined,
  BookOutlined,
  StopOutlined,
} from '@ant-design/icons';
import {
  getChapterTypeMeta,
  type ChapterType,
} from './outline-tree.ts';

export interface ChapterTypeBadgeProps {
  type: ChapterType;
  showIcon?: boolean;
  showTooltip?: boolean;
  className?: string;
  style?: CSSProperties;
}

function getChapterTypeIcon(type: ChapterType) {
  switch (type) {
    case 'specialized':
      return <ThunderboltOutlined style={{ marginRight: 4 }} />;
    case 'general':
      return <FileTextOutlined style={{ marginRight: 4 }} />;
    case 'system_generated':
      return <AppstoreOutlined style={{ marginRight: 4 }} />;
    case 'cover_and_catalog':
      return <BookOutlined style={{ marginRight: 4 }} />;
    case 'not_applicable':
      return <StopOutlined style={{ marginRight: 4 }} />;
    default:
      return null;
  }
}

export function ChapterTypeBadge({
  type,
  showIcon = true,
  showTooltip = true,
  className = '',
  style,
}: ChapterTypeBadgeProps) {
  const meta = getChapterTypeMeta(type);
  const isSystemGenerated = type === 'system_generated';

  const badgeContent = (
    <Tag
      color={meta.color}
      className={`icg-chapter-type-badge ${isSystemGenerated ? 'is-system-generated' : ''} ${className}`}
      style={{
        borderRadius: 4,
        fontSize: 12,
        lineHeight: '20px',
        marginInlineEnd: 0,
        ...style,
      }}
      data-testid="chapter-type-badge"
      data-chapter-type={type}
    >
      {showIcon && getChapterTypeIcon(type)}
      {meta.label}
    </Tag>
  );

  if (showTooltip && meta.description) {
    return (
      <Tooltip title={meta.description} placement="top">
        {badgeContent}
      </Tooltip>
    );
  }

  return badgeContent;
}
