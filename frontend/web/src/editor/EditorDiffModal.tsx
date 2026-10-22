// 为什么有这个文件：提取编辑台差异对比确认弹窗（EditorDiffModal）。
// 它解决什么问题：解耦当前已提交正文与 AI 建议候选正文的双栏对比视图及采纳动作，降低 EditorPage 行数。

import React from 'react';
import { Button, Card, Modal } from 'antd';
import type { Candidate } from '../shared/types.ts';

export interface EditorDiffModalProps {
  diff: { current: string; candidate: Candidate } | null;
  onClose: () => void;
  onApply: (candidate: Candidate) => void;
  combinedBusy: boolean;
  held: boolean;
}

export function EditorDiffModal({
  diff,
  onClose,
  onApply,
  combinedBusy,
  held,
}: EditorDiffModalProps) {
  return (
    <Modal
      title="编写确认 · 差异对比"
      cancelText="关闭"
      width={960}
      open={!!diff}
      onCancel={onClose}
      footer={null}
    >
      {diff && (
        <div className="diff-modal">
          <p className="muted">
            比较已提交正文与本次建议内容。建议采纳后，仍需在编辑台保存并提交正式版本。
          </p>
          <div className="diff-columns">
            <Card title="当前已提交正文">
              <pre>{diff.current}</pre>
            </Card>
            <Card
              title={`建议内容（基于 v${diff.candidate.base_revision}）`}
              extra={
                <Button
                  type="primary"
                  size="small"
                  disabled={combinedBusy || !held}
                  onClick={() => onApply(diff.candidate)}
                >
                  采纳并写入编辑框
                </Button>
              }
            >
              <pre>{diff.candidate.content}</pre>
            </Card>
          </div>
        </div>
      )}
    </Modal>
  );
}
