// 为什么有这个文件：版本历史、版本对比与回退的侧边抽屉（APP-M2-T174、T175，PRD v1.8 §5.11.9）。
// 它解决什么问题：
// 1. 版本列表显示每个版本的修改方式（手改、对话助手替换/插入、章节循环修正、系统生成、版本回退等）与提交人；
// 2. 任选一个历史版本，按段落键与当前正式版本逐段对比：未改、改动（逐字标增删）、新增、删除；
// 3. 持锁时可“回退到此版本”（后台生成新版本，历史保留，权限/编辑锁/来源/锁定段落/系统章节在后台重核），
//    或沿用原流程“核对并恢复为草稿”，人工修订后再提交。

import React, { useMemo, useState } from 'react';
import { Alert, Button, Card, Drawer, Empty, Popconfirm, Radio, Space, Tag, Tooltip } from 'antd';
import { formatTime } from '../app/context.tsx';
import type { RecoveryChoice } from './RecoveryReview.tsx';
import { changeSummary, compareVersions, rollbackBlocker, versionModeLabel, type ParagraphChange, type VersionRecord } from './version-compare.ts';

export type ChapterVersionItem = VersionRecord;

export interface EditorDiffDrawerProps {
  open: boolean;
  onClose: () => void;
  /** 新版本在前 */
  versions: ChapterVersionItem[];
  currentContent: string;
  currentRevision?: number;
  combinedBusy: boolean;
  held: boolean;
  /** 编辑区有未提交的修改 */
  dirty?: boolean;
  /** 系统生成章节 */
  system?: boolean;
  inputFingerprint?: string | null;
  onReviewRecovery: (choice: RecoveryChoice) => void;
  onRollback?: (revision: number) => void;
}

function ChangeRow({ change }: { change: ParagraphChange }) {
  const box: React.CSSProperties = { padding: '6px 10px', borderRadius: 4, margin: '6px 0', whiteSpace: 'pre-wrap', wordBreak: 'break-word' };
  if (change.kind === 'same') return <div style={{ ...box, color: '#86909c' }} data-change="same">{change.text}</div>;
  if (change.kind === 'added') return <div style={{ ...box, background: '#e8ffea' }} data-change="added"><Tag color="green">新增</Tag><ins>{change.text}</ins></div>;
  if (change.kind === 'removed') return <div style={{ ...box, background: '#ffece8' }} data-change="removed"><Tag color="red">删除</Tag><del>{change.text}</del></div>;
  return (
    <div style={{ ...box, background: '#fff7e8' }} data-change="changed">
      <Tag color="orange">改动</Tag>
      {change.parts.map((part, i) => part.kind === 'same' ? <span key={i}>{part.text}</span>
        : part.kind === 'added' ? <ins key={i} style={{ background: '#aff0b5' }}>{part.text}</ins>
          : <del key={i} style={{ background: '#fdcdc5' }}>{part.text}</del>)}
    </div>
  );
}

export function EditorDiffDrawer({
  open, onClose, versions, currentContent, currentRevision, combinedBusy, held, dirty = false, system = false,
  inputFingerprint, onReviewRecovery, onRollback,
}: EditorDiffDrawerProps) {
  const [selectedRevision, setSelectedRevision] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<'list' | 'diff'>('list');
  const latest = versions[0] ?? null;
  const older = versions.find(v => v.revision === selectedRevision) ?? versions[1] ?? latest;
  const changes = useMemo(() => (older && latest ? compareVersions(older, latest) : []), [older, latest]);

  const recover = (item: ChapterVersionItem) => onReviewRecovery({
    title: `历史正文 v${item.revision}`, content: item.content, source_kind: 'history', input_fingerprint: inputFingerprint ?? null,
  });
  const rollbackButton = (item: ChapterVersionItem) => {
    const blocker = rollbackBlocker({ held, isCurrent: item.revision === currentRevision, dirty, system });
    return (
      <Tooltip title={blocker ?? undefined}>
        <Popconfirm title={`回退到 v${item.revision}？`} description="会生成一个新版本，历史版本全部保留；锁定段落不能被回退覆盖。"
          okText="确认回退" cancelText="取消" disabled={!!blocker || combinedBusy} onConfirm={() => onRollback?.(item.revision)}>
          <Button size="small" danger disabled={!!blocker || combinedBusy || !onRollback} data-testid={`rollback-btn-${item.revision}`}>回退到此版本</Button>
        </Popconfirm>
      </Tooltip>
    );
  };

  return (
    <Drawer title="版本历史与对比" open={open} onClose={onClose} width={viewMode === 'diff' ? 840 : 680}
      extra={versions.length > 1 && (
        <Radio.Group size="small" value={viewMode} onChange={e => setViewMode(e.target.value)} optionType="button">
          <Radio.Button value="list">版本列表</Radio.Button>
          <Radio.Button value="diff" data-testid="version-diff-tab">逐段对比</Radio.Button>
        </Radio.Group>
      )}>
      {viewMode === 'diff' && older && latest ? (
        <div className="version-diff-container" data-testid="version-diff">
          <Space wrap style={{ marginBottom: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 500 }}>历史版本：</span>
            <Radio.Group size="small" value={older.revision} onChange={e => setSelectedRevision(e.target.value)}>
              {versions.slice(1).map(v => <Radio.Button key={v.revision} value={v.revision}>v{v.revision}</Radio.Button>)}
            </Radio.Group>
            <span className="muted">对比当前正式版本 v{latest.revision}</span>
          </Space>
          <Alert type="info" showIcon style={{ marginBottom: 8 }} data-testid="version-diff-summary"
            message={`v${older.revision} → v${latest.revision}：${changeSummary(changes)}`}
            description={currentContent !== latest.content ? '编辑区另有未提交的修改，不在本对比中。' : undefined} />
          <div style={{ maxHeight: 520, overflowY: 'auto' }}>{changes.map(change => <ChangeRow key={`${change.kind}-${change.key}`} change={change} />)}</div>
          <Space style={{ marginTop: 8 }}>
            {rollbackButton(older)}
            <Button size="small" disabled={combinedBusy || !held || older.revision === currentRevision} onClick={() => recover(older)}>核对并恢复为草稿</Button>
          </Space>
        </div>
      ) : versions.length ? (
        versions.map(item => (
          <Card size="small" className="version-card" key={item.revision} style={{ marginBottom: 12 }} data-testid="version-card"
            title={<Space>{`正文 v${item.revision}`}<Tag data-testid="version-mode">{versionModeLabel(item)}</Tag>{item.revision === currentRevision && <Tag color="blue">当前</Tag>}</Space>}
            extra={formatTime(item.created_at)}>
            <p className="muted" style={{ margin: '0 0 8px', fontSize: 12 }}>提交账号：{item.actor_id}</p>
            <pre style={{ maxHeight: 180, overflowY: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{item.content}</pre>
            <Space style={{ marginTop: 8 }} wrap>
              <Button size="small" disabled={item.revision === latest?.revision} onClick={() => { setSelectedRevision(item.revision); setViewMode('diff'); }}>与当前版本逐段对比</Button>
              {rollbackButton(item)}
              <Button size="small" disabled={combinedBusy || !held || item.revision === currentRevision} onClick={() => recover(item)}>核对并恢复为草稿</Button>
            </Space>
          </Card>
        ))
      ) : (
        <Empty description="暂无已提交版本" />
      )}
      <Alert style={{ marginTop: 12 }} type="info"
        message="历史版本保留不变。“回退到此版本”直接生成新版本；“恢复为草稿”先放进个人草稿，人工修订并提交后才产生新版本。" />
    </Drawer>
  );
}
