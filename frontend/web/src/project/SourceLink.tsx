// 为什么有这个文件：提取招标文件条款来源链接小组件（SourceLink）。
// 它解决什么问题：解耦招标原件页码定位展示与页面逻辑，统一在工作台各页签之间复用。

import React from 'react';
import { FileTextOutlined } from '@ant-design/icons';
import type { Source } from '../shared/types.ts';

export interface SourceLinkProps {
  source: Source | null;
  onClick: (source: Source) => void;
}

export function SourceLink({ source, onClick }: SourceLinkProps) {
  return source ? (
    <a className="source-link" onClick={() => onClick(source)}>
      <FileTextOutlined /> P.{source.page}
    </a>
  ) : (
    <span className="muted">服务承诺引用 · 无招标页码</span>
  );
}
