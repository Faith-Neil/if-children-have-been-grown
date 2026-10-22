// 为什么有这个文件：提供 React Hook 便捷读取全局或局部权限上下文，并动态获取当前用户在特定资源上的操作权限。
// 它解决什么问题：解耦组件内的业务渲染与权限判定逻辑，支持声明式与编程式两种权限消费方式。

import { useContext } from 'react';
import { can, type CanContext as CanContextType, type CanResult } from './can-directive.ts';
import { CanContext } from './can-context.ts';

/**
 * 权限核验 Hook
 * @param perform 操作名称，如 "project:create", "chapter:edit", "submission:export"
 * @param on 目标资源（可为字符串标识或具体实体对象如 chapter）
 * @param overrideContext 局部覆盖上下文
 */
export function useCan(
  perform: string,
  on?: string | object | null,
  overrideContext?: CanContextType
): CanResult {
  const globalContext = useContext(CanContext);
  const mergedContext: CanContextType = {
    ...globalContext,
    ...overrideContext,
  };
  return can(perform, on, mergedContext);
}

/**
 * 批量权限核验 Hook
 */
export function useCanMap<T extends Record<string, { perform: string; on?: string | object | null }>>(
  rules: T,
  overrideContext?: CanContextType
): { [K in keyof T]: CanResult } {
  const globalContext = useContext(CanContext);
  const mergedContext: CanContextType = {
    ...globalContext,
    ...overrideContext,
  };

  const results = {} as { [K in keyof T]: CanResult };
  for (const [key, rule] of Object.entries(rules)) {
    results[key as keyof T] = can(rule.perform, rule.on, mergedContext);
  }
  return results;
}
