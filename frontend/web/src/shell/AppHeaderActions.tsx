// 为什么有这个文件：提取 App 顶栏操作区（AppHeaderActions）。
// 它解决什么问题：将环境标签、全局搜索、任务中心入口、用户信息、退出与配置弹窗入口从 App.tsx 抽离，降低 App 巨石复杂度。

import React from 'react';
import { Button, Input } from 'antd';
import {
  DatabaseOutlined,
  SearchOutlined,
  SettingOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { companyName } from '../app/context';
import { getSystemRoleLabel } from '../shared/roles';
import { sessionAllowsRoute } from '../app/session-navigation';
import { TaskBadge } from './TaskBadge';
import { NotificationBell } from '../notifications/NotificationBell';
import { shouldShowCompanyLabel } from '../admin/company-provision-core';
import { GenerationSessionBar } from '../status/GenerationSessionBar';
import { activeVolumeSession } from '../status/generation-session';
import type { Account, ApplicationSession, Job } from '../shared/types';

export interface AppHeaderActionsProps {
  session: ApplicationSession | null;
  user: Account;
  jobs: Job[];
  search: string;
  onSearchChange: (value: string) => void;
  onSearchSubmit: () => void;
  onOpenTaskDrawer: () => void;
  onLogout: () => void;
  onOpenModelConfig: () => void;
  onOpenRagflowConfig: () => void;
  token?: string | null;
  onNavigate?: (path: string) => void;
  /** 后台企业设置中的公司显示名；缺省时回退演示别名或 company_id */
  companyDisplayName?: string | null;
  /** 技术卷生成会话：停止、点开回编辑台、结束后刷新。缺省时顶栏不显示会话。 */
  onStopSession?: (jobId: string) => Promise<void> | void;
  onOpenSession?: (session: Job) => void;
  onSessionSettled?: () => void;
}

export function AppHeaderActions({
  session,
  user,
  jobs,
  search,
  onSearchChange,
  onSearchSubmit,
  onOpenTaskDrawer,
  onLogout,
  onOpenModelConfig,
  onOpenRagflowConfig,
  token = null,
  onNavigate,
  companyDisplayName = null,
  onStopSession,
  onOpenSession,
  onSessionSettled,
}: AppHeaderActionsProps) {
  const userPrimaryRole = session?.user?.primary_role;
  const roleDisplayLabel = getSystemRoleLabel(userPrimaryRole);

  const items: React.ReactElement[] = [];
  const volumeSession = activeVolumeSession(jobs);
  if (volumeSession && onStopSession && onOpenSession) {
    items.push(
      <GenerationSessionBar
        key={`generation-${volumeSession.id}`}
        session={volumeSession}
        token={token}
        onOpen={onOpenSession}
        onStop={onStopSession}
        onSettled={() => onSessionSettled?.()}
      />,
    );
  }
  if (sessionAllowsRoute(session, 'workbench')) {
    items.push(
      <Input
        key="search"
        className="global-search"
        aria-label="搜索项目名称或资料名称"
        prefix={<SearchOutlined />}
        placeholder="搜索项目名称 / 资料名称"
        value={search}
        onChange={e => onSearchChange(e.target.value)}
        suffix={<kbd>Ctrl K</kbd>}
        onPressEnter={onSearchSubmit}
      />,
    );
  }
  if (sessionAllowsRoute(session, 'jobs')) {
    items.push(<TaskBadge key="jobs" tasks={jobs} companyId={user.company_id} onClick={onOpenTaskDrawer} />);
  }
  if (sessionAllowsRoute(session, 'notifications') && onNavigate) {
    items.push(<NotificationBell key="notifications" token={token} onNavigate={onNavigate} />);
  }
  const showCompany = shouldShowCompanyLabel(userPrimaryRole || user.role);
  items.push(
    <span className="topbar-user" key="user">
      {showCompany ? (
        <span className="company-label" data-testid="header-company-label">
          <TeamOutlined /> {companyName(user.company_id, companyDisplayName)}
        </span>
      ) : null}
      <span className="user-avatar">{user.name[0]}</span>
      <span className="user-name">{user.name}<small> · {roleDisplayLabel}</small></span>
    </span>,
    <Button key="logout" type="text" size="small" onClick={onLogout}>退出</Button>,
    ...(userPrimaryRole === 'platform_admin' ? [
      <Button key="model" type="text" icon={<SettingOutlined />} aria-label="模型服务配置" onClick={onOpenModelConfig}>模型配置</Button>,
      <Button key="kb" type="text" icon={<DatabaseOutlined />} aria-label="知识库检索配置" onClick={onOpenRagflowConfig}>知识库配置</Button>,
    ] : []),
  );
  return items;
}
