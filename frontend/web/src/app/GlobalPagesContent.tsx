// 为什么有这个文件：提取 App 全局路由页面内容呈现容器（GlobalPagesContent）。
// 它解决什么问题：将工作台项目列表、企业资料库、后台任务中心、规则与管理、知识库、写作档案等全局页面路由分支从 App.tsx 中解耦。

import { NotificationsPage } from '../notifications/NotificationsPage';
import React, { Suspense } from 'react';
import { Alert, Button, Spin, Tabs } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { Can } from '../shell/Can';
import { ProjectListPage } from '../project/ProjectListPage';
import { sessionAllowsAction } from './session-navigation';
import { projectPath } from './app-route';
import {
  LazyAuditLogPage as AuditLogPage,
  LazyCompanyManagePage as CompanyManagePage,
  LazyCompanySettingsPage as CompanySettingsPage,
  LazyDictConfigPage as DictConfigPage,
  LazyJobsPage as JobsPage,
  LazyLibraryPage as LibraryPage,
  LazyPendingPage as PendingPage,
  LazySnippetLibraryPage as SnippetLibraryPage,
  LazyKnowledgeBaseAdminPage as KnowledgeBaseAdminPage,
  LazyUsersPage as UsersPage,
  LazyWritingArchivePage as WritingArchivePage,
} from './lazy-routes';
import type { Account, ApplicationSession, Evidence, Job, Project, SlaTemplate } from '../shared/types';
import type { LibraryReadState, LibraryWriteVersion } from '../library/library-review';
import type { TemplateReadState } from '../library/template-review';
import { kbPermissions } from '../library/kb-admin-core.ts';

export interface GlobalPagesContentProps {
  nav: string;
  loading: boolean;
  projects: Project[];
  session: ApplicationSession | null;
  currentUser: Account;
  busy: boolean;
  search: string;
  token: string | null;

  library: Evidence[];
  libraryRevision: number;
  slaTemplates: SlaTemplate[];
  slaTemplatesRevision: number;
  readLibrary: () => Promise<LibraryReadState>;
  readSlaTemplates: () => Promise<TemplateReadState>;
  libraryMutate: (
    path: string,
    method: string,
    body: unknown,
    expectedRevision?: LibraryWriteVersion
  ) => Promise<unknown>;

  jobs: Job[];
  createButton?: React.ReactNode;
  onOpenProject: (id: string, tab?: string) => void;
  onOpenCreateProject?: () => void;
  onRequestPath: (path: string) => void;
  onRetryJob: (jobId: string) => Promise<void>;
  onCancelJob: (jobId: string) => Promise<void>;
  report: (error: unknown) => void;
}

export function GlobalPagesContent({
  nav,
  loading,
  projects,
  session,
  currentUser,
  busy,
  search,
  token,
  library,
  libraryRevision,
  slaTemplates,
  slaTemplatesRevision,
  readLibrary,
  readSlaTemplates,
  libraryMutate,
  jobs,
  createButton,
  onOpenProject,
  onOpenCreateProject,
  onRequestPath,
  onRetryJob,
  onCancelJob,
  report,
}: GlobalPagesContentProps) {
  const userRole = session?.user?.primary_role || session?.user?.role;

  return (
    <Spin spinning={loading}>
      <main className="workspace-content">
        {nav === 'workbench' && (
          <>
            <div className="page-heading">
              <div>
                <h2>投标项目工作台</h2>
                <p>先看风险，再看进度。这里只列出你已经加入的本公司项目。</p>
              </div>
              {createButton ?? (
                <Can perform="project:create">
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={onOpenCreateProject}
                    disabled={busy || !sessionAllowsAction(session, 'projects.create')}
                  >
                    新建项目
                  </Button>
                </Can>
              )}
            </div>
            <ProjectListPage
              projects={projects}
              onOpenProject={onOpenProject}
              session={session}
              currentUser={currentUser}
            />
            <Alert
              className="page-notice"
              type="info"
              message="先贯通示例主链路"
              description="新建项目后，依次上传招标文件、确认解析、补响应与证据、编制两册章节、检查并下载内部稿。演示建议需要人工确认，不能直接作为正式承诺。"
              showIcon
            />
          </>
        )}

        <Suspense fallback={<Spin spinning />}>
          {nav === 'library' && (
            <LibraryPage
              items={library}
              read={readLibrary}
              readTemplates={readSlaTemplates}
              libraryRevision={libraryRevision}
              templatesRevision={slaTemplatesRevision}
              globalSearch={search}
              templates={slaTemplates}
              user={currentUser}
              busy={busy}
              mutate={libraryMutate}
              report={report}
              token={token ?? null}
            />
          )}

          {nav === 'notifications' && (
            <NotificationsPage token={token} projects={projects} onNavigate={onRequestPath} report={report} />
          )}

          {nav === 'jobs' && (
            <JobsPage
              jobs={jobs}
              openProject={id => onRequestPath(projectPath(id, 'overview'))}
              onRetry={onRetryJob}
              onCancel={onCancelJob}
              companyId={currentUser.company_id}
              role={userRole}
            />
          )}

          {nav === 'admin.rules' && (
            <Tabs
              defaultActiveKey="audit"
              items={[
                {
                  key: 'audit',
                  label: 'A-06 审计日志中心',
                  children: (
                    <AuditLogPage
                      session={session}
                      user={currentUser}
                      onNavigate={onRequestPath}
                    />
                  ),
                },
                {
                  key: 'company',
                  label: 'A-01 企业租户管理',
                  children: (
                    <CompanyManagePage
                      session={session}
                      currentUser={currentUser}
                    />
                  ),
                },
                {
                  key: 'users',
                  label: 'A-02 用户与角色',
                  children: (
                    <UsersPage
                      session={session}
                      currentUser={currentUser}
                      onNavigate={onRequestPath}
                    />
                  ),
                },
                {
                  key: 'dict',
                  label: 'A-03 字典配置',
                  children: (
                    <DictConfigPage
                      session={session}
                      currentUser={currentUser}
                      onNavigate={onRequestPath}
                    />
                  ),
                },
                {
                  key: 'settings',
                  label: 'A-05 扩展字段与公司设置',
                  children: (
                    <CompanySettingsPage
                      session={session}
                      currentUser={currentUser}
                    />
                  ),
                },
              ]}
            />
          )}

          {nav === 'knowledge' && (
            kbPermissions(currentUser?.role).read ? (
              <Tabs
                defaultActiveKey="snippets"
                items={[
                  {
                    key: 'snippets',
                    label: '方案片段',
                    children: <SnippetLibraryPage token={token} user={currentUser} session={session} />,
                  },
                  {
                    key: 'kb-admin',
                    label: '知识库管理（RAGFlow）',
                    children: <KnowledgeBaseAdminPage token={token} role={currentUser?.role} report={report} />,
                  },
                ]}
              />
            ) : (
              <SnippetLibraryPage
                token={token}
                user={currentUser}
                session={session}
              />
            )
          )}

          {nav === 'writing' && (
            <WritingArchivePage
              user={currentUser}
              session={session}
            />
          )}
        </Suspense>
      </main>
    </Spin>
  );
}
