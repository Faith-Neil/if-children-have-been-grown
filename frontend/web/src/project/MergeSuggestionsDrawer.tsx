// 为什么有这个文件：抽取后处理的“合并建议”抽屉（PRD v1.8 §5.1.1、§5.2.1）。
// 它解决什么问题：把相近的条目并列给项目负责人，采纳合并或写理由后不合并；取值（数字）不同的由后台拒绝。

import React, { useEffect, useState } from 'react';
import { Button, Card, Drawer, Empty, Input, Space, Tag } from 'antd';
import { useProject } from '../app/context.tsx';
import { projectCan } from './project-team.ts';
import { request } from '../shared/api.ts';
import type { PostProcessSummary } from '../shared/types.ts';

export function MergeSuggestionsDrawer({ open, onClose, onCount }: { open: boolean; onClose: () => void; onCount?: (n: number) => void }) {
  const { workspace, token, busy, mutate } = useProject();
  const [summary, setSummary] = useState<PostProcessSummary | null>(null);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const lead = projectCan(workspace, 'prepare_sources');
  const base = `/api/v1/projects/${workspace.project.id}`;

  useEffect(() => {
    let cancelled = false;
    request<PostProcessSummary>(`${base}/parse/post-process`, token)
      .then(value => { if (!cancelled) { setSummary(value); onCount?.(value.merge_suggestions.filter(s => s.status === 'pending').length); } })
      .catch(() => { if (!cancelled) setSummary(null); });
    return () => { cancelled = true; };
  }, [base, workspace.revision, token]);

  const pending = (summary?.merge_suggestions ?? []).filter(item => item.status === 'pending');
  return (
    <Drawer title="抽取后处理 · 合并建议" open={open} onClose={onClose} width={560}>
      {summary && (
        <p className="muted" data-testid="merge-summary">
          已合并 {summary.merged_items} 条（{summary.merged_groups} 组）· 已被替代 {summary.superseded_items} 条
        </p>
      )}
      {pending.length ? pending.map(item => (
        <Card size="small" key={item.id} data-testid="merge-suggestion" title={`相似度 ${Math.round(item.similarity * 100)}%`}
          extra={<Tag>{item.requirement_ids.length} 条</Tag>}>
          {item.texts.map((text, index) => <blockquote key={index}>{text}</blockquote>)}
          {lead && (
            <>
              <Input.TextArea rows={2} aria-label="合并或不合并的理由" maxLength={2000} placeholder="理由（必填）"
                value={reasons[item.id] ?? ''} onChange={e => setReasons({ ...reasons, [item.id]: e.target.value })} />
              <Space style={{ marginTop: 8 }}>
                <Button type="primary" size="small" disabled={busy || !(reasons[item.id] ?? '').trim()} data-testid="merge-accept"
                  onClick={() => void mutate(`${base}/requirements/${item.requirement_ids[0]}/merge`, 'POST',
                    { requirement_ids: item.requirement_ids.slice(1), reason: reasons[item.id].trim() }).catch(() => undefined)}>合并</Button>
                <Button size="small" disabled={busy || !(reasons[item.id] ?? '').trim()} data-testid="merge-dismiss"
                  onClick={() => void mutate(`${base}/parse/merge-suggestions/${item.id}/dismiss`, 'POST',
                    { reason: reasons[item.id].trim() }).catch(() => undefined)}>不合并</Button>
              </Space>
            </>
          )}
        </Card>
      )) : <Empty description="没有待决定的合并建议" />}
    </Drawer>
  );
}
