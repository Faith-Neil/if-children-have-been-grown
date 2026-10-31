// 为什么有这个文件：补遗/澄清差异视图（PRD v1.8 §5.1.4、§5.2.4）。
// 它解决什么问题：逐条对照补遗改了哪条原条款（逐字标出）、新增了什么、哪些没定位到原条款、改了哪些事实取值。

import React, { useEffect, useState } from 'react';
import { Alert, Card, Drawer, Empty, Space, Tag } from 'antd';
import { request } from '../shared/api.ts';
import { useProject } from '../app/context.tsx';
import type { AddendumDiff } from '../shared/types.ts';

const KIND: Record<string, { label: string; color: string }> = {
  modified: { label: '修改原条款', color: 'orange' }, added: { label: '新增', color: 'green' },
  unlocated: { label: '未定位到原条款', color: 'red' }, same: { label: '与原条款一致', color: 'default' },
};

export function AddendumDiffDrawer({ fileId, onClose }: { fileId: string; onClose: () => void }) {
  const { workspace, token, report } = useProject();
  const [diff, setDiff] = useState<AddendumDiff | null>(null);
  useEffect(() => {
    if (!fileId) { setDiff(null); return; }
    let cancelled = false;
    request<AddendumDiff>(`/api/v1/projects/${workspace.project.id}/files/${encodeURIComponent(fileId)}/addendum-diff`, token)
      .then(value => { if (!cancelled) setDiff(value); }).catch(error => { if (!cancelled) report(error); });
    return () => { cancelled = true; };
  }, [fileId, workspace.project.id, workspace.revision, token]);

  return (
    <Drawer title={`补遗差异 · ${diff?.file.filename ?? ''}`} width={720} open={!!fileId} onClose={onClose}>
      {diff && (
        <>
          <Space wrap data-testid="diff-summary">
            {Object.entries(diff.summary).map(([key, count]) => <Tag key={key}>{KIND[key]?.label ?? key} {count}</Tag>)}
          </Space>
          {diff.items.length ? diff.items.map(item => (
            <Card size="small" key={item.requirement.requirement_id ?? item.requirement.value} data-testid="diff-item" data-kind={item.kind}
              title={<Tag color={KIND[item.kind]?.color}>{KIND[item.kind]?.label ?? item.kind}</Tag>}>
              <p className="requirement-text">{item.requirement.value}</p>
              {item.target && (
                <p data-testid="diff-text">
                  {item.diff.length ? item.diff.map((part, index) => (
                    <span key={index} style={part.op === 'delete' ? { background: '#ffccc7', textDecoration: 'line-through' }
                      : part.op === 'insert' ? { background: '#d9f7be' } : undefined}>{part.text}</span>
                  )) : item.target.value}
                </p>
              )}
              {item.kind === 'unlocated' && <Alert type="warning" showIcon message="请在“冲突待选定”中指定被替代的原条款" />}
            </Card>
          )) : <Empty description="本文件没有可对照的条目" />}
          {diff.facts.length > 0 && (
            <Card size="small" title="事实取值变化">
              {diff.facts.map(change => (
                <p key={change.key}>{change.key}：{change.old.map(v => v.value).join('、')} → <b>{change.new.value}</b></p>
              ))}
            </Card>
          )}
          {diff.replaced_items.length > 0 && <Alert type="info" showIcon message={`旧版中 ${diff.replaced_items.length} 条已标“所在文件已被替代”`} />}
        </>
      )}
    </Drawer>
  );
}
