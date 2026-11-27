// 为什么有这个文件：技术方案正文在编辑台里按纸面排版，而不是展示 Markdown 源码。
// 它解决什么问题：标题、加粗、列表和表格可以直接改；保存时写回章节原有的 Markdown 字段。

import React, { forwardRef, useCallback, useEffect, useImperativeHandle, useLayoutEffect, useRef, useState } from 'react';
import { EditorContent, useEditor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Underline from '@tiptap/extension-underline';
import Table from '@tiptap/extension-table';
import TableRow from '@tiptap/extension-table-row';
import TableHeader from '@tiptap/extension-table-header';
import TableCell from '@tiptap/extension-table-cell';
import Placeholder from '@tiptap/extension-placeholder';
import { docToMarkdown, markdownToDoc, sameMarkdown, type PaperNode } from './paper-markdown';
import { estimatePaperPageCount, paperStackMinHeight } from './paper-pagination';
import { StreamingPaperView, type StreamingStage } from './StreamingPaperView';

export interface PaperEditorHandle {
  undo: () => void;
  redo: () => void;
  bold: () => void;
  underline: () => void;
  heading: (level: 1 | 2 | 3) => void;
  paragraph: () => void;
  bullet: () => void;
  ordered: () => void;
  table: () => void;
  insertParagraph: (text: string) => void;
  caretOffset: () => number | null;
  selectText: (phrase: string) => boolean;
}

interface Props {
  markdown: string;
  editable: boolean;
  generating: boolean;
  streamStage?: StreamingStage;
  streamFinishing?: boolean;
  waitingForFirstText?: boolean;
  onChange: (markdown: string) => void;
  onActivity?: () => void;
  onSelection?: (range: { start: number; end: number; text: string } | null) => void;
}

function markdownOffset(doc: { cut: (from: number, to: number) => { toJSON: () => PaperNode } }, pos: number) {
  if (pos <= 0) return 0;
  return docToMarkdown(doc.cut(0, pos).toJSON()).length;
}

export const PaperEditor = forwardRef<PaperEditorHandle, Props>(function PaperEditor({ markdown, editable, generating, streamStage = '', streamFinishing = false, waitingForFirstText = false, onChange, onActivity, onSelection }, ref) {
  const incoming = useRef(markdown);
  incoming.current = markdown;
  const changeRef = useRef(onChange);
  const activityRef = useRef(onActivity);
  const selectionRef = useRef(onSelection);
  changeRef.current = onChange;
  activityRef.current = onActivity;
  selectionRef.current = onSelection;
  const sheetRef = useRef<HTMLDivElement>(null);
  const [pageCount, setPageCount] = useState(1);
  // 流式跟随的对象是活跃光标而不是整篇文档底部：多节标书写靠前章节时，写作位置在文档中部。
  const [followPaused, setFollowPaused] = useState(false);
  const autoFollow = useRef(true);
  const expectedScrollTop = useRef<number | null>(null);
  const followAnimation = useRef(0);
  const syncPageLayout = useCallback(() => {
    const sheet = sheetRef.current;
    const surface = (sheet?.querySelector('.paper-streaming-view') ?? sheet?.querySelector('.paper-surface')) as HTMLElement | null;
    if (!surface || !sheet) return;
    const pages = estimatePaperPageCount(surface.scrollHeight);
    setPageCount(pages);
    sheet.style.minHeight = `${paperStackMinHeight(pages)}px`;
    sheet.dataset.pages = String(pages);
  }, []);
  const editor = useEditor({
    extensions: [
      StarterKit.configure({ heading: { levels: [1, 2, 3, 4, 5, 6] } }),
      Underline,
      Table.configure({ resizable: false }),
      TableRow,
      TableHeader,
      TableCell,
      Placeholder.configure({ placeholder: '编写本节投标响应。' }),
    ],
    content: markdownToDoc(markdown),
    editable: editable && !generating,
    editorProps: {
      attributes: { class: 'paper-surface', 'aria-label': '章节正文' },
    },
    onUpdate: ({ editor: current }) => {
      const next = docToMarkdown(current.getJSON() as PaperNode);
      if (sameMarkdown(next, incoming.current)) return;
      activityRef.current?.();
      changeRef.current(next);
    },
  });

  useEffect(() => {
    editor?.setEditable(editable && !generating);
  }, [editor, editable, generating]);

  // 流式期间不重建 ProseMirror；完成交接时在绘制前一次性写入正式正文并恢复滚动位置。
  useLayoutEffect(() => {
    if (!editor || generating) return;
    const current = docToMarkdown(editor.getJSON() as PaperNode);
    if (sameMarkdown(current, markdown)) return;
    const scroller = sheetRef.current?.closest('.editor-scroll');
    const top = scroller instanceof HTMLElement ? scroller.scrollTop : 0;
    editor.commands.setContent(markdownToDoc(markdown), false);
    if (!(scroller instanceof HTMLElement)) return;
    const restore = () => {
      scroller.scrollTop = top;
    };
    restore();
    if (typeof requestAnimationFrame === 'function') requestAnimationFrame(restore);
  }, [editor, markdown, generating]);

  // 流式开始默认跟随活跃光标；用户手动滚动离开生成区即暂停，点「定位到正在撰写」恢复。
  useEffect(() => {
    if (generating) {
      autoFollow.current = true;
      setFollowPaused(false);
      expectedScrollTop.current = null;
    }
    return () => cancelAnimationFrame(followAnimation.current);
  }, [generating]);

  useEffect(() => {
    if (!generating) return;
    const scroller = sheetRef.current?.closest('.editor-scroll');
    if (!(scroller instanceof HTMLElement)) return;
    // 会话开始且容器就绪即初始化预期滚动基准，不等写作光标出现；
    // 否则等待首字期间用户拖动滚动条会被误判偏差之外的“无基线”情况，无法暂停跟随。
    if (expectedScrollTop.current === null) expectedScrollTop.current = scroller.scrollTop;
    const pause = () => {
      if (!autoFollow.current) return;
      autoFollow.current = false;
      cancelAnimationFrame(followAnimation.current);
      setFollowPaused(true);
    };
    const onWheel = (event: WheelEvent) => {
      // 只有滚轮方向能实际移动视口才暂停；页顶向上滚轮不动视口，不算离开生成区。
      const canScrollUp = event.deltaY < 0 && scroller.scrollTop > 0;
      const canScrollDown = event.deltaY > 0 && scroller.scrollTop + scroller.clientHeight < scroller.scrollHeight - 2;
      if (canScrollUp || canScrollDown) pause();
    };
    const onScroll = () => {
      // 程序化滚动总会落在预期位置；出现偏差说明是用户拖动滚动条或键盘滚动。
      const expected = expectedScrollTop.current;
      if (expected !== null && Math.abs(scroller.scrollTop - expected) > 2) pause();
    };
    scroller.addEventListener('wheel', onWheel, { passive: true });
    scroller.addEventListener('touchmove', pause, { passive: true });
    scroller.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      scroller.removeEventListener('wheel', onWheel);
      scroller.removeEventListener('touchmove', pause);
      scroller.removeEventListener('scroll', onScroll);
    };
  }, [generating, editor]);

  // 每次文本生长时把活跃光标钳制在视口 65%~75% 舒适带内；增量小步即时滚动，视觉上自然平滑。
  useEffect(() => {
    if (!generating) return;
    syncPageLayout();
    if (!autoFollow.current) return;
    const scroller = sheetRef.current?.closest('.editor-scroll');
    if (!(scroller instanceof HTMLElement)) return;
    const caret = sheetRef.current?.querySelector('.stream-cursor');
    if (!(caret instanceof HTMLElement)) return;
    const pin = () => {
      // rAF 排队的回调可能晚于用户上翻暂停执行，必须重新确认跟随仍开启，否则会把视口拽回生成区。
      if (!autoFollow.current) return;
      const caretRect = caret.getBoundingClientRect();
      const rect = scroller.getBoundingClientRect();
      const bandTop = rect.top + scroller.clientHeight * 0.65;
      const bandBottom = rect.top + scroller.clientHeight * 0.75;
      let delta = 0;
      if (caretRect.bottom > bandBottom) delta = caretRect.bottom - bandBottom;
      else if (caretRect.top < bandTop) delta = caretRect.top - bandTop;
      if (Math.abs(delta) > 1) scroller.scrollTop += delta;
      expectedScrollTop.current = scroller.scrollTop;
    };
    pin();
    if (typeof requestAnimationFrame === 'function') requestAnimationFrame(pin);
  }, [markdown, generating, syncPageLayout]);

  const scrollToWriting = useCallback(() => {
    const scroller = sheetRef.current?.closest('.editor-scroll');
    if (!(scroller instanceof HTMLElement)) return;
    autoFollow.current = true;
    setFollowPaused(false);
    const caret = sheetRef.current?.querySelector('.stream-cursor');
    if (!(caret instanceof HTMLElement)) return;
    const rect = scroller.getBoundingClientRect();
    const caretRect = caret.getBoundingClientRect();
    const target = scroller.scrollTop + caretRect.top - (rect.top + scroller.clientHeight * 0.7);
    cancelAnimationFrame(followAnimation.current);
    const reduced = typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced || Math.abs(target - scroller.scrollTop) < 2) {
      scroller.scrollTop = target;
      expectedScrollTop.current = scroller.scrollTop;
      return;
    }
    const start = scroller.scrollTop;
    const distance = target - start;
    const clock = () => (typeof performance !== 'undefined' ? performance.now() : Date.now());
    const started = clock();
    const step = () => {
      if (!autoFollow.current) return;
      const progress = Math.min(1, (clock() - started) / 260);
      scroller.scrollTop = start + distance * (1 - Math.pow(1 - progress, 3));
      expectedScrollTop.current = scroller.scrollTop;
      if (progress < 1) followAnimation.current = requestAnimationFrame(step);
    };
    followAnimation.current = requestAnimationFrame(step);
  }, []);

  useEffect(() => {
    const node = sheetRef.current;
    if (!node || !editor) return;
    const apply = (event: Event) => {
      const text = (event as CustomEvent<string>).detail;
      if (typeof text !== 'string') return;
      editor.commands.setContent(markdownToDoc(text), true);
    };
    node.addEventListener('icg-set-markdown', apply);
    return () => node.removeEventListener('icg-set-markdown', apply);
  }, [editor]);

  useEffect(() => {
    if (!editor) return;
    const run = () => requestAnimationFrame(syncPageLayout);
    run();
    const reportSelection = () => {
      const { from, to } = editor.state.selection;
      if (from === to) {
        selectionRef.current?.(null);
        return;
      }
      const text = editor.state.doc.textBetween(from, to, '\n');
      selectionRef.current?.(text
        ? { start: markdownOffset(editor.state.doc, from), end: markdownOffset(editor.state.doc, to), text }
        : null);
    };
    editor.on('create', run);
    editor.on('update', run);
    editor.on('transaction', run);
    editor.on('selectionUpdate', reportSelection);
    const surface = sheetRef.current?.querySelector('.paper-surface') as HTMLElement | null;
    const ro = surface ? new ResizeObserver(run) : null;
    if (surface && ro) ro.observe(surface);
    return () => {
      editor.off('create', run);
      editor.off('update', run);
      editor.off('transaction', run);
      editor.off('selectionUpdate', reportSelection);
      ro?.disconnect();
    };
  }, [editor, syncPageLayout]);

  useImperativeHandle(ref, () => ({
    undo: () => { editor?.chain().focus().undo().run(); },
    redo: () => { editor?.chain().focus().redo().run(); },
    bold: () => { editor?.chain().focus().toggleBold().run(); },
    underline: () => { editor?.chain().focus().toggleUnderline().run(); },
    heading: level => { editor?.chain().focus().toggleHeading({ level }).run(); },
    paragraph: () => { editor?.chain().focus().setParagraph().run(); },
    bullet: () => { editor?.chain().focus().toggleBulletList().run(); },
    ordered: () => { editor?.chain().focus().toggleOrderedList().run(); },
    table: () => { editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run(); },
    insertParagraph: text => { editor?.chain().focus().insertContent({ type: 'paragraph', content: [{ type: 'text', text }] }).run(); },
    caretOffset: () => (editor ? markdownOffset(editor.state.doc, editor.state.selection.from) : null),
    selectText: phrase => {
      if (!editor || !phrase) return false;
      let found: { from: number; to: number } | null = null;
      editor.state.doc.descendants((node, pos) => {
        if (found || !node.isText || !node.text) return;
        const index = node.text.indexOf(phrase);
        if (index < 0) return;
        found = { from: pos + index, to: pos + index + phrase.length };
      });
      if (!found) return false;
      editor.chain().focus().setTextSelection(found).run();
      return true;
    },
  }), [editor]);

  return (
    <div className="paper-workspace" data-testid="paper-workspace">
      <div
        className={`paper-sheet${generating ? ' is-generating' : ''}`}
        data-testid="paper-editor"
        data-page-count={pageCount}
        ref={sheetRef}
      >
        <div className={generating ? 'paper-editor-hidden' : undefined} aria-hidden={generating || undefined}>
          <EditorContent editor={editor} />
        </div>
        {generating && <StreamingPaperView markdown={markdown} stage={streamStage} waitingForFirstText={waitingForFirstText} cursorEnding={streamFinishing} />}
        <span className="paper-page-indicator" data-testid="paper-page-indicator">共 {pageCount} 页</span>
      </div>
      {generating && followPaused && <div className="stream-scroll-dock">
        <button type="button" className="stream-back-bottom" data-testid="stream-locate-writing" onClick={scrollToWriting}>定位到正在撰写</button>
      </div>}
    </div>
  );
});
