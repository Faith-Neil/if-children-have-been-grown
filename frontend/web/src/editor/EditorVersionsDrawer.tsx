// 为什么有这个文件：提取编辑台历史正式版本抽屉（EditorVersionsDrawer）。
// 它解决什么问题：解耦历史版本列表展示、创建时间格式化与核对并恢复为草稿动作，降低 EditorPage 行数。

import React from 'react';
import { Alert, Button, Card, Drawer, Empty } from 'antd';
import { formatTime } from '../app/context.tsx';
import type { RecoveryChoice } from './RecoveryReview.tsx';

export interface ChapterVersionItem {
  revision: number;
  content: string;
  actor_id: string;
  created_at: string;
}

export interface EditorVersionsDrawerProps {
  open: boolean;
  onClose: () => void;
  versions: ChapterVersionItem[];
  combinedBusy: boolean;
  held: boolean;
  currentRevision?: number;
  inputFingerprint?: string | null;
  onReviewRecovery: (choice: RecoveryChoice) => void;
}

export function EditorVersionsDrawer({
  open,
  onClose,
  versions,
  combinedBusy,
  held,
  currentRevision,
  inputFingerprint,
  onReviewRecovery,
}: EditorVersionsDrawerProps) {
  return (
    <Drawer title="正式版本记录" open={open} onClose={onClose} width={680}>
      {versions.length ? (
        versions.map(item => (
          <Card
            size="small"
            className="version-card"
            title={`正文 v${item.revision}`}
            extra={formatTime(item.created_at)}
            key={item.revision}
          >
            <p className="muted">提交账号：{item.actor_id}</p>
            <pre>{item.content}</pre>
            <Button
              size="small"
              disabled={combinedBusy || !held || item.revision === currentRevision}
              onClick={() =>
                onReviewRecovery({
                  title: `历史正文 v${item.revision}`,
                  content: item.content,
                  source_kind: 'history',
                  input_fingerprint: inputFingerprint ?? null,
                })
              }
            >
              核对并恢复为草稿
            </Button>
          </Card>
        ))
      ) : (
        <Empty description="暂无已提交版本" />
      )}
      <Alert
        type="info"
        message="历史版本保留不变。恢复先保存个人草稿，人工修订并提交后才产生新正文版本。"
      />
    </Drawer>
  );
}
