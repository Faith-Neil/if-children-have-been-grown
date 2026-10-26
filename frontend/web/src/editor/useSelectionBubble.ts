// 为什么有这个文件：提取正文划词选择与 AI 交互气泡状态机（useSelectionBubble）。
// 它解决什么问题：解耦选区坐标计算、浮动气泡可见性、润色与合规问答派发及选区清理，降低 EditorPage 行数。

import { useRef, useState } from 'react';

export interface SelectionBubbleState {
  visible: boolean;
  position: { top: number; left: number } | null;
  text: string;
}

export interface UseSelectionBubbleOptions {
  content: string;
  onPolish: (text: string) => void;
  onComplianceQa: (text: string) => void;
}

export function useSelectionBubble({
  content,
  onPolish,
  onComplianceQa,
}: UseSelectionBubbleOptions) {
  const [selectionBubble, setSelectionBubble] = useState<SelectionBubbleState>({
    visible: false,
    position: null,
    text: '',
  });
  const editorWrapperRef = useRef<HTMLElement | null>(null);
  const selection = useRef<{ start: number; end: number } | null>(null);

  // 1. 文本输入框选区事件处理
  const handleTextareaSelect = (e: React.SyntheticEvent<HTMLTextAreaElement>) => {
    const target = e.currentTarget;
    selection.current = { start: target.selectionStart, end: target.selectionEnd };
    const selText = content.slice(target.selectionStart, target.selectionEnd);
    if (selText.trim().length > 0) {
      const rect = target.getBoundingClientRect();
      const wrapperRect = editorWrapperRef.current?.getBoundingClientRect();
      const offsetTop = wrapperRect ? Math.max(10, rect.top - wrapperRect.top + 20) : 20;
      const offsetLeft = wrapperRect ? Math.max(120, rect.left - wrapperRect.left + 220) : 220;
      setSelectionBubble({
        visible: true,
        position: { top: offsetTop, left: offsetLeft },
        text: selText,
      });
    } else {
      setSelectionBubble(prev => ({ ...prev, visible: false }));
    }
  };

  // 2. 只读/未持锁容器划词事件处理
  const handleContainerMouseUp = () => {
    const winSel = window.getSelection();
    const selText = winSel?.toString() || '';
    if (selText.trim().length > 0) {
      const range = winSel?.getRangeAt(0);
      const rect = range?.getBoundingClientRect();
      const wrapperRect = editorWrapperRef.current?.getBoundingClientRect();
      if (rect && wrapperRect) {
        setSelectionBubble({
          visible: true,
          position: {
            top: Math.max(10, rect.top - wrapperRect.top - 8),
            left: Math.max(120, rect.left - wrapperRect.left + rect.width / 2),
          },
          text: selText,
        });
        return;
      }
    }
  };

  // 3. 气泡操作：润色模式
  const handleBubblePolish = (selectedText: string) => {
    onPolish(selectedText);
    setSelectionBubble(prev => ({ ...prev, visible: false }));
  };

  // 4. 气泡操作：合规问答模式
  const handleBubbleComplianceQa = (selectedText: string) => {
    onComplianceQa(selectedText);
    setSelectionBubble(prev => ({ ...prev, visible: false }));
  };

  // 5. 气泡清理与取消选区
  const handleBubbleClear = () => {
    setSelectionBubble({ visible: false, position: null, text: '' });
    selection.current = null;
    if (window.getSelection) {
      window.getSelection()?.removeAllRanges();
    }
  };

  return {
    selectionBubble,
    setSelectionBubble,
    editorWrapperRef,
    selection,
    handleTextareaSelect,
    handleContainerMouseUp,
    handleBubblePolish,
    handleBubbleComplianceQa,
    handleBubbleClear,
  };
}
