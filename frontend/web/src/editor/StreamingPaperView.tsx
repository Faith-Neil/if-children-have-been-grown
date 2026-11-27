// 为什么有这个文件：生成中的正文不能被 TipTap 高频整树重建。
// 它解决什么问题：流式期间用同一套纸面样式只读渲染，完成后再静默交接回可编辑器。

import React, { useRef } from 'react';
import { blockIndexAtLine, growthFrontierLine, parseStreamingInline, parseStreamingMarkdownTracked, stableInlineChunks, type StreamBlock, type StreamInlineNode } from './streaming-markdown';
import { streamingStageLabel, type StreamStageName } from './section-stream';

export type StreamingStage = StreamStageName;

function InlineNodes({ nodes, animated, blockId }: { nodes: StreamInlineNode[]; animated: boolean; blockId: string }) {
  // 所有块都使用同一套起点稳定 key；活跃块只是多一层一次性进入动画，块完成后不重挂载旧文字。
  const chunks = stableInlineChunks(nodes, blockId);
  return <>
    {chunks.map(chunk => {
      let body: React.ReactNode = chunk.text;
      if (chunk.underline) body = <u>{body}</u>;
      if (chunk.bold) body = <strong>{body}</strong>;
      return <span key={chunk.key} className={animated ? 'stream-chunk-enter' : undefined}>{body}</span>;
    })}
  </>;
}

function Cursor({ show, ending }: { show: boolean; ending: boolean }) {
  return show ? <span className={`stream-cursor${ending ? ' is-ending' : ''}`} data-testid="stream-cursor" aria-hidden="true" /> : null;
}

function BlockView({ block, active, showCursor, cursorEnding }: { block: StreamBlock; active: boolean; showCursor: boolean; cursorEnding: boolean }) {
  const cursor = <Cursor show={active && showCursor} ending={cursorEnding} />;
  if (block.type === 'blank') return <p aria-hidden="true"><br /></p>;
  if (block.type === 'heading') {
    const TagName = `h${Math.min(6, block.level)}` as keyof JSX.IntrinsicElements;
    return <TagName><InlineNodes nodes={block.nodes} animated={active} blockId={block.id} />{cursor}</TagName>;
  }
  if (block.type === 'paragraph') return <p><InlineNodes nodes={block.nodes} animated={active} blockId={block.id} />{cursor}</p>;
  if (block.type === 'list') {
    const items = block.items.map((item, index) => <li key={`${block.id}:item:${index}`}><p><InlineNodes nodes={item} animated={active} blockId={`${block.id}:item:${index}`} /></p></li>);
    return <>{block.ordered ? <ol>{items}</ol> : <ul>{items}</ul>}{cursor}</>;
  }
  if (block.type === 'table-placeholder') {
    return <div className="stream-table-placeholder" data-testid="stream-table-placeholder" aria-live="polite">
      <span className="stream-shimmer-line wide" />
      <span>正在生成结构化表格…</span>
    </div>;
  }
  if (block.type === 'table') {
    return <><table>
      <thead><tr>{block.header.map((cell, index) => <th key={`${block.id}:h:${index}`}><p><InlineNodes nodes={parseStreamingInline(cell)} animated={false} blockId={`${block.id}:h:${index}`} /></p></th>)}</tr></thead>
      <tbody>{block.rows.map((row, rowIndex) => <tr key={`${block.id}:r:${rowIndex}`}>{row.map((cell, cellIndex) => <td key={`${block.id}:r:${rowIndex}:c:${cellIndex}`}><p><InlineNodes nodes={parseStreamingInline(cell)} animated={false} blockId={`${block.id}:r:${rowIndex}:c:${cellIndex}`} /></p></td>)}</tr>)}</tbody>
    </table>{cursor}</>;
  }
  return null;
}

export function StreamingPaperView({ markdown, stage, waitingForFirstText, cursorEnding = false }: { markdown: string; stage: StreamingStage; waitingForFirstText: boolean; cursorEnding?: boolean }) {
  const { blocks, blockLines } = parseStreamingMarkdownTracked(markdown);
  // 活跃块跟随真实的文本增长位置而不是文档末尾：写靠前章节时呼吸光标不能落在全篇最后一个块。
  const prevMarkdown = useRef<string | null>(null);
  const grownBlock = useRef(-1);
  const previous = prevMarkdown.current;
  if (previous !== null && previous !== markdown) {
    const line = growthFrontierLine(previous, markdown);
    if (line !== null) {
      const index = blockIndexAtLine(blockLines, line);
      if (index >= 0) grownBlock.current = index;
    }
  }
  prevMarkdown.current = markdown;
  let fallbackIndex = -1;
  for (let index = blocks.length - 1; index >= 0; index -= 1) {
    if (blocks[index].type !== 'blank') {
      fallbackIndex = index;
      break;
    }
  }
  const activeIndex = grownBlock.current >= 0 && grownBlock.current < blocks.length ? grownBlock.current : fallbackIndex;
  return <div className="paper-streaming-view paper-surface" data-testid="streaming-paper-view" aria-live="polite">
    {waitingForFirstText && <div className="stream-stage-capsule" data-testid="stream-stage-capsule">{streamingStageLabel(stage)}</div>}
    {blocks.map((block, index) => <React.Fragment key={block.id}><BlockView block={block} active={index === activeIndex && !waitingForFirstText} showCursor={!waitingForFirstText && index === activeIndex} cursorEnding={cursorEnding} /></React.Fragment>)}
    {waitingForFirstText && <div className="stream-skeleton" data-testid="stream-skeleton" aria-hidden="true">
      <span className="stream-shimmer-line title" />
      <span className="stream-shimmer-line wide" />
      <span className="stream-shimmer-line mid" />
      <span className="stream-shimmer-line short" />
    </div>}
  </div>;
}
