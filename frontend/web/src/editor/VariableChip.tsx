// 为什么有这个文件：正文变量节点的胶囊（APP-M2-T164）。
// 它解决什么问题：有效变量带底色显示当前取值（敏感号码为掩码），失效变量标红；悬停看字段名与原因，点“去数据源修改”跳到项目事实表或服务承诺矩阵。
import React from 'react';
import { Button, Popover, Space } from 'antd';
import { sourceLabel, variableText, type VariableNode } from './variable-nodes.ts';

const VALID: React.CSSProperties = { background: '#fff7d6', border: '1px solid #ffe08a', color: '#614700' };
const BAD: React.CSSProperties = { background: '#fff1f0', border: '1px solid #ffa39e', color: '#a8071a' };

export function VariableChip({ node, onGoToSource }: { node: VariableNode; onGoToSource?: (source: VariableNode['source']) => void }) {
  const valid = node.status === 'valid';
  const content = (
    <div style={{ maxWidth: 300, fontSize: 12 }}>
      <div><strong>{node.label}</strong>{node.kind === 'sla' ? ' · 服务承诺' : ' · 项目事实'}</div>
      {valid ? <div>当前取值：{node.display || '（空）'}{node.masked ? '（已掩码）' : ''}</div> : <div style={{ color: '#a8071a' }}>{node.message}</div>}
      <div className="muted" style={{ marginTop: 4 }}>取值只在数据源里改</div>
      {onGoToSource && <Space style={{ marginTop: 6 }}><Button size="small" onClick={() => onGoToSource(node.source)} data-testid="variable-go-source">{sourceLabel(node.source)}</Button></Space>}
    </div>
  );
  return (
    <Popover content={content} trigger={['hover', 'click']}>
      <span className="icg-variable-node" data-testid="variable-node" data-status={node.status} data-ref={node.ref}
        style={{ display: 'inline-block', padding: '0 4px', margin: '0 1px', borderRadius: 3, lineHeight: '20px', cursor: 'pointer', ...(valid ? VALID : BAD) }}>
        {variableText(node)}
      </span>
    </Popover>
  );
}
