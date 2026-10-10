// 为什么有这个文件：保留 ICG 示例的导航和项目外壳，连接真实业务页签。
// 它解决什么问题：工作台、解析、矩阵、编辑、检查和导出使用同一套项目状态。
import { useEffect, useRef, useState } from 'react';
import { Alert, App as AntApp, Badge, Breadcrumb, Button, Card, Col, Drawer, Empty, Form, Input, Modal, Progress, Row, Select, Space, Spin, Statistic, Table, Tabs, Tag, Tooltip } from 'antd';
import { AppstoreOutlined, ApartmentOutlined, BellOutlined, BookOutlined, CheckSquareOutlined, ClockCircleOutlined, DatabaseOutlined, DownOutlined, FileTextOutlined, MenuFoldOutlined, MenuUnfoldOutlined, PlusOutlined, SearchOutlined, SettingOutlined, TeamOutlined } from '@ant-design/icons';
import { ApiError, download, request } from './api';
import { deadlineForApi, projectFields } from './project-form';
import { ProjectContext, companyName, formatTime, roleName, volumeName } from './context';
import type { Account, Evidence, Job, Project, Workspace } from './types';
import { ChecksPage, ExportPage, FactsPage, MatrixPage, OverviewPage, ParsePage, SettingsPage, TenderPage } from './ProjectPages';
import EditorPage from './EditorPage';
import { LibraryPage, JobsPage, PendingPage } from './SupportPages';

const tabs = [ ['overview', '概览'], ['tender', '招标文件'], ['parse', '解析结果'], ['matrix', '响应矩阵'], ['facts', '项目事实表'], ['editor', '编辑台'], ['manual', '人工处理队列'], ['checks', '合规检查'], ['export', '导出'], ['settings', '项目设置'] ];
const navigation = [ { id: 'workbench', name: '工作台', icon: <AppstoreOutlined /> }, { id: 'library', name: '企业资料库', icon: <DatabaseOutlined /> }, { id: 'knowledge', name: '知识库', icon: <BookOutlined /> }, { id: 'writing', name: '写作档案', icon: <FileTextOutlined /> }, { id: 'statistics', name: '写作观察统计', icon: <ApartmentOutlined /> }, { id: 'admin', name: '管理后台', icon: <SettingOutlined /> } ];

export default function App() {
  const { message, modal } = AntApp.useApp();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountId, setAccountId] = useState('alpha-manager');
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<Account | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [library, setLibrary] = useState<Evidence[]>([]);
  const [libraryRevision, setLibraryRevision] = useState(1);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [nav, setNav] = useState('workbench');
  const [tab, setTab] = useState('overview');
  const [expanded, setExpanded] = useState(false);
  const [search, setSearch] = useState('');
  const [taskDrawer, setTaskDrawer] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [editorDirty, setEditorDirty] = useState(false);
  const [createForm] = Form.useForm();
  const epoch = useRef(0);
  const projectId = useRef<string | null>(null);

  function report(error: unknown) {
    if (error instanceof ApiError) {
      message.error(error.message);
      if (error.status === 401) { epoch.current++; setToken(null); setUser(null); setWorkspace(null); projectId.current = null; }
    } else message.error(error instanceof Error ? error.message : '操作失败，请稍后重试。');
  }
  useEffect(() => { request<{ accounts: Account[] }>('/api/demo/accounts', null).then(data => setAccounts(data.accounts)).catch(report); }, []);
  async function refreshGlobal(currentToken = token) {
    if (!currentToken) return;
    const start = epoch.current;
    const results = await Promise.all([
      request<{ projects: Project[] }>('/api/projects', currentToken),
      request<{ items: Evidence[]; revision: number }>('/api/v1/library', currentToken),
      request<{ jobs: Job[] }>('/api/v1/jobs', currentToken),
    ]);
    if (start !== epoch.current) return;
    setProjects(results[0].projects); setLibrary(results[1].items); setLibraryRevision(results[1].revision); setJobs(results[2].jobs);
  }
  async function login() {
    setBusy(true);
    try {
      const data = await request<{ access_token: string; user: Account }>('/api/demo/login', null, 'POST', { account_id: accountId });
      epoch.current++; setToken(data.access_token); setUser(data.user); setWorkspace(null); projectId.current = null; setNav('workbench');
      await refreshGlobal(data.access_token);
    } catch (error) { report(error); } finally { setBusy(false); }
  }
  function guarded(action: () => void) {
    if (!editorDirty) { action(); return; }
    modal.confirm({ title: '当前章节还有未提交的修改', content: '离开页面会丢失尚未保存的文字。已保存的草稿可以返回恢复。', okText: '离开页面', cancelText: '继续编辑', onOk: () => { setEditorDirty(false); action(); } });
  }
  async function openProject(id: string, nextTab = 'overview') {
    const start = ++epoch.current; projectId.current = id; setLoading(true); setNav('workbench'); setTab(nextTab);
    try { const data = await request<Workspace>(`/api/v1/projects/${id}/workspace`, token); if (start === epoch.current) setWorkspace(data); }
    catch (error) { if (start === epoch.current) { setWorkspace(null); report(error); } } finally { if (start === epoch.current) setLoading(false); }
  }
  async function reload() {
    const id = projectId.current; const start = epoch.current;
    if (!id) return;
    const data = await request<Workspace>(`/api/v1/projects/${id}/workspace`, token);
    if (start !== epoch.current || id !== projectId.current) return;
    setWorkspace(data); await refreshGlobal();
  }
  async function mutate(path: string, method: string, body?: unknown) {
    setBusy(true);
    try { const result = await request(path, token, method, body, workspace?.revision); await reload(); return result; }
    catch (error) { report(error); if (error instanceof ApiError && (error.status === 409 || typeof error.details?.revision === 'number')) await reload().catch(report); throw error; }
    finally { setBusy(false); }
  }
  async function libraryMutate(path: string, method: string, body: unknown) {
    setBusy(true);
    try { const value = await request(path, token, method, body, libraryRevision); await refreshGlobal(); if (workspace) await reload(); return value; }
    catch (error) { report(error); if (error instanceof ApiError && error.status === 409) await refreshGlobal().catch(report); throw error; }
    finally { setBusy(false); }
  }
  async function createProject() {
    let values;
    try { values = await createForm.validateFields(); deadlineForApi(values.deadline); } catch (error) { if (error instanceof Error) report(error); return; }
    setBusy(true);
    let createdId: string | null = null;
    try {
      const created = await request<Project>('/api/projects', token, 'POST', { name: values.name }); createdId = created.id;
      const createdWorkspace = await request<Workspace>(`/api/v1/projects/${created.id}/workspace`, token);
      await request(`/api/v1/projects/${created.id}`, token, 'PATCH', projectFields({ tender_number: values.tender_number, sensitive: values.sensitive, deadline: values.deadline }), createdWorkspace.revision);
      setCreateOpen(false); createForm.resetFields(); await refreshGlobal(); await openProject(created.id, 'tender'); message.success('项目已建立，请上传招标文件。');
    } catch (error) { report(error); if (createdId) { setCreateOpen(false); await refreshGlobal(); await openProject(createdId, 'settings'); message.warning('项目已经建立，基本信息未全部保存，请在项目设置补齐。'); } } finally { setBusy(false); }
  }
  function goNav(value: string) { guarded(() => { epoch.current++; setNav(value); setWorkspace(null); projectId.current = null; }); }
  function navigate(value: string) { guarded(() => setTab(value)); }
  const filteredProjects = projects.filter(item => item.name.includes(search));
  const pending = workspace?.requirements.filter(item => item.status === 'pending').length ?? 0;
  const latest = workspace?.checks[workspace.checks.length - 1];
  const blockers = latest?.issues.filter(item => item.severity === 'blocker' || item.severity === 'blocking' || item.severity === 'error').length ?? 0;
  const coverage = workspace?.requirements.length ? Math.round(workspace.requirements.filter(item => item.response.trim()).length / workspace.requirements.length * 100) : 0;

  if (!token || !user) return <div className="login-screen"><section className="login-brand"><div className="brand-square">标</div><h1>智能投标系统</h1><p>让原文、证据和正文在同一处对齐</p><div className="login-foot">ICG · 本地联调环境<br />合成资料用于验证流程</div></section><section className="login-main"><Card className="login-card" title="欢迎进入工作台"><Alert type="info" message="演示登录" description="选择合成账号体验。项目资料只在当前公司可见；正式账号与密码登录尚未接入。" showIcon /><div className="form-label">体验账号</div><Select aria-label="演示账号" style={{ width: '100%' }} value={accountId} onChange={setAccountId} options={accounts.map(item => ({ value: item.id, label: `${item.name} · ${roleName(item.role)} · ${item.company_id === 'alpha' ? '华东数智' : '远山信息'}` }))} /><Button type="primary" block size="large" onClick={login} loading={busy} disabled={!accounts.length} style={{ marginTop: 24 }}>进入工作台</Button></Card></section></div>;

  return <div className={`app-shell ${expanded ? 'expanded' : ''}`}>
    <aside className="sidebar"><div className="sidebar-brand"><span className="brand-square">标</span>{expanded && <strong>智能投标系统</strong>}</div>{navigation.filter(item => item.id !== 'admin' || user.role === 'manager').map(item => <Tooltip placement="right" title={!expanded ? item.name : undefined} key={item.id}><button aria-label={item.name} className={`sidebar-item ${nav === item.id ? 'active' : ''}`} onClick={() => goNav(item.id)}>{item.icon}{expanded && <span>{item.name}</span>}</button></Tooltip>)}<Tooltip title="后台任务中心" placement="right"><button aria-label="后台任务中心" className={`sidebar-item ${nav === 'jobs' ? 'active' : ''}`} onClick={() => goNav('jobs')}><CheckSquareOutlined />{expanded && <span>后台任务</span>}</button></Tooltip></aside>
    <div className="main-shell"><header className="topbar"><Button type="text" icon={expanded ? <MenuFoldOutlined /> : <MenuUnfoldOutlined />} aria-label="收起或展开导航" onClick={() => setExpanded(!expanded)} /><Breadcrumb items={[{ title: <a onClick={() => goNav('workbench')}>工作台</a> }, ...(workspace ? [{ title: workspace.project.name }, { title: tabs.find(item => item[0] === tab)?.[1] }] : nav === 'workbench' ? [] : [{ title: navigation.find(item => item.id === nav)?.name ?? '后台任务' }])]} /><div className="topbar-right"><Tag color="orange" className="environment">示例数据 · 非真实业务</Tag><Input className="global-search" aria-label="搜索项目名称或资料名称" prefix={<SearchOutlined />} placeholder="搜索项目名称 / 资料名称" value={search} onChange={e => setSearch(e.target.value)} suffix={<kbd>Ctrl K</kbd>} onPressEnter={() => goNav('workbench')} /><Button type="text" icon={<Badge count={jobs.filter(item => item.status === 'running' || item.status === 'queued').length} size="small"><CheckSquareOutlined /></Badge>} aria-label="查看后台任务" onClick={() => setTaskDrawer(true)} /><Tooltip title="站内提醒尚未接入"><Button type="text" icon={<BellOutlined />} aria-label="提醒尚未接入" disabled /></Tooltip><span className="company-label"><TeamOutlined /> {companyName(user.company_id)}</span><span className="user-avatar">{user.name[0]}</span><span className="user-name">{user.name}<small> · {roleName(user.role)}</small></span><Button type="text" size="small" onClick={() => guarded(() => { epoch.current++; setToken(null); setUser(null); setWorkspace(null); setEditorDirty(false); projectId.current = null; })}>退出</Button></div></header>
      {workspace && nav === 'workbench' && <><section className={`project-header ${['matrix', 'editor', 'checks', 'export'].includes(tab) ? 'compact' : ''}`}><div className="project-heading"><div className="project-title"><strong title={workspace.project.name}>{workspace.project.name}</strong><Tag color={workspace.parse_confirmed ? 'blue' : 'orange'}>{workspace.parse_confirmed ? '编制中' : '待确认'}</Tag>{workspace.project.sensitive && <Tag color="volcano">敏感 · 强制本地</Tag>}</div><div className="volume-strip">{(['technical', 'business'] as const).map(volume => <div key={volume}>{volumeName(volume)}<span>{workspace.chapters.filter(chapter => chapter.volume === volume).length} 章</span><Tag color="blue">{workspace.chapters.filter(chapter => chapter.volume === volume).every(chapter => chapter.content.trim()) ? '已提交正文' : '编制中'}</Tag></div>)}</div></div><div className="project-meta"><span>招标编号 <b>{workspace.project.tender_number || '未填写'}</b></span><span>投标主体 {companyName(user.company_id)}</span><span>投标截止时间 <b>{formatTime(workspace.project.deadline)}</b></span><span>响应覆盖率 <b>{coverage}%</b></span><span>阻断 <b className="red">{blockers}</b></span><span>待确认 <b className="orange">{pending}</b></span></div><Tabs activeKey={tab} onChange={navigate} items={tabs.map(([key, label]) => ({ key, label: key === 'manual' ? <span>{label} <Badge count={pending} size="small" /></span> : label }))} /></section>
      <ProjectContext.Provider value={{ workspace, token, user, library, busy, mutate, reload, report, navigate }}><Spin spinning={loading}><main className={`project-content ${['parse', 'editor'].includes(tab) ? 'fullbleed' : ''}`}>
        {tab === 'overview' && <OverviewPage />}{tab === 'tender' && <TenderPage />}{tab === 'parse' && <ParsePage />}{tab === 'matrix' && <MatrixPage />}{tab === 'facts' && <FactsPage />}{tab === 'editor' && <EditorPage key={workspace.project.id} onDirtyChange={setEditorDirty} />}{tab === 'checks' && <ChecksPage />}{tab === 'export' && <ExportPage />}{tab === 'settings' && <SettingsPage />}{tab === 'manual' && <PendingPage title="人工处理队列" detail="主链路目前可以在解析结果逐条确认、在检查列表定位问题。独立段落处理队列、指派和复查还未接通。" />}
      </main></Spin></ProjectContext.Provider></>}
      {(!workspace || nav !== 'workbench') && <Spin spinning={loading}><main className="workspace-content">{nav === 'workbench' && <><div className="page-heading"><div><h2>投标项目工作台</h2><p>先看风险，再看进度。所有项目均来自当前公司。</p></div><Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)} disabled={busy || user.role === 'viewer'}>新建项目</Button></div><Row gutter={16} className="summary-row">{[{ title: '投标项目', value: projects.length }, { title: '当前公司资料', value: library.length }, { title: '进行中的任务', value: jobs.filter(item => ['running', 'queued'].includes(item.status)).length }, { title: '失败任务', value: jobs.filter(item => item.status === 'failed').length }].map(item => <Col span={6} key={item.title}><Card><Statistic title={item.title} value={item.value} /></Card></Col>)}</Row><Card title="我参与的项目" extra={<Input placeholder="搜索项目名称" aria-label="项目名称筛选" prefix={<SearchOutlined />} value={search} onChange={e => setSearch(e.target.value)} style={{ width: 250 }} />}><Table size="small" rowKey="id" dataSource={filteredProjects} pagination={false} columns={[{ title: '项目名称', dataIndex: 'name', render: (name: string, item: Project) => <a onClick={() => openProject(item.id)}>{name}</a> }, { title: '招标编号', dataIndex: 'tender_number', render: (value: string) => value || '未填写' }, { title: '投标截止时间', dataIndex: 'deadline', render: formatTime }, { title: '操作', render: (_: unknown, item: Project) => <Button type="link" onClick={() => openProject(item.id)}>进入项目</Button> }]} /></Card><Alert className="page-notice" type="info" message="先贯通示例主链路" description="新建项目后，依次上传招标文件、确认解析、补响应与证据、编制两册章节、检查并下载内部稿。演示建议需要人工确认，不能直接作为正式承诺。" showIcon /></>}
        {nav === 'library' && <LibraryPage items={library.filter(item => item.name.includes(search))} user={user} busy={busy} mutate={libraryMutate} report={report} />}{nav === 'jobs' && <JobsPage jobs={jobs} openProject={id => openProject(id)} />}{['knowledge', 'writing', 'statistics', 'admin'].includes(nav) && <PendingPage title={navigation.find(item => item.id === nav)?.name ?? ''} detail="该页面的设计已登记，业务能力仍在后续任务中。这里尚未接通配置保存、知识检索或统计，不能以页面外壳替代实际功能。" />}
      </main></Spin>}
    </div>
    <Modal title="新建投标项目" open={createOpen} onCancel={() => setCreateOpen(false)} onOk={createProject} confirmLoading={busy} okText="创建并上传招标文件" width={600}><Alert type="info" showIcon message="技术、商务两册作为本期工作目标" description="资格材料按招标要求归册；报价由人在系统外处理。" /><Form form={createForm} layout="vertical" style={{ marginTop: 20 }} initialValues={{ sensitive: false }}><Form.Item name="name" label="项目名称" rules={[{ required: true, whitespace: true, message: '请填写项目名称' }, { max: 200 }]}><Input placeholder="请输入完整项目名称" /></Form.Item><Form.Item name="tender_number" label="招标编号"><Input /></Form.Item><Form.Item name="deadline" label="投标截止时间"><Input placeholder="2026-12-31 17:00（北京时间）" /></Form.Item><Form.Item name="sensitive" label="敏感项目"><Select options={[{ value: false, label: '普通项目' }, { value: true, label: '敏感 · 只能使用本地服务' }]} /></Form.Item></Form></Modal>
    <Drawer title="后台任务" open={taskDrawer} onClose={() => setTaskDrawer(false)} width={420} extra={<Button type="link" onClick={() => { setTaskDrawer(false); goNav('jobs'); }}>查看全部</Button>}><Alert type="info" message="当前任务同步执行，尚未提供断点恢复与取消" showIcon style={{ marginBottom: 16 }} />{jobs.length ? jobs.slice().reverse().map(job => <Card size="small" key={job.id} className="job-card"><Space><Tag color={job.status === 'failed' ? 'red' : 'green'}>{job.status === 'completed' ? '已完成' : job.status === 'failed' ? '失败' : job.status}</Tag><b>{job.type === 'parse' ? '招标解析' : job.type === 'generate' ? '章节生成' : job.type}</b></Space><p>{job.message}</p><Progress percent={job.progress} size="small" status={job.status === 'failed' ? 'exception' : undefined} /><Button type="link" onClick={() => { setTaskDrawer(false); guarded(() => { void openProject(job.project_id, job.type === 'parse' ? 'parse' : 'editor'); }); }}>前往页面</Button></Card>) : <Empty description="暂无后台任务" />}</Drawer>
  </div>;
}
