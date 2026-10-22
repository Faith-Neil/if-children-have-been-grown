// 为什么有这个文件：提供 React 权限上下文实例，支持 CanProvider 与 useCan 解耦共享。
// 它解决什么问题：消除组件层与 Hook 层的循环依赖，确保上下文初始化安全。

import React from 'react';
import type { CanContext as CanContextType } from './can-directive.ts';

/**
 * 全局或局部权限上下文
 */
export const CanContext = React.createContext<CanContextType>({});
