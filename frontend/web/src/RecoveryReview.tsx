// 为什么有这个文件：恢复旧文字前，让编写人并排核对当前内容和待恢复内容。
// 它解决什么问题：恢复必须人工确认，且只写个人草稿，保留正式版本历史。
import { Alert, Checkbox, Modal } from 'antd';
import type { RecoverySource } from './editing-source';

export type RecoveryChoice = { title: string; content: string } & RecoverySource;

export default function RecoveryReview({ choice, current, reviewed, busy, writable, onReview, onCancel, onSave, onReviewSources }: {
  choice: RecoveryChoice | null; current: string; reviewed: boolean; busy: boolean; writable: boolean;
  onReview: (value: boolean) => void; onCancel: () => void; onSave: () => Promise<void>;
  onReviewSources: () => void;
}) {
  return <Modal title={`恢复核对 · ${choice?.title ?? ''}`} width={960} open={!!choice}
    onCancel={onCancel} onOk={onSave} cancelText="继续保留当前内容" okText="保存为新的个人草稿"
    confirmLoading={busy} okButtonProps={{ disabled: !reviewed || !writable }}>
    <Alert type="warning" showIcon message="恢复会替换当前个人草稿，正式正文和历史版本暂不改变"
      description="保存成功后再修订；提交本节才形成新的正文版本。后台会重新核对编辑权、正文版本、来源版本和草稿顺序。" />
    <Alert className="page-notice" showIcon type={choice?.reviewed_input_fingerprint ? 'success' : 'info'}
      message={choice?.reviewed_input_fingerprint ? '已人工重新核对当前来源，这次恢复使用核对时的来源依据' : choice?.source_kind === 'draft' ? '旧草稿保留原来的来源依据，恢复不会自动升级为最新资料' : '历史正文需按当前项目来源重新核对；恢复先形成个人草稿'}
      description={<a onClick={onReviewSources}>核对最新来源</a>} />
    <div className="diff-columns"><div><h4>当前编辑内容</h4><pre className="diff-before">{current || '（空正文）'}</pre></div>
      <div><h4>准备恢复的内容</h4><pre className="diff-after">{choice?.content || '（空正文）'}</pre></div></div>
    <Checkbox checked={reviewed} onChange={event => onReview(event.target.checked)}>
      我已核对文字差异和对应来源，确认用这些文字替换当前个人草稿
    </Checkbox>
  </Modal>;
}
