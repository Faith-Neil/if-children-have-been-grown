// 为什么有这个文件：项目页签「人工处理队列」（PRD v1.8 §5.7.7），替换原 PendingPage 占位。
// 它解决什么问题：把各章节自动修不了的问题按章节集中，逐条处理或驳回，处理完可对本节重新检查；按钮是否出现以后台返回的权限为准。

import { useCallback, useEffect, useState } from 'react';
import { Alert, Button, Card, Checkbox, Empty, Form, Input, Modal, Radio, Segmented, Space, Spin, Tabs, Tag, Tooltip } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useProject, volumeName } from '../app/context.tsx';
import { editorChapterPath } from '../app/app-route.ts';
import type { HumanIssue, HumanQueue, HumanQueueChapter, Volume } from '../shared/types.ts';
import {
  RESOLVE_METHODS, daysUntil, defaultResolveMethod, fetchHumanQueue, loopLine, needsMaterial, paragraphEditPayload,
  paragraphEditProblem, queuePaths, sameParagraphIssues, severityTag,
} from './main-path-core.ts';
import { ChapterLoopPage } from './ChapterLoopPage.tsx';
import { projectVolumes, technicalOnly, volumeOptions } from './project-volumes.ts';

type Pending = { kind: 'resolve' | 'reject' | 'edit'; group: HumanQueueChapter; issue: HumanIssue } | null;

// 页签内两个视图：待人工处理的问题（默认）与全部章节的循环进度/轮次时间线（APP-M2-T130/T131）。
export function ManualQueuePage() {
  const [view, setView] = useState('queue');
  return (
    <Tabs
      activeKey={view}
      onChange={setView}
      items={[
        { key: 'queue', label: '待人工处理', children: <HumanQueueView /> },
        { key: 'loops', label: '章节循环进度', children: <ChapterLoopPage /> },
      ]}
    />
  );
}

function HumanQueueView() {
  const { workspace, token, busy, mutate, navigate, report } = useProject();
  const [volume, setVolume] = useState<Volume | 'all'>('all');
  const [queue, setQueue] = useState<HumanQueue | null>(null);
  const [loading, setLoading] = useState(false);
  const [pending, setPending] = useState<Pending>(null);
  const [form] = Form.useForm();
  const projectId = workspace.project.id;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setQueue(await fetchHumanQueue(projectId, token, volume));
    } catch (error) {
      report(error);
    } finally {
      setLoading(false);
    }
  }, [projectId, token, volume, report]);

  useEffect(() => { void load(); }, [load, workspace.revision]);

  function open(kind: 'resolve' | 'reject' | 'edit', group: HumanQueueChapter, issue: HumanIssue) {
    form.resetFields();
    form.setFieldsValue(kind === 'resolve'
      ? { method: defaultResolveMethod(issue), note: '', also: [] }
      : kind === 'edit' ? { text: issue.paragraph_text ?? '', note: '' }
        : { reason_type: 'false_positive', reason: '' });
    setPending({ kind, group, issue });
  }

  async function submit() {
    if (!pending) return;
    const values = await form.validateFields();
    const { issue } = pending;
    try {
      if (pending.kind === 'edit') {
        await mutate(queuePaths.edit(projectId, issue.id), 'POST', paragraphEditPayload(pending.group, values.text, values.note || ''));
      } else if (pending.kind === 'resolve') {
        await mutate(queuePaths.resolve(projectId, issue.id), 'POST', {
          method: values.method, note: values.note || '', also_issue_ids: values.also || [],
        });
      } else {
        await mutate(queuePaths.reject(projectId, issue.id), 'POST', { reason_type: values.reason_type, reason: values.reason });
      }
      setPending(null);
    } catch {
      /* 错误已提示；保留填写内容 */
    }
  }

  async function recheck(group: HumanQueueChapter) {
    try {
      await mutate(queuePaths.recheck(projectId, group.chapter_id), 'POST', {});
    } catch {
      /* 错误已提示 */
    }
  }

  const days = daysUntil(queue?.deadline || workspace.project.deadline);
  const summary = queue?.summary;

  return (
    <>
      <div className="page-heading">
        <div>
          <h2>人工处理队列</h2>
          <Space size={16} wrap>
            <span>待处理 <b className={summary?.pending ? 'red' : 'green'}>{summary?.pending ?? 0}</b></span>
            <span>涉及章节 <b>{summary?.chapters ?? 0}</b></span>
            {days !== null && <span>距投标截止 <b className={days <= 3 ? 'red' : ''}>{days}</b> 天</span>}
            {summary?.by_reason.map(item => <Tag key={item.reason}>{item.label} {item.count}</Tag>)}
          </Space>
        </div>
        <Space>
          <Segmented
            value={volume}
            onChange={value => setVolume(value as Volume | 'all')}
            options={volumeOptions(workspace, true)}
          />
          <Button icon={<ReloadOutlined />} onClick={() => void load()} loading={loading}>刷新</Button>
        </Space>
      </div>
      <Spin spinning={loading && !queue}>
        {queue && !queue.chapters.length ? (
          <Card><Empty description="没有待人工处理的问题" /></Card>
        ) : (
          queue?.chapters.map(group => (
            <Card
              key={group.chapter_id}
              className="stack-card"
              data-testid="manual-queue-chapter"
              title={<Space wrap><b>{group.number} {group.title}</b><Tag>{volumeName(group.volume)}</Tag><span className="muted">{group.assignee_name ?? '未分配负责人'}</span></Space>}
              extra={
                <Space>
                  <span className="muted">{loopLine(group)}</span>
                  {group.volume_finalized && <Tag>分册已定稿</Tag>}
                  <Tooltip title={group.can_recheck ? '' : group.volume_finalized ? '分册已定稿，须先解锁' : '只有本节负责人或项目负责人可以重新检查'}>
                    <Button size="small" disabled={busy || !group.can_recheck} onClick={() => void recheck(group)}>重新检查</Button>
                  </Tooltip>
                </Space>
              }
            >
              {group.issues.map(issue => {
                const tag = severityTag(issue);
                return (
                  <div key={issue.id} className="queue-issue" data-testid="manual-queue-issue">
                    <div className="card-heading">
                      <Space wrap>
                        <b>{issue.number}</b>
                        <Tag color={tag.color}>{tag.label}</Tag>
                        <Tag>{issue.rule}</Tag>
                        {issue.human_reason_label && <Tag color="purple">{issue.human_reason_label}</Tag>}
                        {issue.fix_count > 0 && <span className="muted">已自动修正 {issue.fix_count} 次</span>}
                      </Space>
                      <Space>
                        {needsMaterial(issue) && <Button type="link" size="small" onClick={() => navigate('matrix')}>去补资料</Button>}
                        <Button type="link" size="small" onClick={() => navigate(editorChapterPath(projectId, group.chapter_id))}>在编辑台修改</Button>
                        {issue.permissions.edit && <Button size="small" disabled={busy} data-testid="queue-edit-paragraph" onClick={() => open('edit', group, issue)}>改写本段</Button>}
                        {issue.permissions.resolve && <Button size="small" type="primary" ghost disabled={busy} onClick={() => open('resolve', group, issue)}>标为已处理</Button>}
                        {issue.permissions.reject && <Button size="small" disabled={busy} onClick={() => open('reject', group, issue)}>驳回</Button>}
                      </Space>
                    </div>
                    <p className="requirement-text">{issue.message}</p>
                    <blockquote>第 {issue.paragraph_index + 1} 段：{issue.quote}</blockquote>
                    <p className="muted">{issue.suggestion}</p>
                  </div>
                );
              })}
            </Card>
          ))
        )}
      </Spin>
      <Modal
        open={!!pending}
        title={pending?.kind === 'reject' ? `驳回问题 ${pending.issue.number}` : pending?.kind === 'edit' ? `改写问题 ${pending.issue.number} 所在段落` : `标记问题 ${pending?.issue.number ?? ''} 已处理`}
        okText={pending?.kind === 'reject' ? '确认驳回' : pending?.kind === 'edit' ? '保存本段并标为已处理' : '确认已处理'}
        cancelText="取消"
        onCancel={() => setPending(null)}
        onOk={submit}
        confirmLoading={busy}
      >
        {pending?.kind === 'edit' ? (
          <Form form={form} layout="vertical">
            <Alert type="info" showIcon style={{ marginBottom: 12 }} message={`第 ${pending.issue.paragraph_index + 1} 段：${pending.issue.message}`}
              description="只改写这一段，其余段落不变；保存后生成新的章节版本，本节需重新检查确认。" />
            <Form.Item name="text" label="本段内容" rules={[{ required: true, whitespace: true, message: '请填写改写后的段落' },
              { validator: async (_, value) => { const problem = paragraphEditProblem(pending.issue.paragraph_text ?? '', value ?? ''); if (problem) throw new Error(problem); } }]}>
              <Input.TextArea rows={6} data-testid="queue-edit-text" />
            </Form.Item>
            <Form.Item name="note" label="修改说明（可选）"><Input.TextArea rows={2} maxLength={500} /></Form.Item>
          </Form>
        ) : pending?.kind === 'resolve' ? (
          <Form form={form} layout="vertical">
            <Form.Item name="method" label="处理方式" rules={[{ required: true }]}>
              <Radio.Group options={RESOLVE_METHODS.map(item => ({ ...item }))} />
            </Form.Item>
            <Form.Item name="note" label="处理说明">
              <Input.TextArea rows={2} maxLength={500} />
            </Form.Item>
            {sameParagraphIssues(pending.group, pending.issue).length > 0 && (
              <Form.Item name="also" label="同一段落一起标为已处理">
                <Checkbox.Group options={sameParagraphIssues(pending.group, pending.issue).map(item => ({ value: item.id, label: `${item.number} ${item.message}` }))} />
              </Form.Item>
            )}
            {pending.issue.code === 'PLACEHOLDER_RESIDUAL' && (
              <Alert type="info" showIcon message="保留【待补】不影响本节处理完成，但导出前仍须清零。" />
            )}
          </Form>
        ) : (
          <Form form={form} layout="vertical">
            <Form.Item name="reason_type" label="驳回类型" rules={[{ required: true }]}>
              <Radio.Group options={[{ value: 'false_positive', label: '误报' }, { value: 'not_adopted', label: '不采纳' }]} />
            </Form.Item>
            <Form.Item name="reason" label="理由" rules={[{ required: true, whitespace: true, message: '驳回须填写理由' }]}>
              <Input.TextArea rows={3} maxLength={500} />
            </Form.Item>
          </Form>
        )}
      </Modal>
    </>
  );
}
