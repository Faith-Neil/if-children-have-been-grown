// 为什么有这个文件：响应矩阵“批量智能匹配证据”的结果抽屉（APP-M2-T115）。
// 它解决什么问题：多选行后一次取回候选，逐行勾选再挂接；不可引用的候选显示原因但不可选，历史标书只作参考。
import { useEffect, useState } from 'react';
import { Alert, Button, Card, Checkbox, Drawer, Empty, Space, Spin, Tag, Typography } from 'antd';
import { useProject } from '../app/context.tsx';
import type { Requirement } from '../shared/types.ts';
import { appendEvidence, matchEvidence, selectable, type MatchResult } from './matrix-core.ts';

export function MatrixMatchDrawer({ ids, onClose }: { ids: string[]; onClose: () => void }) {
  const { workspace, token, busy, mutate, report } = useProject();
  const [results, setResults] = useState<MatchResult[] | null>(null);
  const [notice, setNotice] = useState('');
  const [chosen, setChosen] = useState<Record<string, string[]>>({});

  useEffect(() => {
    if (!ids.length) return;
    setResults(null); setChosen({});
    matchEvidence(workspace.project.id, token, ids).then(data => { setResults(data.results); setNotice(data.notice); }).catch(error => { report(error); onClose(); });
  }, [ids.join(',')]);

  async function attach(row: Requirement) {
    const picks = chosen[row.id] ?? [];
    if (!picks.length) return;
    try {
      await mutate(`/api/v1/projects/${workspace.project.id}/requirements/${row.id}`, 'PATCH', { evidence_ids: appendEvidence(row.evidence_ids, picks) });
      setChosen(value => ({ ...value, [row.id]: [] }));
    } catch { /* 后台拒绝时保留勾选 */ }
  }

  return (
    <Drawer open={ids.length > 0} onClose={onClose} width={720} title={`智能匹配证据 · ${ids.length} 行`} destroyOnClose>
      {notice && <Alert type="info" showIcon className="stack-card" message={notice} />}
      <Spin spinning={!results}>
        {results?.map(result => {
          const row = workspace.requirements.find(item => item.id === result.requirement_id);
          if (!row) return null;
          return (
            <Card key={result.requirement_id} size="small" className="stack-card" data-testid="matrix-match-row"
              title={<Typography.Text ellipsis style={{ maxWidth: 520 }}>{row.text}</Typography.Text>}
              extra={<Button size="small" type="primary" disabled={busy || !(chosen[row.id] ?? []).length || !row.permissions?.response} onClick={() => void attach(row)}>挂接所选</Button>}>
              {!result.structured.length && !result.snippets.length && <Empty description="资料库没有可引用的记录，可先去补录" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
              <Checkbox.Group value={chosen[row.id] ?? []} onChange={value => setChosen(current => ({ ...current, [row.id]: value as string[] }))} style={{ width: '100%' }}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  {result.structured.map(candidate => (
                    <Checkbox key={candidate.id} value={candidate.id} disabled={!selectable(candidate)}>
                      {candidate.name} {candidate.revision ? `· v${candidate.revision}` : ''} <Tag>{Math.round(candidate.score * 100)}%</Tag>
                      {candidate.already_attached && <Tag color="green">已挂接</Tag>}
                      {!candidate.attachable && <Tag color="red">{candidate.reason}</Tag>}
                    </Checkbox>
                  ))}
                </Space>
              </Checkbox.Group>
              {result.snippets.filter(s => !s.unavailable).map(snippet => (
                <div key={snippet.source_id} className="muted">[片] {snippet.name}（知识库检索，须在资料库确认后才能作为证据）</div>
              ))}
              {result.snippets.some(s => s.unavailable) && <div className="muted">知识库暂不可用，只给出资料库规则匹配结果。</div>}
              {result.history_reference.map(item => (
                <div key={item.id ?? item.source_id} className="muted">历史标书（参考，不能挂为证据）：{item.name}</div>
              ))}
            </Card>
          );
        })}
      </Spin>
    </Drawer>
  );
}
