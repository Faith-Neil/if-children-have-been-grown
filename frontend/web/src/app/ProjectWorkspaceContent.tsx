// 为什么有这个文件：提取项目工作区内容区域（ProjectWorkspaceContent）。
// 它解决什么问题：将 ProjectHeader、只读横幅、ProjectContext 与 10 个项目子页签从 App.tsx 中解耦。

import React, { Suspense } from 'react';
import { Spin } from 'antd';
import { ProjectHeader } from '../project/ProjectHeader';
import { ProjectContext } from './context';
import { ReadonlyBanner } from '../status/StatusViews';
import {
  LazyChecksPage as ChecksPage,
  LazyEditorPage as EditorPage,
  LazyExportPage as ExportPage,
  LazyFactsPage as FactsPage,
  LazyMatrixPage as MatrixPage,
  LazyOverviewPage as OverviewPage,
  LazyParsePage as ParsePage,
  LazyManualQueuePage as ManualQueuePage,
  LazyProjectSettingsPage as ProjectSettingsPage,
  LazyTenderPage as TenderPage,
} from './lazy-routes';
import type { Account, ApplicationSession, Evidence, SlaTemplate, Workspace } from '../shared/types';
import type { AppRoute } from './app-route';

export interface ProjectWorkspaceContentProps {
  workspace: Workspace;
  tab: string;
  loading: boolean;
  accessLost: boolean;
  session: ApplicationSession | null;
  currentUser: Account;
  token: string;
  library: Evidence[];
  slaTemplates: SlaTemplate[];
  busy: boolean;
  currentRoute: AppRoute;
  onNavigateTab: (tab: string) => void;
  onDirtyChange: (dirty: boolean) => void;
  onBackToWorkbench: () => void;
  mutate: (path: string, method: string, body?: unknown) => Promise<unknown>;
  reload: () => Promise<Workspace | undefined>;
  report: (error: unknown) => void;
  navigate: (value: string) => void;
}

export function ProjectWorkspaceContent({
  workspace,
  tab,
  loading,
  accessLost,
  session,
  currentUser,
  token,
  library,
  slaTemplates,
  busy,
  currentRoute,
  onNavigateTab,
  onDirtyChange,
  onBackToWorkbench,
  mutate,
  reload,
  report,
  navigate,
}: ProjectWorkspaceContentProps) {
  const isCompactTab = ['matrix', 'editor', 'checks', 'export'].includes(tab);
  const isFullbleedTab = ['parse', 'editor'].includes(tab);

  return (
    <>
      <ProjectHeader
        workspace={workspace}
        activeTab={tab}
        onNavigateTab={onNavigateTab}
        session={session}
        currentUser={currentUser}
        compact={isCompactTab}
      />

      <ProjectContext.Provider
        value={{
          workspace,
          token,
          user: currentUser,
          library,
          slaTemplates,
          busy,
          mutate,
          reload,
          report,
          navigate,
        }}
      >
        <Spin spinning={loading}>
          {accessLost && (
            <ReadonlyBanner
              reason="当前页面的写入已暂停"
              description="之前读取的内容及未保存文字仍保留。请返回工作台或进入有权访问的页面，重新核对最新权限。"
              onAction={onBackToWorkbench}
              actionText="返回工作台"
              className="page-notice"
            />
          )}

          <main className={`project-content ${isFullbleedTab ? 'fullbleed' : ''}`}>
            <Suspense fallback={<Spin spinning />}>
              <>
                {tab === 'overview' && <OverviewPage />}
                {tab === 'tender' && <TenderPage />}
                {tab === 'parse' && <ParsePage />}
                {tab === 'matrix' && <MatrixPage />}
                {tab === 'facts' && <FactsPage />}
                {tab === 'editor' && (
                  <EditorPage
                    key={workspace.project.id}
                    onDirtyChange={onDirtyChange}
                    initialChapterId={
                      currentRoute.kind === 'project' && currentRoute.tab === 'editor'
                        ? currentRoute.chapterId
                        : undefined
                    }
                  />
                )}
                {tab === 'checks' && <ChecksPage />}
                {tab === 'export' && <ExportPage />}
                {tab === 'settings' && <ProjectSettingsPage />}
                {tab === 'manual' && <ManualQueuePage />}
              </>
            </Suspense>
          </main>
        </Spin>
      </ProjectContext.Provider>
    </>
  );
}
