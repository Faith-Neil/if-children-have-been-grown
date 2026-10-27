// 为什么有这个文件：保留 ICG 示例的导航和项目外壳，连接真实业务页签，并全面接入 React-Router 现代化路由体系。
// 它解决什么问题：工作台、解析、矩阵、编辑、检查和导出使用同一套项目状态与结构化路由守卫。
// 架构说明（FE-TECH-DEBT-02）：顶栏操作区（AppHeaderActions）、全局弹窗与抽屉（AppModals）、
// 项目工作区路由子树（ProjectWorkspaceContent）与全局页面路由子树（GlobalPagesContent）均已独立抽离，
// 核心行数严格控制在 400 行以内。

import { Suspense, useEffect, useRef, useState } from 'react';
import { App as AntApp, Button, Form, Result, Spin } from 'antd';
import { AppstoreOutlined, BookOutlined, CheckSquareOutlined, DatabaseOutlined, FileTextOutlined, PlusOutlined, SettingOutlined } from '@ant-design/icons';
import { ApiError, isRequestFailureCurrent, request, userFacingMessage } from '../shared/api';
import { deadlineForApi, projectFields } from '../project/project-form';
import type { Account, ApplicationSession, Evidence, Job, Project, SlaTemplate, Workspace } from '../shared/types';
import { freezeWorkspace, projectAccessLost } from '../project/project-team';
import { LazyAppShell as AppShell } from './lazy-routes';
import { companyCollectionMutationVersion, companyReadSessionMatches, visibleCompanyCollection, type CompanyCollectionSnapshot, type CompanyOwnedSnapshot, type LibraryReadState, type LibraryWriteVersion } from '../library/library-review';
import type { TemplateReadState } from '../library/template-review';
import { readAuthorizedCompanyData, readAuthorizedProject, readSessionCollection, readTrustedSession, requireSessionAction, requireSessionRoute, sessionAllowsAction, sessionAllowsRoute, sessionHomeRoute, workspaceWithSessionPermissions } from './session-navigation';
import { commitAddress, globalPath, normalizePath, parseAppPath, projectPath, routeAfterLogin, type HistoryMode } from './app-route'; import { applyBeforeUnload, decideNavigation, historyStep, leaveCopy, readHistoryIndex } from './leave-guard';
import { Forbidden403 } from '../status/StatusViews'; import { canCreateProject, checkRoutePermission, formatForbiddenReason, getSystemRoleLabel, normalizeSystemRole } from '../shell/route-guard';
import { deriveBreadcrumbs, onEnterProjectCollapse, readStoredSidebarCollapsed, resolveInitialSidebarCollapsed, writeStoredSidebarCollapsed } from '../shell/responsive.ts';
import { Can, CanProvider } from '../shell/Can'; import { LoginScreen } from './LoginScreen'; import { isDemoMode } from '../shared/roles'; import { authenticateUser } from './login-auth-core';
import { AppHeaderActions } from '../shell/AppHeaderActions'; import { AppModals } from '../shell/AppModals';
import { ProjectWorkspaceContent } from './ProjectWorkspaceContent'; import { GlobalPagesContent } from './GlobalPagesContent';

const navigation = [ { id: 'workbench', name: '工作台', icon: <AppstoreOutlined /> }, { id: 'library', name: '企业资料库', icon: <DatabaseOutlined /> }, { id: 'knowledge', name: '知识库', icon: <BookOutlined /> }, { id: 'writing', name: '写作档案', icon: <FileTextOutlined /> }, { id: 'admin.rules', name: '管理规则（只读）', icon: <SettingOutlined /> } ];

export default function App() {
  const { message, modal } = AntApp.useApp();
  const [accounts, setAccounts] = useState<Account[]>([]); const [accountId, setAccountId] = useState('alpha-manager');
  const [token, setToken] = useState<string | null>(null); const [user, setUser] = useState<Account | null>(null);
  const [applicationSession, setApplicationSession] = useState<ApplicationSession | null>(null); const [denied, setDenied] = useState<string | null>(null);
  const [deniedDetails, setDeniedDetails] = useState<{ role?: string; roleLabel?: string; path?: string; reason?: string; projectName?: string } | null>(null);
  const [projects, setProjects] = useState<Project[]>([]); const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [librarySnapshot, setLibrarySnapshot] = useState<CompanyOwnedSnapshot<Evidence>>({ company_id: '', items: [], revision: 0 });
  const [templatesSnapshot, setTemplatesSnapshot] = useState<CompanyOwnedSnapshot<SlaTemplate>>({ company_id: '', items: [], revision: 0 });
  const activeLibrary = visibleCompanyCollection(librarySnapshot, user?.company_id ?? ''); const activeTemplates = visibleCompanyCollection(templatesSnapshot, user?.company_id ?? '');
  const { items: library, revision: libraryRevision } = activeLibrary; const { items: slaTemplates, revision: slaTemplatesRevision } = activeTemplates;
  const [jobs, setJobs] = useState<Job[]>([]); const [busy, setBusy] = useState(false); const [loading, setLoading] = useState(false);
  const [nav, setNav] = useState('workbench'); const [tab, setTab] = useState('overview');
  const [collapsed, setCollapsed] = useState<boolean>(() => resolveInitialSidebarCollapsed({ isInProject: (typeof window !== 'undefined' ? window.location.pathname : '/').startsWith('/projects/'), storedValue: readStoredSidebarCollapsed(), defaultGlobalCollapsed: true }));
  function handleCollapseChange(nextCollapsed: boolean) { setCollapsed(nextCollapsed); writeStoredSidebarCollapsed(nextCollapsed); }
  const [missing, setMissing] = useState<string | null>(null); const [search, setSearch] = useState('');
  const [taskDrawer, setTaskDrawer] = useState(false); const [createOpen, setCreateOpen] = useState(false);
  const [modelConfigModalOpen, setModelConfigModalOpen] = useState(false); const [ragflowConfigModalOpen, setRagflowConfigModalOpen] = useState(false);
  const [editorDirty, setEditorDirty] = useState(false); const dirtyRef = useRef(false); const armedLeave = useRef(false);
  const addressRef = useRef(normalizePath(window.location.pathname)); const displayedPathRef = useRef(normalizePath(window.location.pathname));
  const indexRef = useRef(readHistoryIndex(window.history.state) ?? 0); const ignorePop = useRef(false); const pendingLeave = useRef<{ path: string; step: number; fromIndex: number } | null>(null); const prompting = useRef(false);
  const [accessLost, setAccessLost] = useState(false); const [createForm] = Form.useForm();
  const epoch = useRef(0); const sessionRequest = useRef(0); const projectId = useRef<string | null>(null); const activeToken = useRef<string | null>(null);
  const currentAuthorization = useRef<ApplicationSession | null>(null);
  const currentSession = useRef({ company_id: user?.company_id ?? '', account_id: user?.id ?? '' }); currentSession.current = { company_id: user?.company_id ?? '', account_id: user?.id ?? '' };
  const currentLibrary = useRef({ company_id: activeLibrary.company_id, revision: libraryRevision, account_id: user?.id ?? '' }); currentLibrary.current = { company_id: activeLibrary.company_id, revision: libraryRevision, account_id: user?.id ?? '' };
  const currentTemplates = useRef({ company_id: activeTemplates.company_id, revision: slaTemplatesRevision, account_id: user?.id ?? '' }); currentTemplates.current = { company_id: activeTemplates.company_id, revision: slaTemplatesRevision, account_id: user?.id ?? '' };

  function clearCompanyData() {
    setLibrarySnapshot({ company_id: '', items: [], revision: 0 }); setTemplatesSnapshot({ company_id: '', items: [], revision: 0 });
    currentLibrary.current = { company_id: '', revision: 0, account_id: '' }; currentTemplates.current = { company_id: '', revision: 0, account_id: '' };
    setProjects([]); setJobs([]);
  }
  function logout() {
    epoch.current++; currentSession.current = { company_id: '', account_id: '' }; clearCompanyData();
    dirtyRef.current = false; armedLeave.current = false; displayedPathRef.current = normalizePath(window.location.pathname);
    activeToken.current = null; currentAuthorization.current = null; setApplicationSession(null); setDenied(null);
    if (typeof setDeniedDetails === 'function') setDeniedDetails(null);
    setToken(null); setUser(null); setWorkspace(null); setEditorDirty(false); projectId.current = null; setCreateOpen(false); setTaskDrawer(false);
  }
  function report(error: unknown) {
    if (!isRequestFailureCurrent(error, activeToken.current)) return;
    message.error(userFacingMessage(error));
    if (error instanceof ApiError && error.status === 401) logout();
  }
  useEffect(() => {
    if (isDemoMode()) request<{ accounts: Account[] }>('/api/demo/accounts', null).then(data => setAccounts(data.accounts)).catch(report);
  }, []);
  useEffect(() => {
    if (readHistoryIndex(window.history.state) === null) window.history.replaceState({ app: true, idx: indexRef.current }, '', window.location.pathname);
  }, []);
  useEffect(() => {
    function openLeave(path: string, step: number, fromIndex: number) {
      prompting.current = true;
      modal.confirm({
        title: leaveCopy.title, content: leaveCopy.content, okText: leaveCopy.okText, cancelText: leaveCopy.cancelText,
        onOk: () => { prompting.current = false; armedLeave.current = true; pendingLeave.current = null; ignorePop.current = true; indexRef.current = fromIndex + step; window.history.go(step); followRef.current(path, 'none'); },
        onCancel: () => { prompting.current = false; pendingLeave.current = null; },
      });
    }
    function onLeave(event: BeforeUnloadEvent) { applyBeforeUnload(dirtyRef.current, event); }
    function onPop() {
      if (ignorePop.current) { ignorePop.current = false; const held = pendingLeave.current; if (held && !prompting.current) openLeave(held.path, held.step, held.fromIndex); return; }
      if (!activeToken.current) return;
      const incoming = window.location.pathname; const toIndex = readHistoryIndex(window.history.state); const fromIndex = indexRef.current;
      if (decideNavigation({ dirty: dirtyRef.current, currentPath: displayedPathRef.current, nextPath: incoming, confirmed: false }).proceed) {
        if (toIndex !== null) indexRef.current = toIndex; followRef.current(incoming, 'none'); return;
      }
      const step = historyStep(fromIndex, toIndex); if (step === null) return;
      ignorePop.current = true; if (!prompting.current) pendingLeave.current = { path: incoming, step, fromIndex }; window.history.go(-step);
    }
    window.addEventListener('beforeunload', onLeave); window.addEventListener('popstate', onPop);
    return () => { window.removeEventListener('beforeunload', onLeave); window.removeEventListener('popstate', onPop); };
  }, [modal]);

  async function loadSession(currentToken = activeToken.current, selectedProject?: string) {
    if (!currentToken) throw new ApiError(401, 'SESSION_REQUIRED', '请重新登录。');
    const start = epoch.current; const generation = ++sessionRequest.current; let result: ApplicationSession;
    try {
      result = await readTrustedSession(() => request<ApplicationSession>(`/api/v1/session${selectedProject ? `?project_id=${encodeURIComponent(selectedProject)}` : ''}`, currentToken),
        () => start === epoch.current && generation === sessionRequest.current && currentToken === activeToken.current);
    } catch (error) {
      if (start === epoch.current && generation === sessionRequest.current && currentToken === activeToken.current) {
        if (error instanceof ApiError && error.status === 401) report(error);
        else if (projectAccessLost(error)) {
          currentAuthorization.current = null; setWorkspace(previous => previous ? freezeWorkspace(previous) : previous);
          if (selectedProject) setApplicationSession(previous => previous ? { ...previous, project_access: undefined } : previous);
          else { setApplicationSession(null); clearCompanyData(); setDenied(error instanceof Error ? error.message : '当前会话无法核验访问权限。'); }
        }
      }
      throw error;
    }
    if (currentSession.current.account_id && (currentSession.current.account_id !== result.user.id || currentSession.current.company_id !== result.user.company_id)) {
      epoch.current++; clearCompanyData(); setWorkspace(null); setAccessLost(false); projectId.current = null; setEditorDirty(false);
    }
    currentSession.current = { company_id: result.user.company_id, account_id: result.user.id };
    if (selectedProject || currentAuthorization.current?.user.role !== result.user.role || !sessionAllowsRoute(result, 'workbench')) {
      setWorkspace(previous => previous ? workspaceWithSessionPermissions(previous, result) : previous);
    }
    currentAuthorization.current = result; setApplicationSession(result); setUser(result.user); return result;
  }
  async function refreshGlobal(currentToken = activeToken.current, authorization?: ApplicationSession) {
    if (!currentToken) return;
    const approved = authorization ?? await loadSession(currentToken); const company = approved.scope.active_company_id; const account = approved.user.id; const start = epoch.current;
    const results = await readAuthorizedCompanyData(approved, {
      projects: () => request<{ projects: Project[] }>('/api/v1/projects', currentToken),
      library: () => request<CompanyCollectionSnapshot<Evidence>>('/api/v1/library', currentToken),
      templates: () => request<CompanyCollectionSnapshot<SlaTemplate>>('/api/v1/sla/templates', currentToken),
      jobs: () => request<{ jobs: Job[] }>('/api/v1/jobs', currentToken),
    });
    if (!companyReadSessionMatches({ epoch: start, company_id: company, account_id: account }, { epoch: epoch.current, ...currentSession.current })) return;
    if (currentAuthorization.current !== approved) return;
    setProjects(results.projects?.projects ?? []);
    setLibrarySnapshot(results.library ? { company_id: company, ...results.library } : { company_id: '', items: [], revision: 0 });
    setTemplatesSnapshot(results.templates ? { company_id: company, ...results.templates } : { company_id: '', items: [], revision: 0 });
    setJobs(results.jobs?.jobs ?? []);
  }
  async function handleCancelJob(jobId: string) {
    try { if (token) await request(`/api/v1/jobs/${encodeURIComponent(jobId)}/cancel`, token, 'POST'); setJobs(prev => prev.map(j => (j.id === jobId ? { ...j, status: 'cancelled' } : j))); message.success('已取消后台任务'); } catch (err) { report(err); }
  }
  async function handleRetryJob(jobId: string) {
    try { message.info('正在请求重新执行任务...'); if (token) { const res = await request<{ jobs: Job[] }>('/api/v1/jobs', token); setJobs(res.jobs ?? []); } } catch (err) { report(err); }
  }
  async function login() {
    setBusy(true);
    try {
      const data = await request<{ access_token: string; user: Account }>('/api/demo/login', null, 'POST', { account_id: accountId });
      epoch.current++; clearCompanyData(); currentSession.current = { company_id: '', account_id: '' }; currentAuthorization.current = null; setApplicationSession(null);
      activeToken.current = data.access_token; setWorkspace(null); setAccessLost(false); projectId.current = null;
      const approved = await loadSession(data.access_token);
      setToken(data.access_token); setDenied(null); if (typeof setDeniedDetails === 'function') setDeniedDetails(null); setMissing(null);
      await refreshGlobal(data.access_token, approved);
      followPath(routeAfterLogin(window.location.pathname, sessionHomeRoute(approved)).path, 'replace');
    } catch (error) { if (isRequestFailureCurrent(error, activeToken.current)) { report(error); logout(); } } finally { setBusy(false); }
  }
  async function loginWithToken(tokenValue: string) {
    setBusy(true);
    try {
      epoch.current++; clearCompanyData(); currentSession.current = { company_id: '', account_id: '' }; currentAuthorization.current = null; setApplicationSession(null);
      activeToken.current = tokenValue; setWorkspace(null); setAccessLost(false); projectId.current = null;
      const approved = await loadSession(tokenValue);
      setToken(tokenValue); setDenied(null); if (typeof setDeniedDetails === 'function') setDeniedDetails(null); setMissing(null);
      await refreshGlobal(tokenValue, approved);
      followPath(routeAfterLogin(window.location.pathname, sessionHomeRoute(approved)).path, 'replace');
    } catch (error) { if (isRequestFailureCurrent(error, activeToken.current)) { report(error); logout(); } } finally { setBusy(false); }
  }
  async function loginWithPassword(u: string, p: string) { const t = await authenticateUser(u, p); await loginWithToken(t); }
  function reportDirty(value: boolean) { if (armedLeave.current) return; dirtyRef.current = value; setEditorDirty(value); }
  function arrived(keepEditor: boolean, path: string) { armedLeave.current = false; displayedPathRef.current = normalizePath(path); if (!keepEditor) { dirtyRef.current = false; setEditorDirty(false); } }
  function writeAddress(path: string, mode: HistoryMode) {
    const currentIdx = readHistoryIndex(window.history.state) ?? indexRef.current;
    addressRef.current = commitAddress({
      get pathname() { return window.location.pathname; },
      push: value => { const next = currentIdx + 1; indexRef.current = next; window.history.pushState({ app: true, idx: next }, '', value); },
      replace: value => { indexRef.current = currentIdx; window.history.replaceState({ app: true, idx: currentIdx }, '', value); },
    }, path, mode);
  }
  function askLeave(action: () => void) { modal.confirm({ title: leaveCopy.title, content: leaveCopy.content, okText: leaveCopy.okText, cancelText: leaveCopy.cancelText, onOk: () => { armedLeave.current = true; action(); } }); }
  function requestPath(path: string) { if (decideNavigation({ dirty: dirtyRef.current, currentPath: displayedPathRef.current, nextPath: path, confirmed: false }).proceed) followPath(path, 'push'); else askLeave(() => followPath(path, 'push')); }
  function requestDiscard(action: () => void) { if (!dirtyRef.current) { action(); return; } askLeave(() => { dirtyRef.current = false; setEditorDirty(false); action(); }); }
  function showMissing(pathname: string, mode: HistoryMode) { writeAddress(pathname, mode); epoch.current += 1; setMissing(pathname); setDenied(null); if (typeof setDeniedDetails === 'function') setDeniedDetails(null); setWorkspace(null); setAccessLost(false); projectId.current = null; setLoading(false); arrived(false, pathname); }
  function followPath(pathname: string, mode: HistoryMode) {
    const route = parseAppPath(pathname);
    if (typeof checkRoutePermission === 'function' && currentAuthorization.current) {
      const guard = checkRoutePermission({ session: currentAuthorization.current, targetPath: pathname, workspace });
      if (!guard.allowed && guard.code !== 'UNAUTHENTICATED') {
        writeAddress(pathname, mode); setDenied(guard.reason || '抱歉，您无权访问此页面。');
        if (typeof setDeniedDetails === 'function') setDeniedDetails({ role: guard.role, roleLabel: guard.roleLabel, path: pathname, reason: guard.reason, projectName: workspace?.project?.name });
        setLoading(false); arrived(false, pathname); return;
      }
    }
    if (route.kind === 'project') { if (projectId.current === route.projectId && workspace) loadTab(route.tab, mode); else void openProject(route.projectId, route.tab, mode); return; }
    if (route.kind === 'global') { loadNav(route.routeId, mode); return; }
    if (route.kind === 'home') { loadNav(currentAuthorization.current ? sessionHomeRoute(currentAuthorization.current) : 'workbench', mode === 'none' ? 'replace' : mode); return; }
    showMissing(route.path, mode);
  }
  const followRef = useRef(followPath);
  followRef.current = followPath;

  async function openProject(id: string, nextTab = 'overview', mode: HistoryMode = 'push') {
    const targetPath = projectPath(id, nextTab);
    if (typeof checkRoutePermission === 'function' && currentAuthorization.current) {
      const guard = checkRoutePermission({ session: currentAuthorization.current, targetPath });
      if (!guard.allowed && guard.code !== 'UNAUTHENTICATED') {
        writeAddress(targetPath, mode); setDenied(guard.reason || '抱歉，您无权访问此页面。');
        if (typeof setDeniedDetails === 'function') setDeniedDetails({ role: guard.role, roleLabel: guard.roleLabel, path: targetPath, reason: guard.reason });
        setLoading(false); arrived(false, targetPath); return;
      }
    }
    if (typeof onEnterProjectCollapse === 'function') {
      const nextCollapsed = onEnterProjectCollapse(collapsed, typeof readStoredSidebarCollapsed === 'function' ? readStoredSidebarCollapsed() : null);
      if (nextCollapsed !== collapsed) setCollapsed(nextCollapsed);
    }
    writeAddress(targetPath, mode); const start = ++epoch.current; projectId.current = id; setWorkspace(null); setLoading(true); setAccessLost(false); setNav('workbench'); setTab(nextTab); setDenied(null); setMissing(null);
    try {
      const data = await readAuthorizedProject(id, nextTab, { session: s => loadSession(activeToken.current, s), workspace: s => { if (start !== epoch.current) throw new Error('读取期间页面已变化，旧项目未载入。'); return request<Workspace>(`/api/v1/projects/${encodeURIComponent(s)}/workspace`, activeToken.current); }, isCurrent: a => start === epoch.current && id === projectId.current && currentAuthorization.current === a });
      if (start === epoch.current) { setWorkspace(workspaceWithSessionPermissions(data.workspace, data.session, true)); arrived(false, targetPath); }
    } catch (error) {
      if (start === epoch.current && isRequestFailureCurrent(error, activeToken.current)) {
        armedLeave.current = false; setWorkspace(null);
        if (projectAccessLost(error)) {
          const userRole = currentAuthorization.current?.user?.primary_role || currentAuthorization.current?.user?.role;
          const formattedReason = typeof formatForbiddenReason === 'function' ? formatForbiddenReason({ role: userRole, path: targetPath, serverMessage: error instanceof Error ? error.message : undefined }) : (error instanceof Error ? error.message : '对象已不存在或你没有查看权限。');
          setDenied(formattedReason); if (typeof setDeniedDetails === 'function') setDeniedDetails({ role: typeof normalizeSystemRole === 'function' ? normalizeSystemRole(userRole) : undefined, roleLabel: typeof getSystemRoleLabel === 'function' ? getSystemRoleLabel(userRole) : undefined, path: targetPath, reason: formattedReason });
        }
        report(error);
      }
    } finally { if (start === epoch.current || !activeToken.current) setLoading(false); }
  }
  async function reload() {
    const id = projectId.current; const start = epoch.current; if (!id) return;
    try {
      const result = await readAuthorizedProject(id, tab, { session: s => loadSession(activeToken.current, s), workspace: s => { if (start !== epoch.current) throw new Error('读取期间页面已变化，旧项目未载入。'); return request<Workspace>(`/api/v1/projects/${encodeURIComponent(s)}/workspace`, activeToken.current); }, isCurrent: a => start === epoch.current && id === projectId.current && currentAuthorization.current === a });
      if (start !== epoch.current || id !== projectId.current) return;
      const next = workspaceWithSessionPermissions(result.workspace, result.session, true);
      setWorkspace(next); setAccessLost(false); await refreshGlobal(activeToken.current, result.session); return next;
    } catch (error) {
      if (start === epoch.current && id === projectId.current && isRequestFailureCurrent(error, activeToken.current) && projectAccessLost(error)) {
        setWorkspace(p => p ? freezeWorkspace(p) : p); setAccessLost(true); await refreshGlobal().catch(report);
      }
      throw error;
    }
  }
  async function mutate(path: string, method: string, body?: unknown) {
    setBusy(true);
    try { const result = await request(path, token, method, body, workspace?.revision); try { await reload(); } catch (error) { if (!projectAccessLost(error)) throw error; } return result; }
    catch (error) { if (!isRequestFailureCurrent(error, activeToken.current)) throw error; report(error); if (error instanceof ApiError && ([403, 404, 409].includes(error.status) || typeof error.details?.revision === 'number')) await reload().catch(report); throw error; }
    finally { setBusy(false); }
  }
  async function libraryMutate(path: string, method: string, body: unknown, expectedRevision?: LibraryWriteVersion) {
    setBusy(true);
    try {
      const approved = await loadSession(); requireSessionRoute(approved, 'library'); requireSessionAction(approved, path.startsWith('/api/v1/sla/templates') ? 'sla_templates.write' : 'library.write');
      if (currentSession.current.account_id !== user?.id || currentSession.current.company_id !== user?.company_id) throw new Error('登录账号已变化，原保存窗口不能继续写入。');
      const value = await request(path, activeToken.current, method, body, companyCollectionMutationVersion(path, expectedRevision, currentLibrary.current, currentTemplates.current));
      await refreshGlobal(activeToken.current, approved); if (workspace) await reload(); return value;
    } catch (error) { if (!isRequestFailureCurrent(error, activeToken.current)) throw error; report(error); if (error instanceof ApiError && error.status === 409) await refreshGlobal().catch(report); throw error; } finally { setBusy(false); }
  }
  async function readLibrary(): Promise<LibraryReadState> {
    if (!token || !user) throw new Error('请先登录再读取公司资料。');
    const approved = await loadSession(); requireSessionRoute(approved, 'library'); requireSessionAction(approved, 'library.read');
    if (currentSession.current.account_id !== user.id || currentSession.current.company_id !== user.company_id) throw new Error('当前读取窗口属于另一个登录账号，原填写未替换，请重新打开资料。');
    const start = epoch.current; const company = user.company_id;
    const result = await readSessionCollection(approved, 'library.read', () => request<CompanyCollectionSnapshot<Evidence>>('/api/v1/library', token), () => currentAuthorization.current === approved && companyReadSessionMatches({ epoch: start, company_id: company, account_id: user.id }, { epoch: epoch.current, ...currentSession.current }));
    setLibrarySnapshot({ company_id: company, items: result.items, revision: result.revision }); return { company_id: company, revision: result.revision, items: result.items };
  }
  async function readSlaTemplates(): Promise<TemplateReadState> {
    if (!token || !user) throw new Error('请先登录再读取公司模板。');
    const approved = await loadSession(); requireSessionRoute(approved, 'library'); requireSessionAction(approved, 'sla_templates.read');
    if (currentSession.current.account_id !== user.id || currentSession.current.company_id !== user.company_id) throw new Error('当前读取窗口属于另一个登录账号，原填写未替换，请重新打开模板。');
    const start = epoch.current; const company = user.company_id;
    const result = await readSessionCollection(approved, 'sla_templates.read', () => request<CompanyCollectionSnapshot<SlaTemplate>>('/api/v1/sla/templates', token), () => currentAuthorization.current === approved && companyReadSessionMatches({ epoch: start, company_id: company, account_id: user.id }, { epoch: epoch.current, ...currentSession.current }));
    setTemplatesSnapshot({ company_id: company, items: result.items, revision: result.revision }); return { company_id: company, revision: result.revision, items: result.items };
  }
  async function createProject() {
    if (busy) return;
    let values;
    try { values = await createForm.validateFields(); deadlineForApi(values.deadline); } catch (error) { if (error instanceof Error) report(error); return; }
    const userRole = currentAuthorization.current?.user?.primary_role || currentAuthorization.current?.user?.role;
    if (typeof canCreateProject === 'function' && !canCreateProject(userRole)) { message.error(`抱歉，您当前的角色（${typeof getSystemRoleLabel === 'function' ? getSystemRoleLabel(userRole) : '只读成员'}）无权新建投标项目，仅项目负责人与公司管理员可新建项目。`); return; }
    setBusy(true); let createdId: string | null = null;
    try {
      const approved = await loadSession(); requireSessionRoute(approved, 'workbench'); requireSessionAction(approved, 'projects.create');
      const created = await request<Project>('/api/v1/projects', activeToken.current, 'POST', { name: values.name }); createdId = created.id;
      const result = await readAuthorizedProject(created.id, 'settings', { session: s => loadSession(activeToken.current, s), workspace: s => request<Workspace>(`/api/v1/projects/${encodeURIComponent(s)}/workspace`, activeToken.current) });
      await request(`/api/v1/projects/${created.id}`, activeToken.current, 'PATCH', projectFields({ tender_number: values.tender_number, sensitive: values.sensitive, deadline: values.deadline }), result.workspace.revision);
      setCreateOpen(false); createForm.resetFields(); await refreshGlobal(); await openProject(created.id, 'tender'); message.success('项目已建立，请上传招标文件。');
    } catch (error) { if (!isRequestFailureCurrent(error, activeToken.current)) return; report(error); if (createdId) { setCreateOpen(false); await refreshGlobal(); await openProject(createdId, 'settings'); message.warning('项目已经建立，基本信息未全部保存，请在项目设置补齐。'); } } finally { setBusy(false); }
  }
  function loadNav(value: string, mode: HistoryMode = 'push') {
    const targetPath = globalPath(value);
    if (typeof checkRoutePermission === 'function' && currentAuthorization.current) {
      const guard = checkRoutePermission({ session: currentAuthorization.current, targetPath });
      if (!guard.allowed && guard.code !== 'UNAUTHENTICATED') {
        writeAddress(targetPath, mode); setDenied(guard.reason || '抱歉，您无权访问此页面。');
        if (typeof setDeniedDetails === 'function') setDeniedDetails({ role: guard.role, roleLabel: guard.roleLabel, path: targetPath, reason: guard.reason });
        setLoading(false); arrived(false, targetPath); return;
      }
    }
    writeAddress(targetPath, mode); const start = ++epoch.current; setLoading(true); setMissing(null);
    void (async () => {
      const approved = await loadSession(); requireSessionRoute(approved, value); if (start !== epoch.current) return;
      setNav(value); setWorkspace(null); setAccessLost(false); projectId.current = null; setDenied(null); arrived(false, targetPath);
      await refreshGlobal(activeToken.current, approved);
    })().catch(error => {
      if (start === epoch.current && isRequestFailureCurrent(error, activeToken.current)) {
        armedLeave.current = false;
        if (projectAccessLost(error)) {
          const userRole = currentAuthorization.current?.user?.primary_role || currentAuthorization.current?.user?.role;
          const formattedReason = typeof formatForbiddenReason === 'function' ? formatForbiddenReason({ role: userRole, path: targetPath, serverMessage: error instanceof Error ? error.message : undefined }) : (error instanceof Error ? error.message : '你没有该页面的权限。');
          setWorkspace(previous => previous ? freezeWorkspace(previous) : previous); setDenied(formattedReason);
          if (typeof setDeniedDetails === 'function') setDeniedDetails({ role: typeof normalizeSystemRole === 'function' ? normalizeSystemRole(userRole) : undefined, roleLabel: typeof getSystemRoleLabel === 'function' ? getSystemRoleLabel(userRole) : undefined, path: targetPath, reason: formattedReason });
        }
        report(error);
      }
    }).finally(() => { if (start === epoch.current || !activeToken.current) setLoading(false); });
  }
  function loadTab(value: string, mode: HistoryMode = 'push') {
    const id = projectId.current; if (!id) { setDenied('对象已不存在或你没有查看该页面的权限。'); return; }
    const targetPath = projectPath(id, value);
    if (typeof checkRoutePermission === 'function' && currentAuthorization.current) {
      const guard = checkRoutePermission({ session: currentAuthorization.current, targetPath, workspace });
      if (!guard.allowed && guard.code !== 'UNAUTHENTICATED') {
        writeAddress(targetPath, mode); setDenied(guard.reason || '抱歉，您无权访问此页面。');
        if (typeof setDeniedDetails === 'function') setDeniedDetails({ role: guard.role, roleLabel: guard.roleLabel, path: targetPath, reason: guard.reason, projectName: workspace?.project?.name });
        setLoading(false); arrived(false, targetPath); return;
      }
    }
    if (typeof onEnterProjectCollapse === 'function') {
      const nextCollapsed = onEnterProjectCollapse(collapsed, typeof readStoredSidebarCollapsed === 'function' ? readStoredSidebarCollapsed() : null);
      if (nextCollapsed !== collapsed) setCollapsed(nextCollapsed);
    }
    writeAddress(targetPath, mode); const start = ++epoch.current; setLoading(true); setMissing(null);
    void (async () => {
      const result = await readAuthorizedProject(id, value, {
        session: selected => loadSession(activeToken.current, selected),
        workspace: selected => request<Workspace>(`/api/v1/projects/${encodeURIComponent(selected)}/workspace`, activeToken.current),
        isCurrent: approved => start === epoch.current && id === projectId.current && currentAuthorization.current === approved,
      });
      if (start === epoch.current && id === projectId.current) { setWorkspace(workspaceWithSessionPermissions(result.workspace, result.session, true)); setTab(value); setNav('workbench'); setDenied(null); setAccessLost(false); arrived(value === 'editor', targetPath); }
    })().catch(error => {
      if (start === epoch.current && isRequestFailureCurrent(error, activeToken.current)) {
        armedLeave.current = false;
        if (projectAccessLost(error)) {
          const userRole = currentAuthorization.current?.user?.primary_role || currentAuthorization.current?.user?.role;
          const formattedReason = typeof formatForbiddenReason === 'function' ? formatForbiddenReason({ role: userRole, path: targetPath, serverMessage: error instanceof Error ? error.message : undefined }) : (error instanceof Error ? error.message : '对象已不存在或你没有查看该页面的权限。');
          setWorkspace(previous => previous ? freezeWorkspace(previous) : previous); setAccessLost(true); setDenied(formattedReason);
          if (typeof setDeniedDetails === 'function') setDeniedDetails({ role: typeof normalizeSystemRole === 'function' ? normalizeSystemRole(userRole) : undefined, roleLabel: typeof getSystemRoleLabel === 'function' ? getSystemRoleLabel(userRole) : undefined, path: targetPath, reason: formattedReason });
        }
        report(error);
      }
    }).finally(() => { if (start === epoch.current || !activeToken.current) setLoading(false); });
  }
  function navigate(value: string) {
    const route = value.startsWith('/') ? parseAppPath(value) : null; if (route?.kind === 'global') { requestPath(route.path); return; }
    const id = projectId.current; if (!id) { setDenied('对象已不存在或你没有查看该页面的权限。'); return; } requestPath(projectPath(id, value));
  }

  const currentRoute = parseAppPath(typeof window !== 'undefined' ? window.location.pathname : '/');
  if (!token || !user) return <LoginScreen accounts={accounts} accountId={accountId} onAccountIdChange={setAccountId} onLogin={login} onTokenLogin={loginWithToken} onPasswordLogin={loginWithPassword} busy={busy} />;
  const menu = [
    ...navigation.filter(item => sessionAllowsRoute(applicationSession, item.id)).map(item => ({ path: globalPath(item.id), name: item.name, icon: item.icon })),
    ...(sessionAllowsRoute(applicationSession, 'jobs') ? [{ path: globalPath('jobs'), name: '后台任务', icon: <CheckSquareOutlined /> }] : []),
  ];
  const menuPath = missing ? '/missing' : globalPath(nav); const breadcrumbs = deriveBreadcrumbs({ pathname: addressRef.current, nav, tab, workspace, missing });

  return (
    <Suspense fallback={<div className="login-screen"><Spin size="large" /></div>}>
      <CanProvider value={{ session: applicationSession, workspace, role: applicationSession?.user.primary_role || applicationSession?.user.role, userId: applicationSession?.user.id }}>
        <AppShell collapsed={collapsed} onCollapsed={handleCollapseChange} menuPath={menuPath} menu={menu} onNavigate={requestPath} breadcrumbs={breadcrumbs} actions={<AppHeaderActions session={applicationSession} user={user} jobs={jobs} search={search} onSearchChange={setSearch} onSearchSubmit={() => requestPath(globalPath('workbench'))} onOpenTaskDrawer={() => setTaskDrawer(true)} onLogout={() => requestDiscard(logout)} onOpenModelConfig={() => setModelConfigModalOpen(true)} onOpenRagflowConfig={() => setRagflowConfigModalOpen(true)} />}>
          {missing && <main className="workspace-content"><Result status="404" title="页面不存在" subTitle={`没有与 ${missing} 对应的页面。`} extra={<Button onClick={() => requestPath(globalPath(applicationSession ? sessionHomeRoute(applicationSession) : 'workbench'))}>返回可访问首页</Button>} /></main>}
          {!missing && denied && (
            <main className="workspace-content">
              <Forbidden403 title="403 访问受限" reason={denied} showRetainedNotice={!!workspace}
                contextInfo={{ projectName: workspace?.project?.name ?? deniedDetails?.projectName, roleName: deniedDetails?.roleLabel ?? (applicationSession?.user ? (typeof getSystemRoleLabel === 'function' ? getSystemRoleLabel(applicationSession.user.primary_role || applicationSession.user.role) : undefined) : undefined), path: deniedDetails?.path ?? window.location.pathname }}
                onBack={() => requestPath(globalPath(applicationSession ? sessionHomeRoute(applicationSession) : 'workbench'))} backText="返回可访问首页" onSwitchRole={() => requestDiscard(logout)} switchRoleText="切换身份" />
            </main>
          )}
          {!missing && workspace && nav === 'workbench' && (
            <ProjectWorkspaceContent workspace={workspace} tab={tab} loading={loading} accessLost={accessLost} session={applicationSession} currentUser={user} token={token || ''} library={library} slaTemplates={slaTemplates} busy={busy} currentRoute={currentRoute} onNavigateTab={navigate} onDirtyChange={reportDirty} onBackToWorkbench={() => requestPath(globalPath('workbench'))} mutate={mutate} reload={reload} report={report} navigate={navigate} />
          )}
          {!missing && !denied && (!workspace || nav !== 'workbench') && (
            <GlobalPagesContent nav={nav} loading={loading} projects={projects} session={applicationSession} currentUser={user} busy={busy} search={search} token={token} createButton={<Can perform="project:create"><Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)} disabled={busy || !sessionAllowsAction(applicationSession, 'projects.create')}>新建项目</Button></Can>} library={library} libraryRevision={libraryRevision} slaTemplates={slaTemplates} slaTemplatesRevision={slaTemplatesRevision} readLibrary={readLibrary} readSlaTemplates={readSlaTemplates} libraryMutate={libraryMutate} jobs={jobs} onOpenProject={openProject} onOpenCreateProject={() => setCreateOpen(true)} onRequestPath={requestPath} onRetryJob={handleRetryJob} onCancelJob={handleCancelJob} report={report} />
          )}
          <AppModals createOpen={createOpen} onCloseCreate={() => setCreateOpen(false)} onCreateProject={createProject} createBusy={busy} createForm={createForm} session={applicationSession} taskDrawerOpen={taskDrawer} onCloseTaskDrawer={() => setTaskDrawer(false)} jobs={jobs} user={user} onViewAllJobs={() => { setTaskDrawer(false); requestPath(globalPath('jobs')); }} onNavigateJob={task => { setTaskDrawer(false); if (task.projectId) requestPath(projectPath(task.projectId, task.type === 'parse' ? 'parse' : 'editor')); }} onRetryJob={handleRetryJob} onCancelJob={handleCancelJob} modelConfigModalOpen={modelConfigModalOpen} onCloseModelConfig={() => setModelConfigModalOpen(false)} token={token} workspace={workspace} ragflowConfigModalOpen={ragflowConfigModalOpen} onCloseRagflowConfig={() => setRagflowConfigModalOpen(false)} />
        </AppShell>
      </CanProvider>
    </Suspense>
  );
}
