// 为什么有这个文件：提取抽取冲突待选定卡片列表（ConflictCards）。
// 它解决什么问题：解耦招标文件解析冲突处理与主页签展示，提供单选项与选定理由提交。

import React, { useState } from 'react';
import { Button, Card, Empty, Input, Radio, Tag } from 'antd';
import { useProject } from '../app/context.tsx';
import { projectCan } from './project-team.ts';
import { SourceLink } from './SourceLink.tsx';
import type { Source } from '../shared/types.ts';

const ignoreFailure = () => undefined;

export interface ConflictCardsProps {
  onLocate: (source: Source) => void;
}

export function ConflictCards({ onLocate }: ConflictCardsProps) {
  const { workspace, busy, mutate } = useProject();
  const [choices, setChoices] = useState<Record<string, string>>({});
  const [reasons, setReasons] = useState<Record<string, string>>({});

  return workspace.conflicts.length ? (
    <>
      {workspace.conflicts.map(item => (
        <Card
          className="conflict-card"
          key={item.id}
          title={item.key}
          extra={
            <Tag color={item.status === 'resolved' ? 'green' : 'red'}>
              {item.status === 'resolved' ? '已处理' : '待处理'}
            </Tag>
          }
        >
          <Radio.Group
            value={choices[item.id] ?? item.selected_fact_id}
            onChange={e => setChoices({ ...choices, [item.id]: e.target.value })}
            disabled={busy || !projectCan(workspace, 'prepare_sources')}
            style={{ width: '100%' }}
          >
            {item.fact_ids.map(id => {
              const fact = workspace.facts.find(value => value.id === id);
              return fact ? (
                <Radio className="conflict-option" value={id} key={id}>
                  <b>{fact.value}</b>
                  <p>
                    <SourceLink source={fact.source} onClick={onLocate} />
                  </p>
                  <blockquote>{fact.source?.quote || '服务承诺引用，无独立招标原文'}</blockquote>
                </Radio>
              ) : null;
            })}
          </Radio.Group>
          <Input.TextArea
            rows={3}
            placeholder="选定理由（必填），例如以正式招标文件为准"
            value={reasons[item.id] ?? item.reason}
            onChange={e => setReasons({ ...reasons, [item.id]: e.target.value })}
            disabled={!projectCan(workspace, 'prepare_sources')}
          />
          <Button
            style={{ marginTop: 12 }}
            type="primary"
            disabled={
              busy ||
              !projectCan(workspace, 'prepare_sources') ||
              !(choices[item.id] ?? item.selected_fact_id) ||
              !(reasons[item.id] ?? item.reason)?.trim()
            }
            onClick={() =>
              mutate(`/api/v1/projects/${workspace.project.id}/conflicts/${item.id}`, 'PATCH', {
                selected_fact_id: choices[item.id] ?? item.selected_fact_id,
                reason: reasons[item.id] ?? item.reason,
              }).catch(ignoreFailure)
            }
          >
            选定正确取值
          </Button>
        </Card>
      ))}
    </>
  ) : (
    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前没有发现取值冲突；仍需人工对照原文" />
  );
}
