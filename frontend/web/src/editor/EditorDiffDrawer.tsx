// 为什么有这个文件：提取版本历史与正文 Diff 比对侧边抽屉（EditorDiffDrawer）。
// 它解决什么问题：解耦历史正式版本列表展示、与当前草稿/正文的双栏 Diff 对比及恢复流程，降低 EditorPage 行数。

import React, { useState } from 'react';
import { Alert, Button, Card, Drawer, Empty, Radio, Space } from 'antd';
import { formatTime } from '../app/context.tsx';
import type { RecoveryChoice } from './RecoveryReview.tsx';

export interface ChapterVersionItem {
  revision: number;
  content: string;
  actor_id: string;
  created_at: string;
}

export interface EditorDiffDrawerProps {
  open: boolean;
  onClose: () => void;
  versions: ChapterVersionItem[];
  currentContent: string;
  currentRevision?: number;
  combinedBusy: boolean;
  held: boolean;
  inputFingerprint?: string | null;
  onReviewRecovery: (choice: RecoveryChoice) => void;
}

export function EditorDiffDrawer({
  open,
  onClose,
  versions,
  currentContent,
  currentRevision,
  combinedBusy,
  held,
  inputFingerprint,
  onReviewRecovery,
}: EditorDiffDrawerProps) {
  const [selectedRevision, setSelectedRevision] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<'list' | 'diff'>('list');

  const activeVersion = versions.find(v => v.revision === selectedRevision) ?? versions[0] ?? null;

  return (
    <Drawer
      title="正式版本历史与差异比对"
      open={open}
      onClose={onClose}
      width={viewMode === 'diff' ? 840 : 680}
      extra={
        versions.length > 0 && (
          <Radio.Group
            size="small"
            value={viewMode}
            onChange={e => setViewMode(e.target.value)}
            optionType="button"
          >
            <Radio.Button value="list">版本列表</Radio.Button>
            <Radio.Button value="diff">差异比对</Radio.Button>
          </Radio.Group>
        )
      }
    >
      {viewMode === 'diff' && activeVersion ? (
        <div className="version-diff-container" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Space>
              <span style={{ fontSize: 13, fontWeight: 500 }}>比对版本：</span>
              <Radio.Group
                size="small"
                value={activeVersion.revision}
                onChange={e => setSelectedRevision(e.target.value)}
              >
                {versions.map(v => (
                  <Radio.Button key={v.revision} value={v.revision}>
                    v{v.revision}
                  </Radio.Button>
                ))}
              </Radio.Group>
            </Space>
            <Button
              size="small"
              type="primary"
              disabled={combinedBusy || !held || activeVersion.revision === currentRevision}
              onClick={() =>
                onReviewRecovery({
                  title: `历史正文 v${activeVersion.revision}`,
                  content: activeVersion.content,
                  source_kind: 'history',
                  input_fingerprint: inputFingerprint ?? null,
                })
              }
            >
              核对并恢复为草稿
            </Button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div style={{ border: '1px solid #e5e6eb', borderRadius: 4, padding: 12, background: '#f7f8fa' }}>
              <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 13 }}>
                历史正文 (v{activeVersion.revision}) · {formatTime(activeVersion.created_at)}
              </div>
              <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0, maxHeight: 480, overflowY: 'auto' }}>
                {activeVersion.content || '（空正文）'}
              </pre>
            </div>
            <div style={{ border: '1px solid #e5e6eb', borderRadius: 4, padding: 12, background: '#fff' }}>
              <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 13 }}>
                当前编辑区内容 {currentRevision ? `(v${currentRevision})` : ''}
              </div>
              <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0, maxHeight: 480, overflowY: 'auto' }}>
                {currentContent || '（空正文）'}
              </pre>
            </div>
          </div>
        </div>
      ) : versions.length ? (
        versions.map(item => (
          <Card
            size="small"
            className="version-card"
            title={`正文 v${item.revision}`}
            extra={formatTime(item.created_at)}
            key={item.revision}
            style={{ marginBottom: 12 }}
          >
            <p className="muted" style={{ margin: '0 0 8px', fontSize: 12 }}>
              提交账号：{item.actor_id}
            </p>
            <pre style={{ maxHeight: 180, overflowY: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
              {item.content}
            </pre>
            <Space style={{ marginTop: 8 }}>
              <Button
                size="small"
                onClick={() => {
                  setSelectedRevision(item.revision);
                  setViewMode('diff');
                }}
              >
                与当前内容比对
              </Button>
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
            </Space>
          </Card>
        ))
      ) : (
        <Empty description="暂无已提交版本" />
      )}
      <Alert
        style={{ marginTop: 12 }}
        type="info"
        message="历史版本保留不变。恢复先保存个人草稿，人工修订并提交后才产生新正文版本。"
      />
    </Drawer>
  );
}
