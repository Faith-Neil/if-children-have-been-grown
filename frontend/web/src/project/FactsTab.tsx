// 为什么有这个文件：提取项目工作区「项目事实表」页签（FactsPage）。
// 它解决什么问题：解耦项目事实表格核对、服务承诺矩阵只读引用核查与事实修改弹窗交互，降低 ProjectPages 行数。

import React, { useState } from 'react';
import { Alert, Button, Card, Drawer, Form, Input, Modal, Select, Table, Tag } from 'antd';
import { useProject } from '../app/context.tsx';
import { projectCan } from './project-team.ts';
import { displaySlaValue } from '../admin/sla-form.ts';
import { SourceLink } from './SourceLink.tsx';
import { OriginalPreview } from './OriginalPreview.tsx';
import { ConflictCards } from './ConflictCards.tsx';
import type { Fact, Source } from '../shared/types.ts';
import { needsReentry } from './parse-review-core.ts';

const statusName = (value: string) =>
  value === 'confirmed' ? '已确认' : value === 'needs_review' ? '需重新核对' : value === 'rejected' ? '已排除' : '待确认';
const statusColor = (value: string) =>
  value === 'confirmed' ? 'green' : value === 'rejected' ? 'default' : 'orange';

export function FactsPage() {
  const { workspace, busy, mutate, navigate } = useProject();
  const [edit, setEdit] = useState<Fact | null>(null);
  const [source, setSource] = useState<Source | null>(null);
  const [form] = Form.useForm();
  const referenced = edit?.source_type === 'sla';

  async function save() {
    const values = await form.validateFields();
    if (
      !edit ||
      !projectCan(workspace, 'edit_facts') ||
      ((referenced || edit.required) && !projectCan(workspace, 'confirm_facts'))
    )
      return;
    try {
      await mutate(`/api/v1/projects/${workspace.project.id}/facts/${encodeURIComponent(edit.id)}`, 'PATCH', {
        ...(referenced ? {} : { value: values.value }),
        ...(projectCan(workspace, 'confirm_facts') ? { status: values.status } : {}),
        reason: values.reason || '',
      });
      setEdit(null);
    } catch {
      /* 保留输入供重新核对；引用事实绝不另写一份取值。 */
    }
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <h2>项目事实表</h2>
          <p>统一项目口径；服务承诺直接引用矩阵里的取值，修改后必须重新核对。</p>
        </div>
      </div>
      {workspace.facts.some(item => ['pending', 'needs_review'].includes(item.status)) && (
        <Alert
          className="page-notice"
          showIcon
          type="warning"
          message="存在待确认或需重新核对的事实；必备服务承诺由负责人逐条确认"
        />
      )}
      <Card>
        <Table
          rowKey="id"
          size="small"
          dataSource={workspace.facts}
          pagination={false}
          columns={[
            {
              title: '事实名称',
              render: (_, item) => (
                <>
                  {item.key}
                  {item.required && <Tag color="red">必备</Tag>}
                </>
              ),
            },
            {
              title: '当前取值',
              render: (_, item) => (
                <>
                  {displaySlaValue(item.value, item.unit)}{' '}
                  {needsReentry(item) && <Tag color="red" title={item.unreadable_reason}>原文不可读</Tag>}
                </>
              ),
            },
            {
              title: '来源',
              render: (_, item) => (
                <>
                  {item.source_type === 'sla' && (
                    <p>
                      <a onClick={() => navigate('matrix')}>引用服务承诺矩阵（值只读）</a>
                    </p>
                  )}
                  <SourceLink source={item.source} onClick={setSource} />
                </>
              ),
            },
            {
              title: '状态',
              dataIndex: 'status',
              render: value => <Tag color={statusColor(value)}>{statusName(value)}</Tag>,
            },
            { title: '说明', dataIndex: 'reason' },
            {
              title: '操作',
              render: (_, item) => (
                <Button
                  type="link"
                  disabled={
                    busy ||
                    !projectCan(workspace, 'edit_facts') ||
                    ((item.source_type === 'sla' || item.required) && !projectCan(workspace, 'confirm_facts'))
                  }
                  onClick={() => {
                    setEdit(item);
                    form.setFieldsValue({
                      ...item,
                      status: item.source_type === 'sla' ? 'confirmed' : item.status,
                    });
                  }}
                >
                  {item.source_type === 'sla' ? '逐项核对并确认' : '核对与修改'}
                </Button>
              ),
            },
          ]}
        />
      </Card>
      <div className="page-notice">
        <h3>取值冲突</h3>
        <ConflictCards onLocate={setSource} />
      </div>
      <Drawer title="事实来源" width={760} open={!!source} onClose={() => setSource(null)}>
        <OriginalPreview source={source} />
      </Drawer>
      <Modal
        title={referenced ? '负责人确认引用事实' : '核对项目事实'}
        open={!!edit}
        onCancel={() => setEdit(null)}
        onOk={save}
        cancelText="取消"
        okText={projectCan(workspace, 'confirm_facts') ? '保存确认' : '保存待核对修改'}
        confirmLoading={busy}
        okButtonProps={{
          disabled:
            !projectCan(workspace, 'edit_facts') ||
            ((referenced || edit?.required) && !projectCan(workspace, 'confirm_facts')),
        }}
      >
        {referenced && (
          <Alert
            className="page-notice"
            showIcon
            type="info"
            message="此值来自服务承诺矩阵，本页只确认，不另外修改取值"
            description={displaySlaValue(edit?.value, edit?.unit)}
          />
        )}
        <Form form={form} layout="vertical" disabled={busy || !projectCan(workspace, 'edit_facts')}>
          <Form.Item
            name="value"
            label={edit?.key}
            rules={referenced ? [] : [{ required: true, whitespace: true }]}
          >
            <Input.TextArea rows={3} disabled={referenced} />
          </Form.Item>
          <Form.Item name="status" label="人工核对状态">
            <Select
              disabled={!projectCan(workspace, 'confirm_facts')}
              options={
                referenced
                  ? [{ value: 'confirmed', label: '已逐项核对当前取值' }]
                  : [
                      { value: 'pending', label: '待确认' },
                      { value: 'confirmed', label: '已确认' },
                      { value: 'rejected', label: '已排除' },
                    ]
              }
            />
          </Form.Item>
          <Form.Item name="reason" label="核对依据">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
