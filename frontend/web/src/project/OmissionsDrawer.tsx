// 为什么有这个文件：解析结果页的「疑似遗漏」抽屉（PRD v1.8 §5.2.4 第④步）。
// 它解决什么问题：兜底扫描命中但没有被星号/废标条目覆盖的原文逐条列出，项目负责人逐条新增为条目或写理由排除；不提供批量按钮。

import { useCallback, useEffect, useState } from 'react';
import { Alert, Button, Card, Drawer, Empty, Form, Input, Modal, Radio, Select, Space, Tag } from 'antd';
import { useProject } from '../app/context.tsx';
import type { ScanHit, ScanHitList, Source } from '../shared/types.ts';
import { SCAN_STATE_LABELS, defaultHitCategory, fetchScanHits, queuePaths } from './main-path-core.ts';

type Pending = { kind: 'add' | 'exclude'; hit: ScanHit } | null;

export function OmissionsDrawer({ open, onClose, onLocate }: { open: boolean; onClose: () => void; onLocate: (source: Source) => void }) {
  const { workspace, token, busy, mutate, report } = useProject();
  const [data, setData] = useState<ScanHitList | null>(null);
  const [pending, setPending] = useState<Pending>(null);
  const [form] = Form.useForm();
  const projectId = workspace.project.id;

  const load = useCallback(async () => {
    try {
      setData(await fetchScanHits(projectId, token));
    } catch (error) {
      report(error);
    }
  }, [projectId, token, report]);

  useEffect(() => { if (open) void load(); }, [open, load, workspace.revision]);

  function start(kind: 'add' | 'exclude', hit: ScanHit) {
    form.resetFields();
    if (kind === 'add') form.setFieldsValue({ category: defaultHitCategory(hit), volume: 'technical', text: hit.quote });
    setPending({ kind, hit });
  }

  async function submit() {
    if (!pending) return;
    const values = await form.validateFields();
    const path = pending.kind === 'add' ? queuePaths.addHit(projectId, pending.hit.id) : queuePaths.excludeHit(projectId, pending.hit.id);
    try {
      await mutate(path, 'POST', values);
      setPending(null);
    } catch {
      /* 错误已提示 */
    }
  }

  const hits = data?.hits ?? [];
  return (
    <Drawer title={`星号/废标兜底扫描 · 疑似遗漏 ${data?.summary.suspected ?? 0}`} open={open} onClose={onClose} width={600}>
      {data?.summary.too_many && <Alert type="warning" showIcon className="page-notice" message="命中超过 30 条，请公司管理员复核兜底词表。" />}
      {hits.length ? hits.map(hit => {
        const state = SCAN_STATE_LABELS[hit.state];
        return (
          <Card key={hit.id} size="small" className="scan-hit" data-testid="scan-hit">
            <div className="card-heading">
              <Space wrap>
                <Tag color={state.color}>{state.label}</Tag>
                <a onClick={() => onLocate({ file_id: hit.file_id, page: hit.page, quote: hit.quote })}>{hit.filename} 第 {hit.page} 页</a>
                {hit.terms.map(term => <Tag key={term}>{term}</Tag>)}
              </Space>
              {hit.state === 'suspected' && data?.can_handle && (
                <Space>
                  <Button size="small" type="primary" ghost disabled={busy} onClick={() => start('add', hit)}>新增为条目</Button>
                  <Button size="small" disabled={busy} onClick={() => start('exclude', hit)}>排除</Button>
                </Space>
              )}
            </div>
            <blockquote>{hit.quote}</blockquote>
            {hit.state === 'excluded' && <p className="muted">排除理由：{hit.reason}</p>}
          </Card>
        );
      }) : <Empty description="兜底扫描没有命中" />}
      {data && <p className="muted">词表版本 {data.scan_version}</p>}
      <Modal
        open={!!pending}
        title={pending?.kind === 'add' ? '新增为星号/废标条目' : '排除疑似遗漏'}
        okText={pending?.kind === 'add' ? '新增' : '确认排除'}
        cancelText="取消"
        onCancel={() => setPending(null)}
        onOk={submit}
        confirmLoading={busy}
      >
        <Form form={form} layout="vertical">
          {pending?.kind === 'add' ? (
            <>
              <Form.Item name="category" label="类别" rules={[{ required: true }]}>
                <Radio.Group options={[{ value: 'star', label: '星号条款' }, { value: 'disqualification', label: '废标条款' }]} />
              </Form.Item>
              <Form.Item name="volume" label="归属分册" rules={[{ required: true }]}>
                <Select options={[{ value: 'technical', label: '技术分册' }, { value: 'business', label: '商务分册' }]} />
              </Form.Item>
              <Form.Item name="text" label="条款原文" rules={[{ required: true, whitespace: true }]}>
                <Input.TextArea rows={3} />
              </Form.Item>
            </>
          ) : (
            <Form.Item name="reason" label="排除理由" rules={[{ required: true, whitespace: true, message: '排除必须填写理由' }]}>
              <Input.TextArea rows={3} maxLength={500} />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </Drawer>
  );
}
