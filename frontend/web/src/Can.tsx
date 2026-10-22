// 为什么有这个文件：封装权限核验指令组件 <Can> 与上下文容器 <CanProvider>。
// 它解决什么问题：支持基于 PRD v1.8 §2.3 的声明式权限控制，严格保障无权限按钮从 DOM 中彻底隐藏，杜绝仅靠 CSS 隐藏被绕过的安全隐患。

import React from 'react';
import { Tooltip } from 'antd';
import { CanContext } from './can-context.ts';
import { useCan, useCanMap } from './useCan.ts';
import { can, type CanContext as CanContextType, type CanResult } from './can-directive.ts';

export { CanContext } from './can-context.ts';
export { useCan, useCanMap } from './useCan.ts';
export { can, type CanContext as CanContextType, type CanResult } from './can-directive.ts';

/**
 * 权限上下文提供器 Props
 */
export interface CanProviderProps {
  value: CanContextType;
  children: React.ReactNode;
}

/**
 * 权限上下文提供器
 */
export const CanProvider: React.FC<CanProviderProps> = ({ value, children }) => {
  return <CanContext.Provider value={value}>{children}</CanContext.Provider>;
};

/**
 * <Can> 权限核验指令 Props
 */
export interface CanProps {
  perform?: string;
  on?: string | object | null;
  action?: string; // 兼容别名
  resource?: string | object | null; // 兼容别名
  perm?: string; // 兼容别名
  data?: any; // 资源数据对象
  context?: CanContextType; // 局部覆盖上下文
  fallback?: React.ReactNode; // 无权限时的备选呈现（默认 null）
  passThrough?: boolean; // 若为 true，不隐藏元素而是将其置灰并禁用
  tooltipOnDisabled?: boolean | string; // 置灰时是否悬浮展示无权限原因
  children?: React.ReactNode | ((result: CanResult) => React.ReactNode);
}

/**
 * 权限指令组件 <Can>
 * 默认在无权限时不渲染任何 DOM 节点（零 DOM 痕迹），彻底避免 CSS display:none 绕过
 */
export const Can: React.FC<CanProps> = ({
  perform,
  on,
  action,
  resource,
  perm,
  data,
  context,
  fallback = null,
  passThrough = false,
  tooltipOnDisabled = false,
  children,
}) => {
  const targetPerform = perform || action || perm || '';
  const targetOn = on ?? resource ?? data ?? null;

  const result = useCan(targetPerform, targetOn, context);

  // 1. 函数式 children 模式
  if (typeof children === 'function') {
    return <>{children(result)}</>;
  }

  // 2. 具备权限：直接正常渲染
  if (result.allowed) {
    return <>{children}</>;
  }

  // 3. 无权限但配置了 passThrough：置灰禁用并可选注入 Tooltip
  if (passThrough && React.isValidElement(children)) {
    const tooltipText =
      typeof tooltipOnDisabled === 'string'
        ? tooltipOnDisabled
        : result.reason || '当前角色无权限操作';

    const childElement = children as React.ReactElement<any>;
    const disabledElement = React.cloneElement(childElement, {
      disabled: true,
      'aria-disabled': 'true',
      title: tooltipText,
    });

    if (tooltipOnDisabled) {
      return (
        <Tooltip title={tooltipText}>
          <span style={{ display: 'inline-block', cursor: 'not-allowed' }}>
            {disabledElement}
          </span>
        </Tooltip>
      );
    }
    return disabledElement;
  }

  // 4. 默认严格安全模式：完全不渲染，无任何 DOM 节点残留
  return <>{fallback}</>;
};

export default Can;
