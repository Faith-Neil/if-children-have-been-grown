// 为什么有这个文件：提取 App 全局弹窗与抽屉容器（AppModals）。
// 它解决什么问题：将新建项目、任务中心、模型配置与知识库配置弹窗聚合管理，支持平台管理员脱敏注入与权限感知。

import React from 'react';
import type { FormInstance } from 'antd';
import { CreateProjectModal } from '../project/CreateProjectModal';
import { TaskCenterDrawer } from './TaskCenterDrawer';
import { ModelConfigModal } from '../admin/ModelConfigModal';
import { RagflowConfigModal } from '../admin/RagflowConfigModal';
import { sessionAllowsAction } from '../app/session-navigation';
import type { Account, ApplicationSession, Job, Workspace } from '../shared/types';
import type { TaskItem } from './task-center';

export interface AppModalsProps {
  createOpen: boolean;
  onCloseCreate: () => void;
  onCreateProject: () => void;
  createBusy: boolean;
  createForm: FormInstance;
  session: ApplicationSession | null;

  taskDrawerOpen: boolean;
  onCloseTaskDrawer: () => void;
  jobs: Job[];
  user: Account | null;
  onViewAllJobs: () => void;
  onNavigateJob: (task: TaskItem) => void;
  onRetryJob?: (jobId: string, failedStepKey?: string) => Promise<void> | void;
  onCancelJob?: (jobId: string) => Promise<void> | void;

  modelConfigModalOpen: boolean;
  onCloseModelConfig: () => void;
  token: string | null;
  workspace: Workspace | null;

  ragflowConfigModalOpen: boolean;
  onCloseRagflowConfig: () => void;
}

export function AppModals({
  createOpen,
  onCloseCreate,
  onCreateProject,
  createBusy,
  createForm,
  session,

  taskDrawerOpen,
  onCloseTaskDrawer,
  jobs,
  user,
  onViewAllJobs,
  onNavigateJob,
  onRetryJob,
  onCancelJob,

  modelConfigModalOpen,
  onCloseModelConfig,
  token,
  workspace,

  ragflowConfigModalOpen,
  onCloseRagflowConfig,
}: AppModalsProps) {
  const userRole = session?.user?.primary_role || session?.user?.role;

  return (
    <>
      <CreateProjectModal
        open={createOpen}
        onCancel={onCloseCreate}
        onOk={onCreateProject}
        confirmLoading={createBusy}
        canCreate={sessionAllowsAction(session, 'projects.create')}
        form={createForm}
      />

      <TaskCenterDrawer
        open={taskDrawerOpen}
        onClose={onCloseTaskDrawer}
        tasks={jobs}
        companyId={user?.company_id}
        role={userRole}
        onViewAll={onViewAllJobs}
        onNavigateJob={onNavigateJob}
        onRetry={onRetryJob}
        onCancel={onCancelJob}
      />

      <ModelConfigModal
        open={modelConfigModalOpen}
        onClose={onCloseModelConfig}
        token={token}
        session={session}
        projectId={workspace?.project?.id}
        projectSensitive={Boolean(workspace?.project?.sensitive)}
      />

      <RagflowConfigModal
        open={ragflowConfigModalOpen}
        onClose={onCloseRagflowConfig}
        token={token}
        session={session}
      />
    </>
  );
}
