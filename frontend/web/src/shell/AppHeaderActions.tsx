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
import { sessionAllowsRoute } from '../app/session-navigation';
import { TaskBadge } from './TaskBadge';
import { NotificationBell } from '../notifications/NotificationBell';
import { shouldShowCompanyLabel } from '../admin/company-provision-core';
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
}: AppHeaderActionsProps) {
  const userPrimaryRole = session?.user?.primary_role;
  const roleDisplayLabel =
    {
      platform_admin: '平台管理员',
      group_admin: '集团管理员',
      company_admin: '公司管理员',
      data_admin: '资料管理员',
      project_lead: '项目负责人',
      bid_writer: '投标编写人',
      auditor: '审核人',
      viewer: '只读成员',
    }[userPrimaryRole ?? ''] ?? '成员';

  const items: React.ReactElement[] = [];
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
    <Button key="model" type="text" icon={<SettingOutlined />} aria-label="模型服务配置" onClick={onOpenModelConfig}>模型配置</Button>,
    <Button key="kb" type="text" icon={<DatabaseOutlined />} aria-label="知识库检索配置" onClick={onOpenRagflowConfig}>知识库配置</Button>,
  );
  return items;
}
