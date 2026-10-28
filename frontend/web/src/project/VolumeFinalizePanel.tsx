// 为什么有这个文件：导出页的「分册定稿」区：指定交叉复核人、复核确认、定稿与解锁（PRD v1.8 §2.3、§4.2、§5.8.5）。
// 它解决什么问题：原先后台有定稿接口但页面没有入口；现在每册一行，按钮按角色和前提出现，后台仍会再次核对。

import { useState } from 'react';
import { Button, Card, Form, Input, Modal, Radio, Select, Space, Tag, Tooltip } from 'antd';
import { formatTime, useProject, volumeName } from '../app/context.tsx';
import type { Volume, VolumeStatus } from '../shared/types.ts';
import { queuePaths, reviewTag, reviewerCandidates, volumeActions } from './main-path-core.ts';

type Dialog = { kind: 'assign' | 'confirm' | 'unlock'; volume: Volume } | null;

export function VolumeFinalizePanel({ volumes, checkId }: { volumes: VolumeStatus[]; checkId?: string }) {
  const { workspace, user, busy, mutate, navigate } = useProject();
  const [dialog, setDialog] = useState<Dialog>(null);
  const [form] = Form.useForm();
  const projectId = workspace.project.id;

  function open(kind: NonNullable<Dialog>['kind'], volume: Volume) {
    form.resetFields();
    if (kind === 'confirm') form.setFieldsValue({ decision: 'approved', note: '' });
    setDialog({ kind, volume });
  }

  async function submit() {
    if (!dialog) return;
    const values = await form.validateFields();
    const path = dialog.kind === 'assign' ? queuePaths.assignReviewer(projectId, dialog.volume)
      : dialog.kind === 'confirm' ? queuePaths.confirmReview(projectId, dialog.volume)
        : queuePaths.unlock(projectId, dialog.volume);
    try {
      await mutate(path, 'POST', values);
      setDialog(null);
    } catch {
      /* 错误已提示，保留填写 */
    }
  }

  async function finalize(volume: Volume) {
    try {
      await mutate(queuePaths.finalize(projectId, volume), 'POST', checkId ? { check_id: checkId } : {});
    } catch {
      /* 后台给出未满足的前提 */
    }
  }

  return (
    <Card title="分册定稿" className="stack-card" data-testid="volume-finalize-panel">
      {(['technical', 'business'] as Volume[]).map(volume => {
        const status = volumes.find(item => item.volume_id === volume);
        const actions = volumeActions(status, workspace, user.id, volume);
        const review = status?.cross_review;
        const tag = reviewTag(review);
        return (
          <div key={volume} className="volume-finalize-row" data-testid={`volume-finalize-${volume}`}>
            <div className="card-heading">
              <Space wrap>
                <b>{volumeName(volume)}</b>
                {status?.is_finalized ? <Tag color="success">已定稿</Tag> : <Tag>编制中</Tag>}
                <Tag color={tag.color}>{tag.label}</Tag>
                {review?.reviewer_name && <span className="muted">复核人：{review.reviewer_name}</span>}
              </Space>
              <Space>
                {actions.canAssign && <Button size="small" disabled={busy} onClick={() => open('assign', volume)}>{review?.status === 'none' || !review ? '指定复核人' : '重新指定'}</Button>}
                {actions.canConfirm && <Button size="small" type="primary" ghost disabled={busy} onClick={() => open('confirm', volume)}>确认复核</Button>}
                {!status?.is_finalized && isManagerVisible(actions) && (
                  <Tooltip title={actions.finalizeBlockers.join('；')}>
                    <Button size="small" type="primary" disabled={busy || !actions.canFinalize} onClick={() => void finalize(volume)}>定稿</Button>
                  </Tooltip>
                )}
                {actions.canUnlock && <Button size="small" danger disabled={busy} onClick={() => open('unlock', volume)}>解锁</Button>}
              </Space>
            </div>
            {status?.is_finalized ? (
              <p className="muted">{formatTime(status.finalized_at || '')} 定稿。解锁后检查和导出文件随之过期，须重新复核再定稿。</p>
            ) : actions.finalizeBlockers.length > 0 ? (
              <p className="muted">
                {actions.finalizeBlockers.join('；')}
                {(status?.pending_human_issues ?? 0) > 0 && <a onClick={() => navigate('manual')}> 去处理</a>}
              </p>
            ) : null}
            {review?.status === 'returned' && review.decision_note && <blockquote>退回意见：{review.decision_note}</blockquote>}
          </div>
        );
      })}
      <Modal
        open={!!dialog}
        title={dialog ? `${volumeName(dialog.volume)} · ${dialog.kind === 'assign' ? '指定交叉复核人' : dialog.kind === 'confirm' ? '交叉复核' : '解锁分册'}` : ''}
        okText={dialog?.kind === 'unlock' ? '确认解锁' : '确定'}
        cancelText="取消"
        onCancel={() => setDialog(null)}
        onOk={submit}
        confirmLoading={busy}
      >
        <Form form={form} layout="vertical">
          {dialog?.kind === 'assign' && (
            <Form.Item name="reviewer_id" label="复核人（不能是本分册编写人）" rules={[{ required: true, message: '请选择复核人' }]}>
              <Select options={reviewerCandidates(workspace.team, dialog.volume)} />
            </Form.Item>
          )}
          {dialog?.kind === 'confirm' && (
            <>
              <Form.Item name="decision" label="复核结论" rules={[{ required: true }]}>
                <Radio.Group options={[{ value: 'approved', label: '复核通过' }, { value: 'returned', label: '退回修改' }]} />
              </Form.Item>
              <Form.Item noStyle shouldUpdate>
                {() => (
                  <Form.Item name="note" label="复核意见" rules={[{ required: form.getFieldValue('decision') === 'returned', whitespace: true, message: '退回须写明原因' }]}>
                    <Input.TextArea rows={3} maxLength={500} />
                  </Form.Item>
                )}
              </Form.Item>
            </>
          )}
          {dialog?.kind === 'unlock' && (
            <Form.Item name="reason" label="解锁原因" rules={[{ required: true, whitespace: true, message: '解锁须写明原因' }]}>
              <Input.TextArea rows={3} maxLength={500} />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </Card>
  );
}

function isManagerVisible(actions: ReturnType<typeof volumeActions>): boolean {
  return actions.canAssign || actions.canFinalize;
}
