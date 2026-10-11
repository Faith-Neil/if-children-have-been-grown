// 为什么有这个文件：展示已经接通的资料与任务，并标明其余页面的真实边界。
// 它解决什么问题：辅助页面不再硬编码成功，也不会把待实现能力误当作完成。
import { useRef, useState } from 'react';
import { Alert, App as AntApp, Button, Card, Col, Empty, Form, Input, Modal, Progress, Row, Select, Space, Statistic, Table, Tabs, Tag } from 'antd';
import { PlusOutlined, SearchOutlined } from '@ant-design/icons';
import { formatTime } from './context';
import type { Account, Evidence, Job, SlaTemplate } from './types';
import { SlaTemplatesPage } from './SlaPages';
import { captureLibraryReview, libraryReviewProblem, libraryWriteVersion, loadReviewedLibrary, type LibraryMutation, type LibraryReader, type LibraryReviewBasis } from './library-review';
import type { TemplateReader } from './template-review';

const types = [{ value: 'qualification', label: '企业资质' }, { value: 'personnel', label: '人员证书' }, { value: 'performance', label: '项目业绩' }, { value: 'sla', label: '服务承诺资料' }, { value: 'snippet', label: '方案片段' }, { value: 'history', label: '历史标书（参考）' }];
const typeName = (value: string) => types.find(item => item.value === value)?.label ?? value;

export function LibraryPage({ items, templates, user, busy, mutate, report, read, readTemplates, libraryRevision, templatesRevision, globalSearch = '' }: { items: Evidence[]; templates: SlaTemplate[]; user: Account; busy: boolean; mutate: LibraryMutation; report: (error: unknown) => void; read: LibraryReader; readTemplates: TemplateReader; libraryRevision: number; templatesRevision: number; globalSearch?: string }) {
  const { modal, message } = AntApp.useApp();
  const [category, setCategory] = useState('all');
  const [search, setSearch] = useState('');
  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState<Evidence | null>(null);
  const [reviewBasis, setReviewBasis] = useState<LibraryReviewBasis | null>(null);
  const [reviewing, setReviewing] = useState(false);
  const [form] = Form.useForm();
  const editorSession = useRef(0);
  const latest = useRef({ company_id: user.company_id, revision: libraryRevision, items, user, busy: busy || reviewing });
  latest.current = { company_id: user.company_id, revision: libraryRevision, items, user, busy: busy || reviewing };
  const reviewProblem = open ? libraryReviewProblem(reviewBasis, latest.current) : null;
  const usable = (item: Evidence) => item.usable_as_evidence ?? (item.status === 'confirmed' && item.type !== 'history');
  const canSave = () => latest.current.user.role !== 'viewer' && !latest.current.busy;
  async function save() {
    if (!canSave() || !open) return;
    const session = editorSession.current;
    let values;
    try { values = await form.validateFields(); } catch { return; }
    if (session !== editorSession.current || !canSave()) return;
    let expected;
    try { expected = libraryWriteVersion(reviewBasis, latest.current); } catch (error) { report(error); return; }
    try {
      await mutate(edit ? `/api/v1/library/${edit.id}` : '/api/v1/library', edit ? 'PATCH' : 'POST', { name: values.name, type: values.type, content: values.content, valid_until: values.valid_until || null, status: values.status, reason: values.reason || '' }, expected);
      if (session === editorSession.current) setOpen(false);
    } catch { /* 父级报告请求错误；原版本与填写保留，不借刷新后的版本重试。 */ }
  }
  function create() {
    if (busy || user.role === 'viewer') return;
    try {
      const basis = captureLibraryReview(latest.current, null);
      editorSession.current++; setEdit(null); setReviewBasis(basis); form.resetFields(); form.setFieldsValue({ type: 'qualification', status: 'pending' }); setOpen(true);
    } catch (error) { report(error); }
  }
  function editing(item: Evidence) {
    if (busy) return;
    try {
      const basis = captureLibraryReview(latest.current, item.id);
      editorSession.current++; setEdit(basis.item); setReviewBasis(basis); form.resetFields(); form.setFieldsValue(basis.item); setOpen(true);
    } catch (error) { report(error); }
  }
  function describe(item: Partial<Evidence> | null) {
    if (!item) return '新资料，尚未保存。';
    return [`资料：${item.name || '未填写'}`, `类别：${typeName(item.type || '')}`, `记录版本：${item.revision ?? '尚未保存'}`, `有效期：${item.valid_until || '未登记到期日'}`, `确认状态：${item.status === 'confirmed' ? '已确认' : item.status === 'rejected' ? '已排除' : '待确认'}`, `内容：\n${item.content || '未填写'}`, `说明：${item.reason || '未填写'}`].join('\n');
  }
  async function reviewLatest() {
    if (latest.current.busy || !reviewBasis || !open) return;
    const session = editorSession.current;
    const original = reviewBasis;
    const local = form.getFieldsValue() as Partial<Evidence>;
    let proposal;
    setReviewing(true);
    try {
      const fresh = await read();
      if (session !== editorSession.current) return;
      if (fresh.company_id !== original.company_id) throw new Error('读取期间公司已变化，原填写未替换，请重新核对。');
      proposal = captureLibraryReview(fresh, original.item_id);
    } catch (error) { report(error); return; } finally { setReviewing(false); }
    const replaceForm = original.item_basis !== proposal.item_basis;
    modal.confirm({ title: '核对资料与公司最新版本', width: 1080,
      content: <><Row gutter={12}>{[{ title: '最初读取的已保存资料', value: describe(original.item) }, { title: '当前未保存的填写（可先复制保留）', value: describe(local) }, { title: '后台当前已保存资料', value: describe(proposal.item) }].map(column => <Col span={8} key={column.title}><Card size="small" title={column.title}><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', maxHeight: 320, overflowY: 'auto' }}>{column.value}</pre></Card></Col>)}</Row><p>最初公司资料库版本：{original.revision}；本次核对版本：{proposal.revision}。</p><Alert showIcon type={replaceForm ? 'warning' : 'info'} message={replaceForm ? '这条资料已变化：载入将替换当前未保存的填写，请先复制需要保留的文字。' : '这条资料未变化：确认后只更新已核对的公司版本，当前填写完整保留。'} description="此操作不写入后台。核对期间版本再次变化时，不会替换当前填写；取消也保留原文字。" /></>,
      okText: replaceForm ? '已核对，替换表单并载入最新资料' : '已核对新版本，保留当前填写', cancelText: '保留当前填写，不载入',
      onOk: async () => {
        if (editorSession.current !== session) throw new Error('当前编辑资料已经切换，请重新核对。');
        setReviewing(true);
        try {
          const accepted = await loadReviewedLibrary(original, proposal, read);
          if (editorSession.current !== session) throw new Error('读取期间当前编辑资料已切换，原填写未替换。');
          if (accepted.replace_form && accepted.basis.item) { form.resetFields(); form.setFieldsValue(accepted.basis.item); setEdit(accepted.basis.item); }
          setReviewBasis(accepted.basis);
          message.success(accepted.replace_form ? '已载入最新资料，请重新填写本次修改。' : '已核对当前公司版本，你的填写已保留。');
        } catch (error) { report(error); throw error; } finally { setReviewing(false); }
      },
    });
  }
  return <><div className="page-heading"><div><h2>企业资料库</h2><p>当前公司可引用的资料、方案片段与历史参考。</p></div><Button type="primary" icon={<PlusOutlined />} onClick={create} disabled={busy || user.role === 'viewer'}>补录合成资料</Button></div><Row gutter={16} className="summary-row">{[{ label: '当前公司资料', value: items.length }, { label: '已确认可引用', value: items.filter(usable).length }, { label: '待确认', value: items.filter(item => item.status === 'pending').length }, { label: '仅作历史参考', value: items.filter(item => item.type === 'history').length }].map(item => <Col span={6} key={item.label}><Card><Statistic title={item.label} value={item.value} /></Card></Col>)}</Row><Alert className="page-notice" type="info" showIcon message="资料新增、修改、确认与证据挂接已经联通" description="当前仅使用合成文字资料；真实附件槽位、人员敏感字段、授权链、批量导入和审核流程还未实现。资料变化会使旧项目检查过期。" /><div className="library-layout"><Card size="small" className="library-category"><button className={category === 'all' ? 'active' : ''} onClick={() => setCategory('all')}>全部资料 <span>{items.length}</span></button>{types.map(item => <button key={item.value} className={category === item.value ? 'active' : ''} onClick={() => setCategory(item.value)}>{item.label}<span>{items.filter(value => value.type === item.value).length}</span></button>)}<button className={category === 'sla_templates' ? 'active' : ''} onClick={() => setCategory('sla_templates')}>服务承诺模板<span>{templates.length}</span></button></Card>{category === 'sla_templates' ? <Card className="library-table"><SlaTemplatesPage items={templates} revision={templatesRevision} read={readTemplates} globalSearch={globalSearch} user={user} busy={busy} mutate={mutate} report={report} /></Card> : <Card className="library-table" title={category === 'all' ? '全部资料' : typeName(category)} extra={<Input placeholder="搜索资料名称" aria-label="资料名称筛选" prefix={<SearchOutlined />} value={search} onChange={e => setSearch(e.target.value)} />}><Table rowKey="id" size="small" pagination={{ pageSize: 10 }} dataSource={items.filter(item => (category === 'all' || item.type === category) && item.name.includes(search) && item.name.includes(globalSearch))} columns={[{ title: '资料名称', dataIndex: 'name', render: (value, item) => <a onClick={() => editing(item)}>{value}</a> }, { title: '类别', dataIndex: 'type', render: typeName }, { title: '有效期', dataIndex: 'valid_until', render: value => value || '未登记到期日' }, { title: '确认状态', dataIndex: 'status', render: value => <Tag color={value === 'confirmed' ? 'green' : 'orange'}>{value === 'confirmed' ? '已确认' : value === 'rejected' ? '已排除' : '待确认'}</Tag> }, { title: '可引用状态', render: (_, item) => <Tag color={usable(item) ? 'green' : 'default'}>{usable(item) ? '可作证据（仍需核对项目截止）' : item.type === 'history' ? '只能参考' : '不可引用'}</Tag> }, { title: '操作', render: (_, item) => <Button type="link" onClick={() => editing(item)}>{user.role === 'viewer' ? '查看' : '核对 / 修改'}</Button> }]} /></Card>}</div><Modal title={edit ? '资料详情与核对' : '补录合成资料'} width={720} open={open} onCancel={() => { if (!latest.current.busy) { editorSession.current++; setOpen(false); } }} onOk={save} okText="保存资料" cancelText="取消" confirmLoading={busy} okButtonProps={{ disabled: user.role === 'viewer' || busy || reviewing || !!reviewProblem }}>{reviewProblem && <Alert className="page-notice" type="warning" showIcon message="资料库发生变化，当前填写仍保留" description={reviewProblem} action={<Button disabled={busy || reviewing} loading={reviewing} onClick={reviewLatest}>核对资料与最新版本</Button>} />}<Form form={form} layout="vertical" disabled={user.role === 'viewer' || busy || reviewing}><Form.Item name="name" label="资料名称" rules={[{ required: true, whitespace: true }]}><Input /></Form.Item><Form.Item name="type" label="资料类别" rules={[{ required: true }]}><Select options={types} /></Form.Item><Form.Item name="content" label="资料内容" rules={[{ required: true, whitespace: true }]}><Input.TextArea rows={6} placeholder="请使用合成测试资料，不填真实客户或人员原件" /></Form.Item><Row gutter={16}><Col span={12}><Form.Item name="valid_until" label="有效期至"><Input type="date" /></Form.Item></Col><Col span={12}><Form.Item name="status" label="人工核对状态"><Select options={[{ value: 'pending', label: '待确认' }, { value: 'confirmed', label: '已逐项核对并确认' }]} /></Form.Item></Col></Row><Form.Item name="reason" label="本次核对说明"><Input.TextArea rows={2} placeholder="修改已经确认的资料后若再次确认，请说明本次核对依据；否则先保存为待确认" /></Form.Item></Form><Alert type="warning" message="只有已确认资料可挂为证据；历史标书即使确认也只能作参考" showIcon /></Modal></>;
}

export function JobsPage({ jobs, openProject }: { jobs: Job[]; openProject: (id: string) => void }) {
  const [status, setStatus] = useState('completed');
  const filtered = jobs.filter(item => item.status === status);
  return <><div className="page-heading"><div><h2>后台任务中心</h2><p>查看当前公司的实际解析与生成任务。</p></div></div><Alert showIcon type="info" className="page-notice" message="当前为同步执行任务" description="后台真实记录执行结果和失败原因。排队、断点恢复、重试与取消尚未实现，因此不会提供假操作按钮。" /><Card><Tabs activeKey={status} onChange={setStatus} items={[{ key: 'running', label: '运行中' }, { key: 'queued', label: '排队' }, { key: 'failed', label: `失败 ${jobs.filter(item => item.status === 'failed').length}` }, { key: 'completed', label: `已完成 ${jobs.filter(item => item.status === 'completed').length}` }]} /><Table rowKey="id" size="small" dataSource={filtered} columns={[{ title: '任务类型', dataIndex: 'type', render: value => value === 'parse' ? '招标文件解析' : value === 'generate' ? '章节候选生成' : value }, { title: '执行情况', dataIndex: 'message' }, { title: '进度', width: 170, render: (_, item) => <Progress percent={item.progress} size="small" status={item.status === 'failed' ? 'exception' : undefined} /> }, { title: '开始时间', dataIndex: 'created_at', render: formatTime }, { title: '失败原因', render: (_, item) => item.error?.message ?? '—' }, { title: '操作', render: (_, item) => <Button type="link" onClick={() => openProject(item.project_id)}>前往项目</Button> }]} /></Card></>;
}

export function PendingPage({ title, detail }: { title: string; detail: string }) {
  return <><div className="page-heading"><div><h2>{title}</h2></div><Tag color="orange">尚未实现</Tag></div><Card><Empty description={detail} /><Alert className="page-notice" type="info" message="当前先贯通项目主流程，再按 ICG 示例补齐此页" showIcon /></Card></>;
}
