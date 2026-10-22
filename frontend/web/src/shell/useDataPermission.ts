// 为什么有这个文件：为 React 组件提供多粒度数据权限与只读态切换 Hook。
// 它解决什么问题：聚合 CanContext 与 ProjectContext 上下文，无缝计算项目/分册/章节当前只读态与提示原因。

import { useContext, useMemo } from 'react';
import { CanContext } from './can-context.ts';
import { ProjectContext } from '../app/context.tsx';
import {
  resolveDataPermission,
  type DataPermissionContext,
  type DataPermissionResult,
} from './data-permission.ts';
import type { Chapter, Volume, Workspace } from '../shared/types.ts';

export interface UseDataPermissionOptions {
  projectId?: string;
  volumeId?: Volume | string | null;
  volume?: Volume | 'all' | null;
  chapterId?: string | null;
  chapter?: (Pick<Chapter, 'id' | 'volume' | 'assignee_id'> & { title?: string }) | null;
  role?: string | string[] | null;
  userId?: string | null;
  workspace?: Pick<Workspace, 'permissions' | 'team' | 'chapters'> | null;
}

/**
 * 多粒度数据权限 Hook
 */
export function useDataPermission(options?: UseDataPermissionOptions): DataPermissionResult {
  const canContext = useContext(CanContext);
  const projectContext = useContext(ProjectContext);

  return useMemo(() => {
    const role =
      options?.role ??
      canContext?.role ??
      projectContext?.user?.role ??
      null;

    const userId =
      options?.userId ??
      canContext?.userId ??
      projectContext?.user?.id ??
      null;

    const workspace =
      options?.workspace ??
      canContext?.workspace ??
      projectContext?.workspace ??
      null;

    const volume =
      options?.volume ??
      (options?.volumeId as Volume | null) ??
      canContext?.volume ??
      null;

    const chapter =
      options?.chapter ??
      canContext?.chapter ??
      null;

    const chapterId =
      options?.chapterId ??
      canContext?.chapter?.id ??
      null;

    const context: DataPermissionContext = {
      role,
      userId,
      workspace,
      volume,
      chapter,
      chapterId,
    };

    return resolveDataPermission(context);
  }, [
    options?.role,
    options?.userId,
    options?.workspace,
    options?.volume,
    options?.volumeId,
    options?.chapter,
    options?.chapterId,
    canContext,
    projectContext?.user?.role,
    projectContext?.user?.id,
    projectContext?.workspace,
  ]);
}
