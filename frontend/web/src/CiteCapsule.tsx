// 为什么有这个文件：为正文段落内联证据节点（.cite）提供胶囊徽标呈现与 Popover 悬浮卡片交互。
// 它解决什么问题：
// 1. 将 [证:ID] 和 [片:ID] 渲染为符合设计规范的紧凑胶囊；
// 2. 悬浮时呈现来源标题、资料编号、核验状态与有效期；
// 3. 点击提供“高亮此依据”交互，联动左侧/右侧写作来源定位。

import React, { useState } from 'react';
import { Popover, Tag, Button, Space } from 'antd';
import { FileTextOutlined, CheckCircleOutlined, ClockCircleOutlined, AimOutlined } from '@ant-design/icons';
import type { CiteKind, CitationMeta } from './cite-capsule.ts';
import { formatCiteLabel, parseCitations } from './cite-capsule.ts';

export interface CiteCapsuleProps {
  id: string;
  kind?: CiteKind;
  type?: CiteKind;
  meta?: Partial<CitationMeta>;
  onClick?: (id: string, kind: CiteKind) => void;
  onHighlightInSources?: (id: string, kind: CiteKind) => void;
  className?: string;
  style?: React.CSSProperties;
}

export const CiteCapsule: React.FC<CiteCapsuleProps> = ({
  id,
  kind,
  type,
  meta,
  onClick,
  onHighlightInSources,
  className = '',
  style,
}) => {
  const [open, setOpen] = useState(false);
  const actualKind: CiteKind = kind || type || 'evidence';

  const title = meta?.title || (actualKind === 'evidence' ? `资料证据 #${id}` : `方案片段 #${id}`);
  const code = meta?.code || id;
  const status = meta?.status || 'confirmed';
  const statusLabel = status === 'confirmed' || status === 'valid' ? '已核验' : '待核对';
  const statusColor = status === 'confirmed' || status === 'valid' ? 'success' : 'warning';
  const validUntil = meta?.validUntil;
  const quote = meta?.quote;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onClick) {
      onClick(id, actualKind);
    }
    if (onHighlightInSources) {
      onHighlightInSources(id, actualKind);
    }
  };

  const popoverContent = (
    <div
      className="cite-capsule-popover"
      data-testid="cite-popover-content"
      style={{ maxWidth: 300, fontSize: 12, lineHeight: 1.6 }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6, gap: 8 }}>
        <strong style={{ color: '#1d2129', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {title}
        </strong>
        <Tag color={kind === 'evidence' ? 'blue' : 'purple'} style={{ margin: 0, fontSize: 11, padding: '0 4px' }}>
          {kind === 'evidence' ? '资料证据' : '方案片段'}
        </Tag>
      </div>

      <div style={{ color: '#4e5969', marginBottom: 4 }}>
        <span style={{ color: '#86909c' }}>资料编号：</span>
        <code style={{ background: '#f2f3f5', padding: '1px 4px', borderRadius: 2, fontSize: 11 }}>{code}</code>
      </div>

      <div style={{ color: '#4e5969', marginBottom: 4 }}>
        <span style={{ color: '#86909c' }}>核验状态：</span>
        <Tag
          color={statusColor}
          icon={statusColor === 'success' ? <CheckCircleOutlined /> : <ClockCircleOutlined />}
          style={{ fontSize: 11, padding: '0 4px', margin: 0 }}
        >
          {statusLabel}
        </Tag>
      </div>

      {validUntil && (
        <div style={{ color: '#4e5969', marginBottom: 4 }}>
          <span style={{ color: '#86909c' }}>有效期至：</span>
          <span>{validUntil}</span>
        </div>
      )}

      {quote && (
        <div
          style={{
            marginTop: 6,
            padding: '6px 8px',
            backgroundColor: '#f7f8fa',
            borderLeft: '2px solid #1e4db7',
            borderRadius: 3,
            color: '#4e5969',
            fontSize: 11,
            maxHeight: 100,
            overflowY: 'auto',
          }}
        >
          {quote}
        </div>
      )}

      <div style={{ marginTop: 8, textAlign: 'right' }}>
        <Button
          size="small"
          type="primary"
          ghost
          icon={<AimOutlined />}
          onClick={handleClick}
          data-testid="cite-highlight-btn"
          style={{ fontSize: 11, height: 24, padding: '0 8px' }}
        >
          在写作来源中高亮
        </Button>
      </div>
    </div>
  );

  const isEvidence = kind === 'evidence';
  const tagColor = isEvidence ? '#1677ff' : '#722ed1';
  const tagBg = isEvidence ? '#e6f4ff' : '#f9f0ff';
  const tagBorder = isEvidence ? '#91caff' : '#d3adf7';

  return (
    <Popover
      content={popoverContent}
      title={null}
      open={open}
      onOpenChange={setOpen}
      placement="top"
      trigger="hover"
    >
      <span
        className={`icg-cite cite ${isEvidence ? 'cite-evidence' : 'cite-snippet'} ${className}`}
        data-testid="cite-capsule"
        data-cite-id={id}
        data-cite-type={kind}
        role="button"
        tabIndex={0}
        onClick={handleClick}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 3,
          padding: '1px 6px',
          margin: '0 3px',
          backgroundColor: tagBg,
          color: tagColor,
          border: `1px solid ${tagBorder}`,
          borderRadius: 10,
          fontSize: 11,
          fontFamily: 'SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace',
          fontWeight: 500,
          cursor: 'pointer',
          lineHeight: '18px',
          verticalAlign: 'baseline',
          transition: 'all 0.15s ease-in-out',
          ...style,
        }}
      >
        <FileTextOutlined style={{ fontSize: 10 }} />
        <span>{formatCiteLabel(actualKind || 'evidence', id)}</span>
      </span>
    </Popover>
  );
};

export interface RichParagraphWithCitesProps {
  text?: string;
  content?: string;
  knownCitations?: Record<string, Partial<CitationMeta>>;
  onCiteClick?: (id: string, kind: CiteKind) => void;
  className?: string;
  style?: React.CSSProperties;
}

/**
 * 将整段正文渲染为带有内联 .cite 胶囊的富段落组件
 */
export const RichParagraphWithCites: React.FC<RichParagraphWithCitesProps> = ({
  text,
  content,
  knownCitations,
  onCiteClick,
  className = '',
  style,
}) => {
  const actualText = content !== undefined ? content : text || '';
  if (!actualText) return null;

  const paragraphs = actualText.split('\n');

  return (
    <div className={`rich-paragraph-with-cites ${className}`} style={{ lineHeight: 1.8, ...style }}>
      {paragraphs.map((p, pIdx) => {
        if (!p.trim()) {
          return <p key={pIdx} style={{ margin: '8px 0', minHeight: 14 }}>&nbsp;</p>;
        }
        const segments = parseCitations(p, knownCitations);
        return (
          <p key={pIdx} style={{ margin: '8px 0' }}>
            {segments.map((seg, sIdx) => {
              if (seg.type === 'cite' && seg.citeMeta) {
                return (
                  <CiteCapsule
                    key={`${seg.citeMeta.id}-${sIdx}`}
                    id={seg.citeMeta.id}
                    kind={seg.citeMeta.kind}
                    meta={seg.citeMeta}
                    onClick={onCiteClick}
                  />
                );
              }
              return <React.Fragment key={sIdx}>{seg.content}</React.Fragment>;
            })}
          </p>
        );
      })}
    </div>
  );
};
