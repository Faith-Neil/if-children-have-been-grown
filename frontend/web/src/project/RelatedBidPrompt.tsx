// 为什么有这个文件：R19 关联投标冲突的确认弹窗与项目设置里的提示条（APP-M2-T096 / PRD v1.8 §5.1.2）。
// 它解决什么问题：项目负责人只能“确认无上述关系并继续”（须填写说明）或“取消”；提示里只有对方公司名称。

import { useEffect, useState } from 'react';
import { Alert, App as AntApp, Button, Input, Tag } from 'antd';
import { request } from '../shared/api.ts';
import { matchLabel, reasonProblem, relatedBidPath, type RelatedBidDetails, type RelatedBidStatus } from './related-bid-core.ts';

type ModalApi = ReturnType<typeof AntApp.useApp>['modal'];

function Body({ details, onReason }: { details: RelatedBidDetails; onReason: (value: string) => void }) {
  const [reason, setReason] = useState('');
  return (
    <div data-testid="related-bid-prompt">
      <p>{details.message}</p>
      <p>{details.companies.map(name => <Tag key={name} color="orange">{name}</Tag>)}<span className="muted">{matchLabel(details.match)}</span></p>
      <Input.TextArea rows={3} maxLength={2000} value={reason} aria-label="关联关系说明" data-testid="related-bid-reason"
        placeholder="写明本公司与上述公司无控股、管理关系，单位负责人也不是同一人"
        onChange={event => { setReason(event.target.value); onReason(event.target.value); }} />
    </div>
  );
}

/** 弹出确认；返回填写的说明，取消时返回 null。 */
export function askRelatedBidReason(modal: ModalApi, details: RelatedBidDetails): Promise<string | null> {
  return new Promise(resolve => {
    let reason = '';
    modal.confirm({
      title: '关联投标冲突', width: 560, content: <Body details={details} onReason={value => { reason = value; }} />,
      okText: '确认无上述关系并继续', cancelText: '取消',
      onOk: async () => {
        const problem = reasonProblem(reason);
        if (problem) throw new Error(problem);
        resolve(reason.trim());
      },
      onCancel: () => resolve(null),
    });
  });
}

/** 项目设置：有未确认的冲突时显示，负责人可填写说明确认。 */
export function RelatedBidBanner({ projectId, token, revision, canConfirm, modal, onConfirmed, report }: {
  projectId: string; token: string | null; revision: number; canConfirm: boolean; modal: ModalApi;
  onConfirmed: () => Promise<void> | void; report: (error: unknown) => void;
}) {
  const [status, setStatus] = useState<RelatedBidStatus | null>(null);
  useEffect(() => {
    let alive = true;
    request<RelatedBidStatus>(relatedBidPath(projectId), token).then(value => { if (alive) setStatus(value); }).catch(() => undefined);
    return () => { alive = false; };
  }, [projectId, token, revision]);
  if (!status?.companies.length) return null;
  if (!status.needs_ack && status.acknowledged) {
    return <Alert className="page-notice" type="info" showIcon data-testid="related-bid-acknowledged"
      message={`关联投标：已由${status.acknowledged.by_name}确认与 ${status.acknowledged.company_names.join('、')} 无关联关系`}
      description={status.acknowledged.reason} />;
  }
  async function confirm() {
    if (!status) return;
    const reason = await askRelatedBidReason(modal, status);
    if (!reason) return;
    try {
      const next = await request<RelatedBidStatus>(relatedBidPath(projectId, '/ack'), token, 'POST', { reason }, revision);
      setStatus(next);
      await onConfirmed();
    } catch (error) { report(error); }
  }
  return <Alert className="page-notice" type="warning" showIcon data-testid="related-bid-banner"
    message={`关联投标冲突：${status.companies.join('、')}（${matchLabel(status.match)}）`} description={status.message}
    action={canConfirm ? <Button size="small" onClick={() => void confirm()} data-testid="related-bid-open">填写说明</Button> : undefined} />;
}
