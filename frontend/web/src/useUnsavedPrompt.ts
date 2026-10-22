// 为什么有这个文件：封装通用的表单未保存离开保护 Hook（useUnsavedPrompt）。
// 它解决什么问题：
// 1. 浏览器原生级别保护：在存在未保存数据（isDirty）时，监听 beforeunload 事件阻止误关闭/刷新；
// 2. 路由与交互级别保护：提供 confirmNavigation 方法，在用户试图跳转、取消或切换时唤起模态弹窗拦截；
// 3. 页面卸载时自动注销事件监听，防止内存泄露。

import { useEffect, useCallback } from 'react';
import { Modal } from 'antd';
import { FORM_LEAVE_COPY, applyBeforeUnloadEvent } from './form-interactions';

export interface UseUnsavedPromptOptions {
  /** 当前表单是否存在未保存的修改 */
  isDirty: boolean;
  /** 是否启用离开拦截（默认 true） */
  enabled?: boolean;
  /** 自定义模态框提示文案 */
  copy?: {
    title?: string;
    content?: string;
    okText?: string;
    cancelText?: string;
  };
  /** 用户确认放弃修改并离开时的额外回调 */
  onConfirmLeave?: () => void;
}

export interface UseUnsavedPromptReturn {
  /** 是否处于未保存拦截激活状态 */
  isPromptActive: boolean;
  /** 包装导航或离开行为的拦截执行器 */
  confirmNavigation: (onProceed: () => void) => void;
}

export function useUnsavedPrompt({
  isDirty,
  enabled = true,
  copy = FORM_LEAVE_COPY,
  onConfirmLeave,
}: UseUnsavedPromptOptions): UseUnsavedPromptReturn {
  const isPromptActive = isDirty && enabled;

  // 1. 浏览器原生 beforeunload 拦截（防止直接关闭标签页或刷新）
  useEffect(() => {
    if (!isPromptActive || typeof window === 'undefined') {
      return;
    }

    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      applyBeforeUnloadEvent(true, event);
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [isPromptActive]);

  // 2. 应用内路由导航或取消操作的拦截确认
  const confirmNavigation = useCallback(
    (onProceed: () => void) => {
      if (!isPromptActive) {
        onProceed();
        return;
      }

      Modal.confirm({
        title: copy.title || FORM_LEAVE_COPY.title,
        content: copy.content || FORM_LEAVE_COPY.content,
        okText: copy.okText || FORM_LEAVE_COPY.okText,
        cancelText: copy.cancelText || FORM_LEAVE_COPY.cancelText,
        okButtonProps: { danger: true },
        onOk: () => {
          if (onConfirmLeave) {
            onConfirmLeave();
          }
          onProceed();
        },
      });
    },
    [isPromptActive, copy, onConfirmLeave]
  );

  return {
    isPromptActive,
    confirmNavigation,
  };
}

export default useUnsavedPrompt;
