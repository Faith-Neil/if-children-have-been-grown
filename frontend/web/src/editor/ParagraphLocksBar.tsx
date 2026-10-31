// 为什么有这个文件：编辑台的段落锁定入口与锁定列表（APP-M2-T163，PRD v1.8 §5.11.8）。
// 它解决什么问题：持有编辑权时把光标所在段落锁住；列出本章锁定段落（锁定人、原因），锁定人或项目负责人可解除。
// 锁住的段落在后台各写入路径被拒绝改动；本组件只负责发起与展示，不在页面上做放行判断。

import React, { useCallback, useEffect, useState } from 'react';
import { Button, List, Popover, Space, Tag, Tooltip } from 'antd';
import { LockOutlined, UnlockOutlined } from '@ant-design/icons';
import { request } from '../shared/api.ts';
import type { Chapter } from '../shared/types.ts';
import { lockAction, paragraphAtOffset, type ParagraphLock } from './paragraph-keys.ts';

export function ParagraphLocksBar(props: {
  projectId: string; chapter: Chapter; content: string; token: string | null; canEdit: boolean; busy: boolean;
  cursor: () => number | null; onChanged: () => Promise<void> | void; report: (error: unknown) => void;
}) {
  const { projectId, chapter, content, token, canEdit, busy, cursor, onChanged, report } = props;
  const base = `/api/v1/projects/${projectId}/chapters/${chapter.id}/paragraph-locks`;
  const [locks, setLocks] = useState<ParagraphLock[]>([]);
  const [working, setWorking] = useState(false);
  const [, setTick] = useState(0);

  const load = useCallback(async () => {
    try { setLocks((await request<{ locks: ParagraphLock[] }>(base, token)).locks); } catch (error) { report(error); }
  }, [base, token, report]);
  useEffect(() => { void load(); }, [load, chapter.revision]);

  const offset = cursor();
  const paragraph = offset === null ? undefined : paragraphAtOffset(content, offset, chapter.paragraphs);
  const action = lockAction({ canEdit, dirtyAgainstCommitted: content !== chapter.content, paragraph });

  async function run(task: () => Promise<unknown>) {
    setWorking(true);
    try { await task(); await load(); await onChanged(); } catch (error) { report(error); } finally { setWorking(false); }
  }

  const list = (
    <List size="small" style={{ width: 360 }} data-testid="paragraph-lock-list" locale={{ emptyText: '本节没有锁定的段落' }} dataSource={locks}
      renderItem={item => (
        <List.Item actions={item.can_unlock ? [<Button key="u" size="small" icon={<UnlockOutlined />} disabled={working || busy}
          data-testid="paragraph-unlock-btn" onClick={() => void run(() => request(`${base}/${encodeURIComponent(item.paragraph_key)}`, token, 'DELETE'))}>解除</Button>] : []}>
          <List.Item.Meta title={<span>{item.excerpt}{!item.present && <Tag color="orange" style={{ marginLeft: 6 }}>当前正文中找不到原样段落</Tag>}</span>}
            description={`锁定人 ${item.locked_by_name}${item.reason ? ` · ${item.reason}` : ''}`} />
        </List.Item>
      )} />
  );

  return (
    <Space size={4} data-testid="paragraph-locks-bar" onMouseEnter={() => setTick(t => t + 1)}>
      <Tooltip title={action.reason}>
        <Button size="small" icon={<LockOutlined />} disabled={!action.enabled || working || busy} data-testid="paragraph-lock-btn"
          onClick={() => paragraph && void run(() => request(base, token, 'POST', { paragraph_key: paragraph.key, base_revision: chapter.revision }))}>
          {action.label}
        </Button>
      </Tooltip>
      <Popover trigger="click" content={list} title="本节锁定的段落">
        <Button size="small" data-testid="paragraph-lock-count">已锁定 {locks.length}</Button>
      </Popover>
    </Space>
  );
}
