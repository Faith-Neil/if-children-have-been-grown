// 为什么有这个文件：响应矩阵“批量智能匹配证据”的结果抽屉（APP-M2-T115）。
// 它解决什么问题：多选行后一次取回候选，逐行勾选再挂接；不可引用的候选显示原因但不可选，历史标书只作参考。
import { useEffect, useState } from 'react';
import { Alert, Button, Card, Checkbox, Drawer, Space, Spin, Tag, Typography } from 'antd';
import { useProject } from '../app/context.tsx';
import type { Requirement } from '../shared/types.ts';
import {
  appendEvidence, candidateMeta, candidateSelectable, fetchEvidenceCandidates, groupCandidates, kbStatusText, type EvidenceCandidates,
} from './matrix-core.ts';

export function MatrixMatchDrawer({ ids, onClose }: { ids: string[]; onClose: () => void }) {
  const { workspace, token, busy, mutate, report } = useProject();
  const [results, setResults] = useState<EvidenceCandidates[] | null>(null);
  const [chosen, setChosen] = useState<Record<string, string[]>>({});

  useEffect(() => {
    if (!ids.length) return;
    setResults(null); setChosen({});
    Promise.all(ids.map(id => fetchEvidenceCandidates(workspace.project.id, token, id)))
      .then(setResults).catch(error => { report(error); onClose(); });
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
      {results?.[0] && <Alert type="info" showIcon className="stack-card" message={results[0].notice} />}
      <Spin spinning={!results}>
        {results?.map(result => {
          const row = workspace.requirements.find(item => item.id === result.requirement_id);
          if (!row) return null;
          const kbText = kbStatusText(result.kb_status);
          return (
            <Card key={result.requirement_id} size="small" className="stack-card" data-testid="matrix-match-row"
              title={<Typography.Text ellipsis style={{ maxWidth: 520 }}>{row.text}</Typography.Text>}
              extra={<Button size="small" type="primary" disabled={busy || !(chosen[row.id] ?? []).length || !row.permissions?.response || !result.can_attach} onClick={() => void attach(row)}>挂接所选</Button>}>
              {kbText && <div className="muted" data-testid="matrix-kb-status">{kbText}</div>}
              <Checkbox.Group value={chosen[row.id] ?? []} onChange={value => setChosen(current => ({ ...current, [row.id]: value as string[] }))} style={{ width: '100%' }}>
                <Space direction="vertical" style={{ width: '100%' }} size={12}>
                  {groupCandidates(result.candidates).map(group => (
                    <div key={group.route} data-testid={`matrix-group-${group.route}`}>
                      <b>{group.title}</b> <Tag>{group.items.length}</Tag>
                      {!group.items.length && <div className="muted">这一路没有候选</div>}
                      <Space direction="vertical" style={{ width: '100%' }} size={4}>
                        {group.items.map((candidate, index) => (
                          <div key={`${candidate.id ?? 'x'}-${index}`} data-testid="matrix-candidate">
                            {group.route === 'structured' ? (
                              <Checkbox value={candidate.id ?? ''} disabled={!candidateSelectable(candidate, result.can_attach)}>
                                {candidate.name} <span className="muted">{candidateMeta(candidate)}</span>
                                {typeof candidate.score === 'number' && <Tag>{Math.round(candidate.score * 100)}%</Tag>}
                                {candidate.already_attached && <Tag color="green">已挂接</Tag>}
                                {candidate.blocked_reason && <Tag color="red">{candidate.blocked_reason}</Tag>}
                              </Checkbox>
                            ) : (
                              <span className="muted">
                                {candidate.name} · {candidateMeta(candidate)}
                                {candidate.blocked_reason && <Tag>{candidate.blocked_reason}</Tag>}
                              </span>
                            )}
                            {candidate.cite_reason && <div className="muted">推荐理由：{candidate.cite_reason}</div>}
                            {group.route !== 'structured' && candidate.content_preview && (
                              <Typography.Paragraph className="muted" ellipsis={{ rows: 2 }} style={{ marginBottom: 0 }}>{candidate.content_preview}</Typography.Paragraph>
                            )}
                          </div>
                        ))}
                      </Space>
                    </div>
                  ))}
                </Space>
              </Checkbox.Group>
            </Card>
          );
        })}
      </Spin>
    </Drawer>
  );
}
