// 为什么有这个文件：落实 2026-10-26 用户审计与官方拍板 B2（引入 React-Router 现代化路由体系）。
// 它解决什么问题：将简易字符串手动路由分发解耦为结构化 React-Router 体系，提供八角色可信守卫（AuthGuard）与脏状态拦截（DirtyGuard）。

import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import type { Account, ApplicationSession, Workspace } from '../shared/types';
import { checkRoutePermission, getSystemRoleLabel } from '../shell/route-guard';
import { Forbidden403 } from '../status/StatusViews';
import { sessionHomeRoute } from './session-navigation';
import { APP_ROUTES, buildGlobalPath } from './routes-core.ts';

export * from './routes-core.ts';

/**
 * AuthGuard 认证与权限守卫组件属性
 */
export interface AuthGuardProps {
  session: ApplicationSession | null;
  token: string | null;
  user: Account | null;
  workspace?: Workspace | null;
  children?: React.ReactNode;
  onNavigate?: (path: string) => void;
  onSwitchRole?: () => void;
}

/**
 * 可信路由认证与 RBAC 八角色守卫组件
 * 1. 认证守卫：未登录跳 /login，并保存来源路径 state.from；
 * 2. 权限守卫：配合现有 roles.ts 8 大标准 RBAC 角色，越权拦截展示语义化 403 页面。
 */
export function AuthGuard({
  session,
  token,
  user,
  workspace,
  children,
  onNavigate,
  onSwitchRole,
}: AuthGuardProps) {
  const location = useLocation();

  // 1. 未认证守卫拦截：跳转 /login
  if (!token || !user) {
    return <Navigate to={APP_ROUTES.LOGIN} replace state={{ from: location.pathname }} />;
  }

  // 2. 八角色与细粒度项目分工权限核验
  if (session) {
    const guard = checkRoutePermission({
      session,
      targetPath: location.pathname,
      workspace,
    });

    if (!guard.allowed && guard.code !== 'UNAUTHENTICATED') {
      const homeRoute = sessionHomeRoute(session);
      const homePath = buildGlobalPath(homeRoute);
      const currentRole = session?.user?.primary_role || user.role;

      return (
        <main className="workspace-content">
          <Forbidden403
            title="403 访问受限"
            reason={guard.reason}
            showRetainedNotice={!!workspace}
            contextInfo={{
              projectName: workspace?.project?.name,
              roleName: guard.roleLabel ?? (currentRole ? getSystemRoleLabel(currentRole) : undefined),
              path: location.pathname,
            }}
            onBack={() => {
              if (onNavigate) onNavigate(homePath);
            }}
            backText="返回可访问首页"
            onSwitchRole={onSwitchRole}
            switchRoleText="切换身份"
          />
        </main>
      );
    }
  }

  return <>{children ?? <Outlet />}</>;
}

/**
 * DirtyGuard 脏状态离开守卫属性
 */
export interface DirtyGuardProps {
  dirty: boolean;
  currentPath: string;
  onConfirmLeave?: () => void;
  children?: React.ReactNode;
}

/**
 * 脏状态离开守卫组件（配合 LeaveGuard 与编辑器使用）
 */
export function DirtyGuard({
  dirty,
  children,
}: DirtyGuardProps) {
  return <>{children ?? <Outlet />}</>;
}
