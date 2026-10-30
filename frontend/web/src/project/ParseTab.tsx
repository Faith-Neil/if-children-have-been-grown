// 为什么有这个文件：提取项目工作区「解析结果」页签（ParsePage）。
// 它解决什么问题：解耦招标文件解析要求列表、条款核对修改/排除、冲突抽屉联动与分册分流，降低 ProjectPages 行数。
// PRD v1.8 §5.2.2（APP-M2-T104）：左原文预览 · 中 10 类分类树（评分类下列评分项与得分要点）· 右条目卡片；
// 顶部“冲突待选定 / 疑似遗漏 / 引用未解析”三个入口；“确认解析结果”旁列出还差哪些前提；星号、废标、资格三类没有批量确认。

import React, { useEffect, useState } from 'react';
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
import { request } from '../shared/api.ts';
import { batchCandidates, confidenceLabel, gateCount, gateSummary, lowConfidence, needsReentry, nodeCategory, nodeRows, nodeTitle, threshold, unmetGates, type ParseReview, type TreeNode } from './parse-review-core.ts';

const statusName = (value: string) =>
  value === 'confirmed' ? '已确认' : value === 'needs_review' ? '需重新核对' : value === 'rejected' ? '已排除' : '待确认';
const statusColor = (value: string) =>
  value === 'confirmed' ? 'green' : value === 'rejected' ? 'default' : 'orange';
const ignoreFailure = () => undefined;

export function ParsePage() {
  const { workspace, token, busy, mutate, navigate } = useProject();
  const { modal } = AntApp.useApp();
  const [node, setNode] = useState<TreeNode>({ kind: 'all' });
  const [review, setReview] = useState<ParseReview | null>(null);
  const [referencesOpen, setReferencesOpen] = useState(false);
  useEffect(() => {
    let cancelled = false;
    request<ParseReview>(`/api/v1/projects/${workspace.project.id}/parse/review`, token)
      .then(value => { if (!cancelled) setReview(value); }).catch(() => { if (!cancelled) setReview(null); });
    return () => { cancelled = true; };
  }, [workspace.project.id, workspace.revision, token]);
  const [source, setSource] = useState<Source | null>(workspace.requirements[0]?.source ?? null);
  const [selected, setSelected] = useState<string | null>(null);
  const [conflictsOpen, setConflictsOpen] = useState(false);
  const [omissionsOpen, setOmissionsOpen] = useState(false);
  const [edit, setEdit] = useState<Requirement | null>(null);
  const [form] = Form.useForm();

  const pending = workspace.requirements.filter(item => item.status === 'pending').length;
  const conflicts = workspace.conflicts.filter(item => item.status === 'pending').length;
  const pendingFacts = workspace.facts.filter(item => item.status === 'pending').length;
  const omissions = workspace.omissions_pending ?? 0;
  const references = workspace.requirements.filter(item => item.reference_status === 'unresolved' && item.status !== 'rejected');
  const limit = threshold(review);
  const unreadable = workspace.requirements.filter(needsReentry).length;
  const low = workspace.requirements.filter(item => lowConfidence(item, limit)).length;
  const shown = nodeRows(workspace.requirements, review, node);
  const currentCategory = nodeCategory(review, node);
  const batch = batchCandidates(workspace.requirements, review, node);
  const lead = projectCan(workspace, 'prepare_sources');
  const canConfirm = review ? review.can_confirm : !(pending > 0 || conflicts > 0 || omissions > 0 || pendingFacts > 0);

  async function batchConfirm() {
    try {
      await mutate(`/api/v1/projects/${workspace.project.id}/requirements/batch-confirm`, 'POST', { requirement_ids: batch.map(item => item.id) });
    } catch { /* 后台列出不能批量确认的条目 */ }
  }
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

  const SKIP_LABEL: Record<string, string> = { contract: '合同条款', format: '文件格式', notice: '须知说明', other: '其他说明' };
  const extractionNote = workspace.files
    .map(file => file.extraction)
    .filter((x): x is NonNullable<typeof x> => Boolean(x?.structured))
    .reduce<string[]>((notes, x) => {
      const skipped = Object.entries(x.skipped_items).map(([kind, n]) => `${SKIP_LABEL[kind] ?? kind} ${n} 项`).join('、');
      notes.push(`识别 ${x.sections} 个章节，实质性条款 ${x.mandatory} 条${skipped ? `；未作为条款：${skipped}（可在原文中查看）` : ''}`);
      return notes;
    }, [])
    .join('；');

  return (
    <>
      <div className="postprocess-bar">
        <span>
          <CheckCircleOutlined className="green" /> 原文抽取 {workspace.requirements.length} 条 · 按章节条目抽取 · 人工核对
          {extractionNote && <span className="muted" data-testid="extraction-summary"> · {extractionNote}</span>}
        </span>
        <Space>
          <Button danger size="small" onClick={() => setConflictsOpen(true)}>
            冲突待选定 {conflicts}
          </Button>
          <Button danger={omissions > 0} size="small" onClick={() => setOmissionsOpen(true)} data-testid="omissions-button">
            疑似遗漏 {omissions}
          </Button>
          <Button size="small" onClick={() => setReferencesOpen(true)} data-testid="references-button">
            引用未解析 {review ? gateCount(review, 'REFERENCES_UNRESOLVED') : references.length}
          </Button>
          <Button
            type="primary"
            size="small"
            disabled={busy || !lead || !workspace.requirements.length || !canConfirm}
            onClick={confirm}
            data-testid="parse-confirm-button"
          >
            {workspace.parse_confirmed ? '已确认解析结果' : '确认解析结果并进入矩阵'}
          </Button>
          {review && (
            <Tooltip title={unmetGates(review).map(g => `${g.label}：${g.count}`).join('；') || undefined}>
              <span className={unmetGates(review).length ? 'orange' : 'muted'} data-testid="parse-gate-summary">{gateSummary(review)}</span>
            </Tooltip>
          )}
        </Space>
      </div>
      <div className="parse-layout">
        <OriginalPreview source={source} />
        <aside className="parse-category">
          <div className="panel-title">
            抽取类别 <span className="muted">{workspace.requirements.length} 条</span>
          </div>
          <button className={node.kind === 'all' ? 'active' : ''} onClick={() => setNode({ kind: 'all' })} data-testid="parse-tree-all">
            全部要求 <span>{pending ? `待 ${pending}` : ''} {workspace.requirements.length}</span>
          </button>
          {(review?.categories ?? []).map(item => (
            <React.Fragment key={item.key}>
              <button
                className={node.kind === 'category' && node.key === item.key ? 'active' : ''}
                onClick={() => setNode({ kind: 'category', key: item.key })}
                data-testid="parse-tree-category"
                data-category={item.key}
              >
                {item.no} {item.label}
                <span>{item.pending ? <b className="orange">待 {item.pending}</b> : null} {item.total}</span>
              </button>
              {item.key === 'scoring' && (node.kind === 'category' || node.kind === 'group') && node.key === 'scoring' && (item.groups ?? []).map(group => (
                <button key={group.name} className={`tree-child ${node.kind === 'group' && node.name === group.name ? 'active' : ''}`}
                  onClick={() => setNode({ kind: 'group', key: 'scoring', name: group.name })} data-testid="parse-tree-group">
                  {group.name}{group.score ? `（${group.score} 分）` : ''}
                  <span>{group.pending ? <b className="orange">待 {group.pending}</b> : null} {group.ids.length} 个要点</span>
                </button>
              ))}
            </React.Fragment>
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
            <button data-testid="parse-unreadable-node" onClick={() => setNode({ kind: 'quality', which: 'unreadable' })}>
              原文不可读 <Badge count={unreadable} size="small" />
            </button>
            <button data-testid="parse-low-confidence-node" onClick={() => setNode({ kind: 'quality', which: 'low' })}>
              低置信度 <Badge count={low} size="small" color="orange" />
            </button>
          </div>
        </aside>
        <section className="parse-cards">
          <div className="panel-title parse-cards-title">
            <span>{nodeTitle(review, node)} <span className="muted">{shown.length} 条</span></span>
            {currentCategory && lead && (currentCategory.batch_allowed ? (
              <Button size="small" data-testid="parse-batch-confirm" disabled={busy || !batch.length} onClick={() => void batchConfirm()}>
                确认本类 {batch.length} 条
              </Button>
            ) : (
              <Tag color="purple" data-testid="parse-individual-only">本类须逐条确认</Tag>
            ))}
          </div>
          {currentCategory && currentCategory.facts > 0 && (
            <Alert className="page-notice" type="info" showIcon message={`本类另有 ${currentCategory.facts} 条项目事实`} action={<Button size="small" onClick={() => navigate('facts')}>去项目事实表</Button>} />
          )}
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
                style={needsReentry(item) ? { borderColor: '#ff4d4f' } : lowConfidence(item, limit) ? { borderColor: '#fa8c16', background: '#fff7e6' } : undefined}
                onClick={() => {
                  setSelected(item.id);
                  setSource(item.source);
                }}
              >
                <div className="card-heading">
                  <b>{review?.categories.find(c => c.key === review.requirement_categories[item.id])?.label ?? categoryName(item.category)}</b>
                  <Space>
                    <SourceLink source={item.source} onClick={setSource} />
                    {needsReentry(item) && (
                      <Tooltip title={item.unreadable_reason || '原文摘录乱码，请对照原页补录'}>
                        <Tag color="red" data-testid="unreadable-tag">原文不可读</Tag>
                      </Tooltip>
                    )}
                    {lowConfidence(item, limit) && <Tag color="orange" data-testid="low-confidence-tag">{confidenceLabel(item)}</Tag>}
                    {item.manually_edited && <Tag color="blue" data-testid="manually-edited-tag">已人工修改</Tag>}
                    <Tag color={statusColor(item.status)}>{statusName(item.status)}</Tag>
                  </Space>
                </div>
                {item.section_path?.length ? <p className="muted requirement-section">{item.section_path.join(' › ')}{typeof item.score === 'number' ? ` · ${item.score} 分` : ''}</p> : null}
                <p className="requirement-text">{item.text}</p>
                {item.source.quote !== item.text && <blockquote>{item.source.quote}</blockquote>}
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
                    disabled={busy || !projectCan(workspace, 'prepare_sources') || item.status === 'confirmed' || needsReentry(item)}
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
      </Drawer>
      <Drawer title="抽取后处理 · 引用未解析" open={referencesOpen} onClose={() => setReferencesOpen(false)} width={560}>
        <Alert type="info" showIcon message="不阻断确认解析结果" description="条目中有“详见/参照”等引用：对照原文核对引用的内容，在说明中写明核对结果后确认。这类条目不能批量确认。" />
        {references.length ? references.map(item => (
          <Card key={item.id} size="small" className="requirement-card" data-testid="reference-item">
            <p className="requirement-text">{item.text}</p>
            <p className="muted">引用：{(item.references ?? []).join('；')}</p>
            <Space>
              <SourceLink source={item.source} onClick={setSource} />
              <Button size="small" type="link" disabled={busy || !lead} onClick={() => { setReferencesOpen(false); editItem({ ...item, status: 'confirmed' }); }}>写明核对结果并确认</Button>
            </Space>
          </Card>
        )) : <Empty description="没有未解析的引用" />}
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
