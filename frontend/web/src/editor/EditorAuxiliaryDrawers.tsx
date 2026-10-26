// 为什么有这个文件：提取编辑台辅助抽屉组（快照快照、写作方案、草稿恢复、来源依据核对）。
// 它解决什么问题：解耦非主视图的 4 个次级抽屉与弹层逻辑，降低 EditorPage 行数。

import React from 'react';
import { Alert, Button, Checkbox, Drawer, Space } from 'antd';
import type { Candidate, WritingInputPreview } from '../shared/types.ts';
import WritingPlanReview from './WritingPlanReview.tsx';
import WritingInputPreviewContent from './WritingInputPreview.tsx';
import RecoveryReview, { type RecoveryChoice } from './RecoveryReview.tsx';

export interface EditorAuxiliaryDrawersProps {
  chapterId: string;
  candidate: Candidate | null;
  candidateIssue: unknown;
  inputOpen: boolean;
  onCloseInput: () => void;
  planOpen: boolean;
  onClosePlan: () => void;
  recovery: RecoveryChoice | null;
  recoveryReviewed: boolean;
  onReviewRecoveryChecked: (checked: boolean) => void;
  onCancelRecovery: () => void;
  onSaveRecovery: () => Promise<void>;
  onReviewSourcesForRecovery: () => void;
  sourceReview: { preview: WritingInputPreview; target: 'editor' | 'recovery' } | null;
  onCloseSourceReview: () => void;
  sourceReviewed: boolean;
  onSourceReviewedChange: (checked: boolean) => void;
  onReloadSources: () => void;
  onConfirmSources: () => void;
  content: string;
  busy: boolean;
  combinedBusy: boolean;
  held: boolean;
  canEdit: boolean;
}

export function EditorAuxiliaryDrawers({
  chapterId,
  candidate,
  candidateIssue,
  inputOpen,
  onCloseInput,
  planOpen,
  onClosePlan,
  recovery,
  recoveryReviewed,
  onReviewRecoveryChecked,
  onCancelRecovery,
  onSaveRecovery,
  onReviewSourcesForRecovery,
  sourceReview,
  onCloseSourceReview,
  sourceReviewed,
  onSourceReviewedChange,
  onReloadSources,
  onConfirmSources,
  content,
  busy,
  combinedBusy,
  held,
  canEdit,
}: EditorAuxiliaryDrawersProps) {
  return (
    <>
      <Drawer
        title="当次写作输入 · 候选历史快照"
        open={inputOpen}
        onClose={onCloseInput}
        width={760}
      >
        {candidateIssue ? (
          <Alert
            className="page-notice"
            showIcon
            type="warning"
            message="候选已失效；下方仍保留生成时的输入供核对"
          />
        ) : null}
        <WritingInputPreviewContent snapshot={candidate?.input_snapshot} historical />
      </Drawer>

      <WritingPlanReview chapterId={chapterId} open={planOpen} onClose={onClosePlan} />

      <RecoveryReview
        choice={recovery}
        current={content}
        reviewed={recoveryReviewed}
        busy={busy}
        writable={held && !combinedBusy && canEdit}
        onReview={onReviewRecoveryChecked}
        onCancel={onCancelRecovery}
        onSave={onSaveRecovery}
        onReviewSources={onReviewSourcesForRecovery}
      />

      <Drawer
        title="核对最新来源 · 更新这次文字的写作依据"
        open={!!sourceReview}
        onClose={onCloseSourceReview}
        width={760}
        zIndex={1200}
        footer={
          <Space wrap>
            <Checkbox
              checked={sourceReviewed}
              onChange={event => onSourceReviewedChange(event.target.checked)}
            >
              我已核对当前来源，并确认待保存文字仍然适用
            </Checkbox>
            <Button
              size="small"
              disabled={combinedBusy}
              onClick={onReloadSources}
            >
              重新读取来源
            </Button>
            <Button
              type="primary"
              loading={busy}
              disabled={!sourceReviewed || combinedBusy || !held || !canEdit}
              onClick={onConfirmSources}
            >
              按已核对来源更新依据
            </Button>
          </Space>
        }
      >
        <Alert
          className="page-notice"
          showIcon
          type="warning"
          message="这一步只更新本次文字的写作依据，不会修改原文、事实、服务承诺或正式正文"
          description="先取得编辑权再确认。确认期间如果来源或正文又有变化，仍会拒绝更新；确认后也须人工修订，再保存草稿或提交。"
        />
        {sourceReview && (
          <WritingInputPreviewContent
            snapshot={sourceReview.preview.input_snapshot}
            historical={false}
          />
        )}
      </Drawer>
    </>
  );
}
