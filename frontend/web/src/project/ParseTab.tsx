// 为什么有这个文件：提取项目工作区「解析结果」页签（ParsePage）。
// 它解决什么问题：解耦招标文件解析要求列表、条款核对修改/排除、冲突抽屉联动与分册分流，降低 ProjectPages 行数。

import React, { useState } from 'react';
import {
  Alert,
  App as AntApp,
  Badge,
  Button,
  Card,
  Col,
  Drawer,
  Empty,
  Form,
  Input,
  Modal,
  Progress,
  Row,
  Select,
  Space,
  Tag,
  Tooltip,
} from 'antd';
import { CheckCircleOutlined } from '@ant-design/icons';
import { categoryName, useProject, volumeName } from '../app/context.tsx';
import { projectCan } from './project-team.ts';
import { SourceLink } from './SourceLink.tsx';
import { OriginalPreview } from './OriginalPreview.tsx';
import { ConflictCards } from './ConflictCards.tsx';
import { OmissionsDrawer } from './OmissionsDrawer.tsx';
import type { Requirement, Source } from '../shared/types.ts';

const statusName = (value: string) =>
  value === 'confirmed' ? '已确认' : value === 'needs_review' ? '需重新核对' : value === 'rejected' ? '已排除' : '待确认';
const statusColor = (value: string) =>
  value === 'confirmed' ? 'green' : value === 'rejected' ? 'default' : 'orange';
const ignoreFailure = () => undefined;

export function ParsePage() {
  const { workspace, busy, mutate, navigate } = useProject();
  const { modal } = AntApp.useApp();
  const [category, setCategory] = useState('all');
  const [source, setSource] = useState<Source | null>(workspace.requirements[0]?.source ?? null);
  const [selected, setSelected] = useState<string | null>(null);
  const [conflictsOpen, setConflictsOpen] = useState(false);
  const [omissionsOpen, setOmissionsOpen] = useState(false);
  const [edit, setEdit] = useState<Requirement | null>(null);
  const [form] = Form.useForm();

  const categories = [...new Set(workspace.requirements.map(item => item.category))];
  const pending = workspace.requirements.filter(item => item.status === 'pending').length;
  const conflicts = workspace.conflicts.filter(item => item.status === 'pending').length;
  const pendingFacts = workspace.facts.filter(item => item.status === 'pending').length;
  const omissions = workspace.omissions_pending ?? 0;
  const shown = workspace.requirements.filter(item => category === 'all' || item.category === category);

  function editItem(item: Requirement) {
    setEdit(item);
    form.setFieldsValue(item);
  }

  async function save() {
    const values = await form.validateFields();
    try {
      await mutate(`/api/v1/projects/${workspace.project.id}/requirements/${edit!.id}`, 'PATCH', {
        text: values.text,
        category: values.category,
        volume: values.volume,
        chapter_id: values.chapter_id || null,
        status: values.status,
        reason: values.reason || '',
      });
      setEdit(null);
    } catch {
      /* 仍保留人工输入 */
    }
  }

  async function confirm() {
    try {
      await mutate(`/api/v1/projects/${workspace.project.id}/parse/confirm`, 'POST', {});
      navigate('matrix');
    } catch {
      /* 按后台列出的前提继续处理 */
    }
  }

  function reject(item: Requirement) {
    let reason = '';
    modal.confirm({
      title: '排除误抽取条目',
      content: (
        <Input.TextArea
          aria-label="排除理由"
          placeholder="写明为何不是当前项目的响应要求"
          onChange={e => {
            reason = e.target.value;
          }}
        />
      ),
      okText: '确认排除',
      onOk: async () => {
        if (!reason.trim()) throw new Error('请填写排除理由');
        await mutate(`/api/v1/projects/${workspace.project.id}/requirements/${item.id}`, 'PATCH', {
          status: 'rejected',
          reason,
        });
      },
    });
  }

  return (
    <>
      <div className="postprocess-bar">
        <span>
          <CheckCircleOutlined className="green" /> 原文抽取 {workspace.requirements.length} 条 · 本地规则 · 人工核对
        </span>
        <Space>
          <Button danger size="small" onClick={() => setConflictsOpen(true)}>
            冲突待选定 {conflicts}
          </Button>
          <Button danger={omissions > 0} size="small" onClick={() => setOmissionsOpen(true)} data-testid="omissions-button">
            疑似遗漏 {omissions}
          </Button>
          <Button
            type="primary"
            size="small"
            disabled={
              busy ||
              !projectCan(workspace, 'prepare_sources') ||
              !workspace.requirements.length ||
              pending > 0 ||
              conflicts > 0 ||
              omissions > 0 ||
              pendingFacts > 0
            }
            onClick={confirm}
          >
            {workspace.parse_confirmed ? '已确认解析结果' : '确认解析结果并进入矩阵'}
          </Button>
        </Space>
      </div>
      <div className="parse-layout">
        <OriginalPreview source={source} />
        <aside className="parse-category">
          <div className="panel-title">
            抽取类别 <span className="muted">{workspace.requirements.length} 条</span>
          </div>
          <button className={category === 'all' ? 'active' : ''} onClick={() => setCategory('all')}>
            全部要求{' '}
            <span>
              {workspace.requirements.filter(item => item.status === 'confirmed').length}/
              {workspace.requirements.length}
            </span>
          </button>
          {categories.map((value, index) => (
            <button
              key={value}
              className={category === value ? 'active' : ''}
              onClick={() => setCategory(value)}
            >
              {index + 1} {categoryName(value)}
              <span>
                {workspace.requirements.filter(item => item.category === value && item.status === 'confirmed').length}/
                {workspace.requirements.filter(item => item.category === value).length}
              </span>
            </button>
          ))}
          <div className="category-section">
            后处理{' '}
            <button onClick={() => setConflictsOpen(true)}>
              冲突待选定 <Badge count={conflicts} size="small" />
            </button>
            <button onClick={() => setOmissionsOpen(true)}>
              疑似遗漏 <Badge count={omissions} size="small" />
            </button>
            <button onClick={() => navigate('facts')}>
              项目事实待核对 <Badge count={pendingFacts} size="small" />
            </button>
          </div>
        </aside>
        <section className="parse-cards">
          <div className="panel-title">
            {category === 'all' ? '全部要求' : categoryName(category)}{' '}
            <span className="muted">{shown.length} 条</span>
          </div>
          <Alert
            type="info"
            showIcon
            message="点条目可定位左侧原文。每条要求都需核对后确认；排除必须写理由。"
          />
          {shown.length ? (
            shown.map(item => (
              <Card
                size="small"
                key={item.id}
                className={`requirement-card ${selected === item.id ? 'selected' : ''} ${
                  item.status === 'rejected' ? 'rejected' : ''
                }`}
                onClick={() => {
                  setSelected(item.id);
                  setSource(item.source);
                }}
              >
                <div className="card-heading">
                  <b>{categoryName(item.category)}</b>
                  <Space>
                    <SourceLink source={item.source} onClick={setSource} />
                    <Tag color={statusColor(item.status)}>{statusName(item.status)}</Tag>
                  </Space>
                </div>
                <p className="requirement-text">{item.text}</p>
                <blockquote>{item.source.quote}</blockquote>
                <Space>
                  <Tag>{volumeName(item.volume)}</Tag>
                  <span className="muted">
                    {workspace.chapters.find(chapter => chapter.id === item.chapter_id)?.title ?? '尚未分配章节'}
                  </span>
                </Space>
                {item.reason && <p className="muted">处理说明：{item.reason}</p>}
                <div className="card-actions">
                  <Button
                    type="link"
                    size="small"
                    disabled={busy || !projectCan(workspace, 'prepare_sources') || item.status === 'confirmed'}
                    onClick={e => {
                      e.stopPropagation();
                      void mutate(`/api/v1/projects/${workspace.project.id}/requirements/${item.id}`, 'PATCH', {
                        status: 'confirmed',
                      }).catch(ignoreFailure);
                    }}
                  >
                    确认
                  </Button>
                  <Button
                    type="link"
                    size="small"
                    disabled={busy || !projectCan(workspace, 'prepare_sources')}
                    onClick={e => {
                      e.stopPropagation();
                      editItem(item);
                    }}
                  >
                    修改
                  </Button>
                  <Button
                    type="link"
                    size="small"
                    danger
                    disabled={busy || !projectCan(workspace, 'prepare_sources') || item.status === 'rejected'}
                    onClick={e => {
                      e.stopPropagation();
                      reject(item);
                    }}
                  >
                    排除（误抽取）
                  </Button>
                </div>
              </Card>
            ))
          ) : (
            <Empty description="还没有抽取条目，请上传并解析招标文件" />
          )}
          <div className="parse-prerequisites">
            确认前提：无待处理冲突与疑似遗漏；要求逐条确认或填写排除理由；项目事实完成核对。
            <Progress
              size="small"
              percent={
                workspace.requirements.length
                  ? Math.round(((workspace.requirements.length - pending) / workspace.requirements.length) * 100)
                  : 0
              }
            />
          </div>
        </section>
      </div>
      <Drawer
        title="抽取后处理 · 冲突待选定"
        open={conflictsOpen}
        onClose={() => setConflictsOpen(false)}
        width={560}
      >
        <Alert
          type="error"
          showIcon
          message="冲突全部处理后才能确认解析结果"
          description="选择正确取值，并写明依据；未选事实不会被自动当作正式承诺。"
        />
        <ConflictCards
          onLocate={value => {
            setSource(value);
          }}
        />
        <Alert
          className="page-notice"
          type="info"
          message="“引用未解析”专用页签尚未实现"
          description="含“详见/参照”引用的条目在确认时须写明人工核对结果。"
        />
      </Drawer>
      <OmissionsDrawer open={omissionsOpen} onClose={() => setOmissionsOpen(false)} onLocate={setSource} />
      <Modal
        title="修改抽取要求"
        open={!!edit}
        onCancel={() => setEdit(null)}
        onOk={save}
        cancelText="取消"
        confirmLoading={busy}
        okText="保存修改"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="text" label="要求原文" rules={[{ required: true, whitespace: true }]}>
            <Input.TextArea rows={4} />
          </Form.Item>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="category" label="抽取类别" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="volume" label="归属分册">
                <Select
                  options={[
                    { value: 'technical', label: '技术分册' },
                    { value: 'business', label: '商务分册' },
                  ]}
                />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="chapter_id" label="对应章节">
            <Select
              allowClear
              options={workspace.chapters.map(item => ({ value: item.id, label: item.title }))}
            />
          </Form.Item>
          <Form.Item name="status" label="核对状态">
            <Select
              options={[
                { value: 'pending', label: '待确认' },
                { value: 'confirmed', label: '已确认' },
                { value: 'rejected', label: '已排除' },
              ]}
            />
          </Form.Item>
          <Form.Item name="reason" label="修改或排除说明">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
