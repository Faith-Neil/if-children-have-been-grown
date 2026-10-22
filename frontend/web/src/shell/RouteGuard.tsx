// 为什么有这个文件：为 React 组件树提供声明式路由与视图守卫。
// 它解决什么问题：当用户越权或会话失效时，阻断受保护子组件渲染，呈现具备角色提示与切换身份动作的语义化 403 页面。

import { type CSSProperties, type ReactNode } from 'react';
import type { ApplicationSession, Workspace } from '../shared/types.ts';
import { checkRoutePermission, type RoutePermissionResult } from './route-guard.ts';
import { Forbidden403 } from '../status/StatusViews.tsx';

export interface RouteGuardProps {
  session: ApplicationSession | null;
  targetPath: string;
  workspace?: Workspace | null;
  action?: string;
  chapterId?: string;
  onBack?: () => void;
  onSwitchRole?: () => void;
  backText?: string;
  switchRoleText?: string;
  fallback?: (result: RoutePermissionResult) => ReactNode;
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
}

export function RouteGuard({
  session,
  targetPath,
  workspace,
  action,
  chapterId,
  onBack,
  onSwitchRole,
  backText = '返回可访问首页',
  switchRoleText = '切换身份',
  fallback,
  children,
  className = '',
  style,
}: RouteGuardProps) {
  const result = checkRoutePermission({
    session,
    targetPath,
    workspace,
    action,
    chapterId,
  });

  if (result.allowed) {
    return <>{children}</>;
  }

  if (fallback) {
    return <>{fallback(result)}</>;
  }

  return (
    <div className={`icg-route-guard-forbidden ${className}`} style={style} data-testid="route-guard-forbidden">
      <Forbidden403
        title="403 访问受限"
        reason={result.reason}
        contextInfo={
          result.contextInfo ?? {
            projectName: workspace?.project?.name,
            roleName: result.roleLabel,
            path: targetPath,
          }
        }
        showRetainedNotice={Boolean(workspace)}
        onBack={onBack}
        backText={backText}
        onSwitchRole={onSwitchRole}
        switchRoleText={switchRoleText}
      />
    </div>
  );
}

export default RouteGuard;
